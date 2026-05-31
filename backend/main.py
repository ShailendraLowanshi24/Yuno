"""
Yuno AI Agent Orchestration Platform — FastAPI Application.

Architecture:
  - FastAPI (async REST + WebSocket)
  - LangGraph (agent runtime with tool calling + cycles)
  - SQLAlchemy async + SQLite (dev) or PostgreSQL (prod)
  - APScheduler (cron-based agent triggers)
  - python-telegram-bot / slack-sdk (messaging channels)
  - React + React Flow frontend (served separately)

Why LangGraph over CrewAI/AutoGen?
  - Explicit graph structure maps 1:1 to our visual workflow builder
  - Async-native (matches FastAPI)
  - Supports feedback loops and conditional edges natively
  - No black-box orchestration — full control over agent execution
  - Checkpointing works well with our SQLite message history
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

from .db import init_db
from .api.agents import router as agents_router
from .api.workflows import router as workflows_router
from .api.monitor import router as monitor_router
from .channels import restart_all_channels
from .agents.scheduler import start_scheduler, reload_all_schedules

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("🚀 Yuno AI Platform starting up...")

    # 1. Initialize database
    await init_db()
    logger.info("✅ Database initialized")

    # 2. Start scheduler
    start_scheduler()
    await reload_all_schedules()
    logger.info("✅ Scheduler started")

    # 3. Restart persisted channel bots
    await restart_all_channels()
    logger.info("✅ Channel bots restarted")

    logger.info("✅ Yuno AI Platform is ready")
    yield

    logger.info("🛑 Yuno AI Platform shutting down...")
    from .agents.scheduler import stop_scheduler
    stop_scheduler()


app = FastAPI(
    title="Yuno AI Agent Orchestration Platform",
    description=(
        "Build, configure, and connect AI agents into collaborative workflows. "
        "Agents run on LangGraph, communicate asynchronously, and are reachable "
        "via Telegram, Slack, or WhatsApp."
    ),
    version="1.0.0",
    lifespan=lifespan,
)

# CORS
cors_origins = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(agents_router, prefix="/api")
app.include_router(workflows_router, prefix="/api")
app.include_router(monitor_router, prefix="/api")


@app.get("/")
async def root():
    return {
        "name": "Yuno AI Agent Orchestration Platform",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health")
async def health():
    return {"status": "healthy"}
