"""
Agent Scheduler — runs agents on a cron schedule using APScheduler.
"""

from __future__ import annotations

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from ..db import Agent, AgentStatus, ChannelType
from ..db.session import AsyncSessionLocal
from ..agents.runtime import AgentRunner

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler()


def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started")


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)


async def register_agent_schedule(agent_id: str, cron_expr: str, prompt: str):
    """Register or update a cron job for an agent."""
    job_id = f"agent_schedule_{agent_id}"

    # Remove existing job if any
    existing = scheduler.get_job(job_id)
    if existing:
        scheduler.remove_job(job_id)

    try:
        parts = cron_expr.strip().split()
        if len(parts) != 5:
            raise ValueError("Cron expression must have 5 fields: minute hour day month day_of_week")

        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4],
        )
        scheduler.add_job(
            _run_scheduled_agent,
            trigger=trigger,
            id=job_id,
            args=[agent_id, prompt],
            replace_existing=True,
        )
        logger.info(f"Registered schedule '{cron_expr}' for agent {agent_id}")
    except Exception as e:
        logger.error(f"Failed to register schedule for agent {agent_id}: {e}")
        raise


async def unregister_agent_schedule(agent_id: str):
    """Remove a scheduled job for an agent."""
    job_id = f"agent_schedule_{agent_id}"
    job = scheduler.get_job(job_id)
    if job:
        scheduler.remove_job(job_id)
        logger.info(f"Unregistered schedule for agent {agent_id}")


async def _run_scheduled_agent(agent_id: str, prompt: str):
    """Scheduled task: run an agent with a preset prompt."""
    import uuid
    session_id = f"scheduled-{uuid.uuid4().hex[:8]}"

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(Agent).where(Agent.id == agent_id))
        agent = result.scalar_one_or_none()
        if not agent or agent.status == AgentStatus.DISABLED:
            return

        runner = AgentRunner(agent, db)
        try:
            await runner.run(
                user_input=prompt,
                session_id=session_id,
                channel=ChannelType.UI,
            )
            logger.info(f"Scheduled run completed for agent {agent_id}")
        except Exception as e:
            logger.error(f"Scheduled run failed for agent {agent_id}: {e}")


async def reload_all_schedules():
    """Load all agent schedules from DB on startup."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Agent).where(Agent.schedule.isnot(None))
        )
        agents = result.scalars().all()

    for agent in agents:
        if agent.schedule and agent.schedule_prompt:
            try:
                await register_agent_schedule(
                    agent.id, agent.schedule, agent.schedule_prompt
                )
            except Exception as e:
                logger.error(f"Failed to reload schedule for agent {agent.id}: {e}")
