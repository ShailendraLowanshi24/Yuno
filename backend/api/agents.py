"""
Agent CRUD API — create, read, update, delete agents.
Also handles chat, channel config, and schedule management.
"""

from __future__ import annotations

import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import (
    Agent, AgentStatus, Message, MessageRole, ChannelType,
    ChannelConfig, get_db
)
from ..agents.runtime import AgentRunner
from ..agents.tools import get_all_tool_names, TOOL_DESCRIPTIONS
from ..channels import start_channel, stop_channel
from ..agents.scheduler import register_agent_schedule, unregister_agent_schedule

router = APIRouter(prefix="/agents", tags=["Agents"])


# ─────────────────────────────────────────────
#  Pydantic schemas
# ─────────────────────────────────────────────

class AgentCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    role: str = Field(..., min_length=1, max_length=128)
    system_prompt: str = Field(..., min_length=1)
    model: str = "gpt-4o-mini"
    provider: str = "openai"
    tools: List[str] = []
    skills: List[str] = []
    channels: List[str] = []
    guardrails: dict = {}
    memory_enabled: bool = True
    memory_window: int = 20
    max_tokens: int = 2048
    temperature: float = 0.7
    max_iterations: int = 10
    schedule: Optional[str] = None
    schedule_prompt: Optional[str] = None
    interaction_rules: dict = {}


class AgentUpdate(BaseModel):
    name: Optional[str] = None
    role: Optional[str] = None
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    tools: Optional[List[str]] = None
    skills: Optional[List[str]] = None
    channels: Optional[List[str]] = None
    guardrails: Optional[dict] = None
    memory_enabled: Optional[bool] = None
    memory_window: Optional[int] = None
    max_tokens: Optional[int] = None
    temperature: Optional[float] = None
    max_iterations: Optional[int] = None
    schedule: Optional[str] = None
    schedule_prompt: Optional[str] = None
    interaction_rules: Optional[dict] = None


class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChannelConfigCreate(BaseModel):
    channel_type: str
    config: dict


# ─────────────────────────────────────────────
#  Agent CRUD
# ─────────────────────────────────────────────

@router.get("/")
async def list_agents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).order_by(desc(Agent.created_at)))
    agents = result.scalars().all()
    return [a.to_dict() for a in agents]


@router.post("/", status_code=201)
async def create_agent(payload: AgentCreate, db: AsyncSession = Depends(get_db)):
    agent = Agent(
        id=str(uuid.uuid4()),
        **payload.model_dump(),
    )
    db.add(agent)
    await db.flush()

    # Register schedule if provided
    if agent.schedule and agent.schedule_prompt:
        await register_agent_schedule(agent.id, agent.schedule, agent.schedule_prompt)

    await db.commit()
    await db.refresh(agent)
    return agent.to_dict()


@router.get("/tools")
async def list_tools():
    """Return all available tool names and descriptions."""
    return [
        {"name": name, "description": desc}
        for name, desc in TOOL_DESCRIPTIONS.items()
    ]


@router.get("/{agent_id}")
async def get_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")
    return agent.to_dict()


@router.put("/{agent_id}")
async def update_agent(agent_id: str, payload: AgentUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")

    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(agent, field, value)

    # Re-register schedule if it changed
    if payload.schedule is not None:
        if payload.schedule and agent.schedule_prompt:
            await register_agent_schedule(agent.id, agent.schedule, agent.schedule_prompt)
        else:
            await unregister_agent_schedule(agent.id)

    db.add(agent)
    await db.commit()
    await db.refresh(agent)
    return agent.to_dict()


@router.delete("/{agent_id}", status_code=204)
async def delete_agent(agent_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")

    await unregister_agent_schedule(agent_id)
    await db.delete(agent)
    await db.commit()


# ─────────────────────────────────────────────
#  Chat (REST)
# ─────────────────────────────────────────────

@router.post("/{agent_id}/chat")
async def chat_with_agent(
    agent_id: str,
    payload: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    agent = result.scalar_one_or_none()
    if not agent:
        raise HTTPException(404, "Agent not found")

    session_id = payload.session_id or str(uuid.uuid4())

    # Load memory (last N messages)
    from langchain_core.messages import HumanMessage, AIMessage
    history = []
    if agent.memory_enabled:
        msg_result = await db.execute(
            select(Message)
            .where(Message.agent_id == agent_id, Message.session_id == session_id)
            .order_by(Message.created_at)
            .limit(agent.memory_window)
        )
        past_msgs = msg_result.scalars().all()
        for m in past_msgs:
            if m.role == MessageRole.USER:
                history.append(HumanMessage(content=m.content))
            elif m.role == MessageRole.ASSISTANT:
                history.append(AIMessage(content=m.content))

    runner = AgentRunner(agent, db)
    response = await runner.run(
        user_input=payload.message,
        session_id=session_id,
        channel=ChannelType.UI,
        history=history,
    )

    return {"session_id": session_id, "response": response}


# ─────────────────────────────────────────────
#  Chat (WebSocket — real-time streaming)
# ─────────────────────────────────────────────

@router.websocket("/{agent_id}/ws/{session_id}")
async def chat_websocket(
    agent_id: str,
    session_id: str,
    websocket: WebSocket,
):
    from ..db.session import AsyncSessionLocal
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            user_input = data.get("message", "")
            if not user_input:
                continue

            async with AsyncSessionLocal() as db:
                result = await db.execute(select(Agent).where(Agent.id == agent_id))
                agent = result.scalar_one_or_none()
                if not agent:
                    await websocket.send_json({"error": "Agent not found"})
                    break

                runner = AgentRunner(agent, db)
                response = await runner.run(
                    user_input=user_input,
                    session_id=session_id,
                    channel=ChannelType.UI,
                )

            await websocket.send_json({
                "type": "message",
                "response": response,
                "session_id": session_id,
            })

    except WebSocketDisconnect:
        pass


# ─────────────────────────────────────────────
#  Message History
# ─────────────────────────────────────────────

@router.get("/{agent_id}/messages/{session_id}")
async def get_messages(
    agent_id: str,
    session_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Message)
        .where(Message.agent_id == agent_id, Message.session_id == session_id)
        .order_by(Message.created_at)
        .limit(limit)
    )
    return [m.to_dict() for m in result.scalars().all()]


@router.get("/{agent_id}/sessions")
async def get_sessions(agent_id: str, db: AsyncSession = Depends(get_db)):
    """Return distinct session IDs for an agent."""
    from sqlalchemy import distinct
    result = await db.execute(
        select(distinct(Message.session_id))
        .where(Message.agent_id == agent_id)
    )
    return [row[0] for row in result.all()]


# ─────────────────────────────────────────────
#  Channel Config
# ─────────────────────────────────────────────

@router.post("/{agent_id}/channels")
async def configure_channel(
    agent_id: str,
    payload: ChannelConfigCreate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Agent).where(Agent.id == agent_id))
    if not result.scalar_one_or_none():
        raise HTTPException(404, "Agent not found")

    # Check for existing config
    existing = await db.execute(
        select(ChannelConfig)
        .where(ChannelConfig.agent_id == agent_id, ChannelConfig.channel_type == payload.channel_type)
    )
    cfg = existing.scalar_one_or_none()
    if cfg:
        cfg.config = payload.config
        cfg.is_active = True
    else:
        cfg = ChannelConfig(
            agent_id=agent_id,
            channel_type=payload.channel_type,
            config=payload.config,
        )
        db.add(cfg)

    await db.flush()

    # Start the bot
    try:
        await start_channel(agent_id, payload.channel_type, payload.config)
    except Exception as e:
        raise HTTPException(400, f"Failed to start channel: {e}")

    await db.commit()
    return cfg.to_dict()


@router.delete("/{agent_id}/channels/{channel_type}")
async def remove_channel(
    agent_id: str,
    channel_type: str,
    db: AsyncSession = Depends(get_db),
):
    await stop_channel(agent_id, channel_type)
    result = await db.execute(
        select(ChannelConfig)
        .where(ChannelConfig.agent_id == agent_id, ChannelConfig.channel_type == channel_type)
    )
    cfg = result.scalar_one_or_none()
    if cfg:
        await db.delete(cfg)
        await db.commit()
    return {"status": "stopped"}
