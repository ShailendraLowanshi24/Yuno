"""
Channel Manager — unified interface for all messaging channel integrations.
"""

from __future__ import annotations

import logging
from ..db import ChannelType

logger = logging.getLogger(__name__)


async def start_channel(agent_id: str, channel_type: str, config: dict):
    """Start a messaging channel bot for an agent."""
    if channel_type == ChannelType.TELEGRAM:
        from .telegram import start_telegram_bot
        token = config.get("bot_token")
        if not token:
            raise ValueError("Telegram requires 'bot_token' in config")
        await start_telegram_bot(agent_id, token)

    elif channel_type == ChannelType.SLACK:
        from .slack import start_slack_bot
        bot_token = config.get("bot_token")
        app_token = config.get("app_token")
        if not bot_token or not app_token:
            raise ValueError("Slack requires 'bot_token' and 'app_token'")
        await start_slack_bot(agent_id, bot_token, app_token)

    else:
        logger.warning(f"Channel type '{channel_type}' start not implemented")


async def stop_channel(agent_id: str, channel_type: str):
    """Stop a running channel bot for an agent."""
    if channel_type == ChannelType.TELEGRAM:
        from .telegram import stop_telegram_bot
        await stop_telegram_bot(agent_id)

    elif channel_type == ChannelType.SLACK:
        from .slack import stop_slack_bot
        await stop_slack_bot(agent_id)


async def restart_all_channels():
    """Called on server startup to re-activate all saved channel configs."""
    try:
        from .telegram import restart_all_telegram_bots
        await restart_all_telegram_bots()
    except Exception as e:
        logger.error(f"Failed to restart Telegram bots: {e}")

    try:
        from .slack import restart_all_slack_bots
        await restart_all_slack_bots()
    except Exception as e:
        logger.error(f"Failed to restart Slack bots: {e}")
