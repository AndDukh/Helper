"""Telegram bot service — polling-based message handler.

Runs inside the backend process as a Celery background task so that the
bot shares the same environment (env-vars, service instances) as the
FastAPI application without requiring a separate container.
"""

import asyncio
import logging
import os

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from .assistant_service import AssistantService

logger = logging.getLogger(__name__)

_assistant = AssistantService()


async def _cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /start command — greet the user."""
    await update.effective_message.reply_text(
        "👋 Hello! I'm your Helper assistant.\n\n"
        "Send me any task or question and I'll do my best to help you."
    )


async def _cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle the /help command."""
    await update.effective_message.reply_text(
        "📋 *Available commands*\n\n"
        "/start — welcome message\n"
        "/help  — this help text\n\n"
        "Or just send me a plain text message with your task.",
        parse_mode="Markdown",
    )


async def _handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Forward every plain-text message to AssistantService and reply."""
    message = update.effective_message
    if not message or not message.text:
        return

    task = message.text.strip()
    if not task:
        return

    await message.reply_text("⏳ Processing your request…")

    try:
        result = await _assistant.execute(task=task)
    except Exception as exc:  # noqa: BLE001
        logger.exception("AssistantService error for task %r: %s", task, exc)
        await message.reply_text("❌ An error occurred while processing your request. Please try again.")
        return

    status = result.get("status", "")
    artifact = result.get("artifact", "").strip()
    summary = result.get("summary", "").strip()

    reply_parts: list[str] = []
    if summary:
        reply_parts.append(f"*Summary:* {summary}")
    if artifact:
        reply_parts.append(artifact)
    if not reply_parts:
        reply_parts.append(f"Status: {status}")

    await message.reply_text("\n\n".join(reply_parts), parse_mode="Markdown")


class TelegramBot:
    """Wraps python-telegram-bot Application for use inside the backend."""

    def __init__(self) -> None:
        self._token: str = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()

    def is_configured(self) -> bool:
        return bool(self._token)

    def run_polling(self) -> None:
        """Build the Application and start long-polling (blocking call).

        Intended to be executed inside a dedicated thread or process so it
        does not block the FastAPI event loop.
        """
        if not self._token:
            logger.error("TELEGRAM_BOT_TOKEN is not set — bot polling will not start.")
            return

        application = Application.builder().token(self._token).build()
        application.add_handler(CommandHandler("start", _cmd_start))
        application.add_handler(CommandHandler("help", _cmd_help))
        application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, _handle_message)
        )

        logger.info("Starting Telegram bot polling (backend service)…")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
