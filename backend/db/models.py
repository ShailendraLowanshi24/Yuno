"""
Database models for Yuno AI Agent Orchestration Platform.
Uses SQLAlchemy 2.0 async ORM with SQLite (dev) or Postgres (prod).
"""

from __future__ import annotations
import uuid
from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    String, Text, Boolean, DateTime, Integer, Float,
    ForeignKey, JSON, Enum as SAEnum
)
from sqlalchemy.orm import (
    DeclarativeBase, Mapped, mapped_column, relationship
)
import enum


def new_uuid() -> str:
    return str(uuid.uuid4())


def utcnow() -> datetime:
    return datetime.utcnow()


class Base(DeclarativeBase):
    pass


# ─────────────────────────────────────────────
#  Enumerations
# ─────────────────────────────────────────────

class AgentStatus(str, enum.Enum):
    ACTIVE = "active"
    IDLE = "idle"
    RUNNING = "running"
    ERROR = "error"
    DISABLED = "disabled"


class WorkflowStatus(str, enum.Enum):
    DRAFT = "draft"
    ACTIVE = "active"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    PAUSED = "paused"


class MessageRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"
    TOOL = "tool"
    AGENT = "agent"


class ChannelType(str, enum.Enum):
    TELEGRAM = "telegram"
    SLACK = "slack"
    WHATSAPP = "whatsapp"
    API = "api"
    UI = "ui"


class RunStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ─────────────────────────────────────────────
#  Agent
# ─────────────────────────────────────────────

class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(String(128), nullable=False)
    system_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    model: Mapped[str] = mapped_column(String(64), default="gpt-4o-mini")
    provider: Mapped[str] = mapped_column(String(32), default="openai")  # openai | anthropic
    status: Mapped[AgentStatus] = mapped_column(SAEnum(AgentStatus), default=AgentStatus.IDLE)

    # Capabilities
    tools: Mapped[list] = mapped_column(JSON, default=list)          # list of tool names
    skills: Mapped[list] = mapped_column(JSON, default=list)
    channels: Mapped[list] = mapped_column(JSON, default=list)       # ChannelType list
    guardrails: Mapped[dict] = mapped_column(JSON, default=dict)

    # Memory & limits
    memory_enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    memory_window: Mapped[int] = mapped_column(Integer, default=20)  # last N messages
    max_tokens: Mapped[int] = mapped_column(Integer, default=2048)
    temperature: Mapped[float] = mapped_column(Float, default=0.7)
    max_iterations: Mapped[int] = mapped_column(Integer, default=10)

    # Schedule (cron expression, None = not scheduled)
    schedule: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    schedule_prompt: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Interaction rules / persona
    interaction_rules: Mapped[dict] = mapped_column(JSON, default=dict)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # Relationships
    messages: Mapped[List["Message"]] = relationship("Message", back_populates="agent", cascade="all, delete-orphan")
    workflow_nodes: Mapped[List["WorkflowNode"]] = relationship("WorkflowNode", back_populates="agent")
    run_logs: Mapped[List["RunLog"]] = relationship("RunLog", back_populates="agent", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role,
            "system_prompt": self.system_prompt,
            "model": self.model,
            "provider": self.provider,
            "status": self.status,
            "tools": self.tools,
            "skills": self.skills,
            "channels": self.channels,
            "guardrails": self.guardrails,
            "memory_enabled": self.memory_enabled,
            "memory_window": self.memory_window,
            "max_tokens": self.max_tokens,
            "temperature": self.temperature,
            "max_iterations": self.max_iterations,
            "schedule": self.schedule,
            "schedule_prompt": self.schedule_prompt,
            "interaction_rules": self.interaction_rules,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


# ─────────────────────────────────────────────
#  Workflow
# ─────────────────────────────────────────────

class Workflow(Base):
    __tablename__ = "workflows"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[WorkflowStatus] = mapped_column(SAEnum(WorkflowStatus), default=WorkflowStatus.DRAFT)
    is_template: Mapped[bool] = mapped_column(Boolean, default=False)
    template_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    # Graph layout stored as JSON (nodes + edges for React Flow)
    graph_layout: Mapped[dict] = mapped_column(JSON, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    nodes: Mapped[List["WorkflowNode"]] = relationship("WorkflowNode", back_populates="workflow", cascade="all, delete-orphan")
    edges: Mapped[List["WorkflowEdge"]] = relationship("WorkflowEdge", back_populates="workflow", cascade="all, delete-orphan")
    runs: Mapped[List["WorkflowRun"]] = relationship("WorkflowRun", back_populates="workflow", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "is_template": self.is_template,
            "template_name": self.template_name,
            "graph_layout": self.graph_layout,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "nodes": [n.to_dict() for n in self.nodes],
            "edges": [e.to_dict() for e in self.edges],
        }


class WorkflowNode(Base):
    __tablename__ = "workflow_nodes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflows.id"), nullable=False)
    agent_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True)
    node_type: Mapped[str] = mapped_column(String(32), default="agent")  # agent | condition | input | output | tool
    label: Mapped[str] = mapped_column(String(128), nullable=False)
    position_x: Mapped[float] = mapped_column(Float, default=0)
    position_y: Mapped[float] = mapped_column(Float, default=0)
    config: Mapped[dict] = mapped_column(JSON, default=dict)  # node-specific config

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="nodes")
    agent: Mapped[Optional["Agent"]] = relationship("Agent", back_populates="workflow_nodes")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "agent_id": self.agent_id,
            "node_type": self.node_type,
            "label": self.label,
            "position": {"x": self.position_x, "y": self.position_y},
            "config": self.config,
        }


class WorkflowEdge(Base):
    __tablename__ = "workflow_edges"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflows.id"), nullable=False)
    source_node_id: Mapped[str] = mapped_column(String(36), nullable=False)
    target_node_id: Mapped[str] = mapped_column(String(36), nullable=False)
    condition: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # Python expression string
    label: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="edges")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "source": self.source_node_id,
            "target": self.target_node_id,
            "condition": self.condition,
            "label": self.label,
        }


# ─────────────────────────────────────────────
#  Workflow Run
# ─────────────────────────────────────────────

class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    workflow_id: Mapped[str] = mapped_column(String(36), ForeignKey("workflows.id"), nullable=False)
    status: Mapped[RunStatus] = mapped_column(SAEnum(RunStatus), default=RunStatus.PENDING)
    trigger: Mapped[str] = mapped_column(String(32), default="manual")  # manual | schedule | channel
    input_data: Mapped[dict] = mapped_column(JSON, default=dict)
    output_data: Mapped[dict] = mapped_column(JSON, default=dict)
    error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    total_tokens: Mapped[int] = mapped_column(Integer, default=0)
    total_cost: Mapped[float] = mapped_column(Float, default=0.0)
    started_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    workflow: Mapped["Workflow"] = relationship("Workflow", back_populates="runs")
    logs: Mapped[List["RunLog"]] = relationship("RunLog", back_populates="run", cascade="all, delete-orphan")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "workflow_id": self.workflow_id,
            "status": self.status,
            "trigger": self.trigger,
            "input_data": self.input_data,
            "output_data": self.output_data,
            "error": self.error,
            "total_tokens": self.total_tokens,
            "total_cost": self.total_cost,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class RunLog(Base):
    __tablename__ = "run_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    run_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("workflow_runs.id"), nullable=True)
    agent_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("agents.id"), nullable=True)
    level: Mapped[str] = mapped_column(String(16), default="info")  # info | warning | error | debug
    event: Mapped[str] = mapped_column(String(64), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    tokens_used: Mapped[int] = mapped_column(Integer, default=0)
    cost: Mapped[float] = mapped_column(Float, default=0.0)
    timestamp: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    run: Mapped[Optional["WorkflowRun"]] = relationship("WorkflowRun", back_populates="logs")
    agent: Mapped[Optional["Agent"]] = relationship("Agent", back_populates="run_logs")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "run_id": self.run_id,
            "agent_id": self.agent_id,
            "level": self.level,
            "event": self.event,
            "message": self.message,
            "metadata": self.metadata,
            "tokens_used": self.tokens_used,
            "cost": self.cost,
            "timestamp": self.timestamp.isoformat(),
        }


# ─────────────────────────────────────────────
#  Messages (conversation history)
# ─────────────────────────────────────────────

class Message(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    session_id: Mapped[str] = mapped_column(String(64), nullable=False)  # conversation thread id
    role: Mapped[MessageRole] = mapped_column(SAEnum(MessageRole), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    channel: Mapped[ChannelType] = mapped_column(SAEnum(ChannelType), default=ChannelType.UI)
    channel_user_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    tool_calls: Mapped[Optional[list]] = mapped_column(JSON, nullable=True)
    tool_call_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    tokens: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    agent: Mapped["Agent"] = relationship("Agent", back_populates="messages")

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "session_id": self.session_id,
            "role": self.role,
            "content": self.content,
            "channel": self.channel,
            "channel_user_id": self.channel_user_id,
            "tool_calls": self.tool_calls,
            "tool_call_id": self.tool_call_id,
            "tokens": self.tokens,
            "created_at": self.created_at.isoformat(),
        }


# ─────────────────────────────────────────────
#  Channel Config
# ─────────────────────────────────────────────

class ChannelConfig(Base):
    __tablename__ = "channel_configs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_uuid)
    agent_id: Mapped[str] = mapped_column(String(36), ForeignKey("agents.id"), nullable=False)
    channel_type: Mapped[ChannelType] = mapped_column(SAEnum(ChannelType), nullable=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)  # bot token, webhook etc.
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "channel_type": self.channel_type,
            "config": {k: "***" if "token" in k.lower() or "secret" in k.lower() else v
                       for k, v in self.config.items()},
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
        }
