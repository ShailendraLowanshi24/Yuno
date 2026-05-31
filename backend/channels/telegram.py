"""
Telegram Channel Integration.

Registers a Telegram bot that forwards messages to a configured agent.
The bot token is stored in the agent's ChannelConfig.
Uses python-telegram-bot v21 (async).
"""

from __future__ import annotations

import asyncio
import logging
import os
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import selectinload
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

from ..db import Agent, ChannelConfig, ChannelType
from ..db.session import AsyncSessionLocal
from ..agents.runtime import AgentRunner

logger = logging.getLogger(__name__)

# Registry of running bots: agent_id → Application
_running_bots: dict[str, Application] = {}


async def start_telegram_bot(agent_id: str, token: str):
    """Start a Telegram bot for the given agent."""
    if agent_id in _running_bots:
        await stop_telegram_bot(agent_id)

    app = Application.builder().token(token).build()

    async def start_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
        name = agent.name if agent else "AI Agent"
        await update.message.reply_text(
            f"👋 Hello! I'm *{name}*. How can I help you today?",
            parse_mode="Markdown",
        )

    async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
        if not update.message or not update.message.text:
            return

        user_id = str(update.effective_user.id)
        chat_id = str(update.effective_chat.id)
        session_id = f"telegram-{chat_id}"
        user_text = update.message.text

        # Show typing indicator
        await context.bot.send_chat_action(chat_id=chat_id, action="typing")

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(Agent).where(Agent.id == agent_id))
            agent = result.scalar_one_or_none()
            if not agent:
                await update.message.reply_text("⚠️ Agent not found.")
                return

            runner = AgentRunner(agent, db)
            try:
                response = await runner.run(
                    user_input=user_text,
                    session_id=session_id,
                    channel=ChannelType.TELEGRAM,
                    channel_user_id=user_id,
                )
            except Exception as e:
                logger.exception("Telegram agent run error")
                response = f"Sorry, I encountered an error: {e}"

        # Telegram max message length is 4096 chars
        for chunk in _split_message(response, 4096):
            await update.message.reply_text(chunk)

    app.add_handler(CommandHandler("start", start_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    _running_bots[agent_id] = app

    # Run in background
    asyncio.create_task(_run_polling(app, agent_id))
    logger.info(f"Telegram bot started for agent {agent_id}")


async def _run_polling(app: Application, agent_id: str):
    try:
        await app.initialize()
        await app.start()
        await app.updater.start_polling(allowed_updates=Update.ALL_TYPES)
        logger.info(f"Telegram polling active for agent {agent_id}")
        # Keep running indefinitely
        while agent_id in _running_bots:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    except Exception as e:
        logger.error(f"Telegram bot error for agent {agent_id}: {e}")
    finally:
        try:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
        except Exception:
            pass


async def stop_telegram_bot(agent_id: str):
    """Stop and remove a running Telegram bot."""
    app = _running_bots.pop(agent_id, None)
    if app:
        try:
            await app.updater.stop()
            await app.stop()
            await app.shutdown()
        except Exception as e:
            logger.warning(f"Error stopping Telegram bot: {e}")
    logger.info(f"Telegram bot stopped for agent {agent_id}")


async def restart_all_telegram_bots():
    """Called on server startup to re-register all saved Telegram channel configs."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(ChannelConfig)
            .where(ChannelConfig.channel_type == ChannelType.TELEGRAM)
            .where(ChannelConfig.is_active == True)
        )
        configs = result.scalars().all()

    for cfg in configs:
        token = cfg.config.get("bot_token")
        if token:
            try:
                await start_telegram_bot(cfg.agent_id, token)
            except Exception as e:
                logger.error(f"Failed to restart Telegram bot for agent {cfg.agent_id}: {e}")


def _split_message(text: str, max_len: int) -> list[str]:
    """Split a long message into chunks."""
    if len(text) <= max_len:
        return [text]
    chunks = []
    while text:
        chunks.append(text[:max_len])
        text = text[max_len:]
    return chunks
