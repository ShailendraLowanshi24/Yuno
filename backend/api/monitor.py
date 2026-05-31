"""
Monitoring API — real-time logs, inter-agent messages, token/cost tracking.
WebSocket endpoint for live log streaming.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Optional
from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import RunLog, WorkflowRun, Message, Agent, RunStatus, get_db
from ..db.session import AsyncSessionLocal

router = APIRouter(prefix="/monitor", tags=["Monitoring"])
logger = logging.getLogger(__name__)

# Active WebSocket connections for log streaming
_log_subscribers: list[WebSocket] = []


async def broadcast_log(log_dict: dict):
    """Broadcast a log entry to all connected WebSocket clients."""
    dead = []
    for ws in _log_subscribers:
        try:
            await ws.send_json(log_dict)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _log_subscribers.remove(ws)


@router.websocket("/ws/logs")
async def stream_logs(websocket: WebSocket):
    """WebSocket endpoint for real-time log streaming."""
    await websocket.accept()
    _log_subscribers.append(websocket)
    try:
        # Send last 50 logs immediately
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(RunLog).order_by(desc(RunLog.timestamp)).limit(50)
            )
            logs = list(reversed(result.scalars().all()))
            for log in logs:
                await websocket.send_json({**log.to_dict(), "historic": True})

        # Keep connection alive
        while True:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                await websocket.send_json({"type": "ping"})

    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _log_subscribers:
            _log_subscribers.remove(websocket)


@router.get("/logs")
async def get_logs(
    agent_id: Optional[str] = None,
    run_id: Optional[str] = None,
    level: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    query = select(RunLog).order_by(desc(RunLog.timestamp)).limit(limit)
    if agent_id:
        query = query.where(RunLog.agent_id == agent_id)
    if run_id:
        query = query.where(RunLog.run_id == run_id)
    if level:
        query = query.where(RunLog.level == level)

    result = await db.execute(query)
    return [l.to_dict() for l in reversed(result.scalars().all())]


@router.get("/stats")
async def get_stats(db: AsyncSession = Depends(get_db)):
    """Return platform-wide statistics."""
    # Agent count
    agent_count = (await db.execute(select(func.count(Agent.id)))).scalar()

    # Total runs
    total_runs = (await db.execute(select(func.count(WorkflowRun.id)))).scalar()

    # Runs by status
    completed = (await db.execute(
        select(func.count(WorkflowRun.id))
        .where(WorkflowRun.status == RunStatus.COMPLETED)
    )).scalar()

    failed = (await db.execute(
        select(func.count(WorkflowRun.id))
        .where(WorkflowRun.status == RunStatus.FAILED)
    )).scalar()

    running = (await db.execute(
        select(func.count(WorkflowRun.id))
        .where(WorkflowRun.status == RunStatus.RUNNING)
    )).scalar()

    # Total tokens & cost
    token_result = await db.execute(
        select(func.sum(RunLog.tokens_used), func.sum(RunLog.cost))
    )
    tokens_row = token_result.one()
    total_tokens = tokens_row[0] or 0
    total_cost = tokens_row[1] or 0.0

    # Total messages
    total_messages = (await db.execute(select(func.count(Message.id)))).scalar()

    # Recent runs
    recent_result = await db.execute(
        select(WorkflowRun)
        .order_by(desc(WorkflowRun.started_at))
        .limit(5)
    )
    recent_runs = [r.to_dict() for r in recent_result.scalars().all()]

    return {
        "agents": agent_count,
        "total_runs": total_runs,
        "completed_runs": completed,
        "failed_runs": failed,
        "running_runs": running,
        "total_tokens": total_tokens,
        "total_cost_usd": round(total_cost, 6),
        "total_messages": total_messages,
        "recent_runs": recent_runs,
    }


@router.get("/messages")
async def get_inter_agent_messages(
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    """Return recent inter-agent messages (agent → agent channel = UI/workflow)."""
    result = await db.execute(
        select(Message)
        .order_by(desc(Message.created_at))
        .limit(limit)
    )
    return [m.to_dict() for m in reversed(result.scalars().all())]
