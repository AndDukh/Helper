import logging
import os
import sys

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, WebAppInfo
from telegram.ext import Application, CommandHandler, ContextTypes

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    webapp_url = os.getenv("WEBAPP_URL", "").strip().rstrip("/")
    if not webapp_url:
        await update.effective_message.reply_text(
            "WEBAPP_URL is not set. Add HTTPS Mini App URL to .env and restart the bot container."
        )
        return

    keyboard = InlineKeyboardMarkup(
        [[InlineKeyboardButton("Open Helper", web_app=WebAppInfo(url=f"{webapp_url}/"))]]
    )
    await update.effective_message.reply_text(
        "Helper Mini App — tap the button below.",
        reply_markup=keyboard,
    )


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN is missing")
        sys.exit(1)

    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    logger.info("Starting Telegram bot polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
