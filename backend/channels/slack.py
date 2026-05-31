"""
Slack Channel Integration using Socket Mode.

Uses slack-sdk with Socket Mode so no public webhook URL is required —
works fully locally.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Optional

from sqlalchemy import select
from slack_sdk.web.async_client import AsyncWebClient
from slack_sdk.socket_mode.aiohttp import SocketModeClient
from slack_sdk.socket_mode.response import SocketModeResponse
from slack_sdk.socket_mode.request import SocketModeRequest

from ..db import Agent, ChannelConfig, ChannelType
from ..db.session import AsyncSessionLocal
from ..agents.runtime import AgentRunner

logger = logging.getLogger(__name__)

_running_slack: dict[str, SocketModeClient] = {}


async def start_slack_bot(agent_id: str, bot_token: str, app_token: str):
    """Start a Slack Socket Mode bot for the given agent."""
    if agent_id in _running_slack:
        await stop_slack_bot(agent_id)

    web_client = AsyncWebClient(token=bot_token)
    socket_client = SocketModeClient(app_token=app_token, web_client=web_client)

    async def handle_events(client: SocketModeClient, req: SocketModeRequest):
        # Acknowledge immediately
        await client.send_socket_mode_response(SocketModeResponse(envelope_id=req.envelope_id))

        if req.type != "events_api":
            return

        event = req.payload.get("event", {})
        if event.get("type") != "message":
            return
        if event.get("subtype"):  # bot_message, message_changed etc.
            return
        if event.get("bot_id"):  # ignore our own messages
            return

        text = event.get("text", "").strip()
        channel_id = event.get("channel", "")
        user_id = event.get("user", "")
        session_id = f"slack-{channel_id}"

        if not text:
            return

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if not agent:
                return

            runner = AgentRunner(agent, db)
            try:
                response = await runner.run(
                    user_input=text,
                    session_id=session_id,
                    channel=ChannelType.SLACK,
                    channel_user_id=user_id,
                )
            except Exception as e:
                logger.exception("Slack agent run error")
                response = f"Sorry, I encountered an error: {e}"

        # Post response
        try:
            await web_client.chat_postMessage(
                channel=channel_id,
                text=response,
                mrkdwn=True,
            )
        except Exception as e:
            logger.error(f"Failed to post Slack message: {e}")

    socket_client.socket_mode_request_listeners.append(handle_events)
    _running_slack[agent_id] = socket_client

    asyncio.create_task(_run_slack(socket_client, agent_id))
    logger.info(f"Slack bot started for agent {agent_id}")


async def _run_slack(client: SocketModeClient, agent_id: str):
    try:
        await client.connect()
        while agent_id in _running_slack:
            await asyncio.sleep(1)
    except Exception as e:
        logger.error(f"Slack bot error for agent {agent_id}: {e}")
    finally:
        try:
            await client.close()
        except Exception:
            pass


async def stop_slack_bot(agent_id: str):
    client = _running_slack.pop(agent_id, None)
    if client:
        try:
            await client.close()
        except Exception:
            pass
    logger.info(f"Slack bot stopped for agent {agent_id}")


async def restart_all_slack_bots():
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ChannelConfig)
            .where(ChannelConfig.channel_type == ChannelType.SLACK)
            .where(ChannelConfig.is_active == True)
        )
        configs = result.scalars().all()

    for cfg in configs:
        bot_token = cfg.config.get("bot_token")
        app_token = cfg.config.get("app_token")
        if bot_token and app_token:
            try:
                await start_slack_bot(cfg.agent_id, bot_token, app_token)
            except Exception as e:
                logger.error(f"Failed to restart Slack bot for agent {cfg.agent_id}: {e}")
