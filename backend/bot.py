"""Celery task entry point for the Telegram bot polling service.

Usage (run from the backend/ directory or inside the backend container):

    celery -A bot.celery_app worker --loglevel=info

The single task ``bot.run_telegram_bot`` is dispatched by FastAPI on startup
(see app/main.py) and runs the blocking polling loop inside a Celery worker
process, keeping it completely separate from the async FastAPI event loop.
"""

import os

from celery import Celery

redis_url = os.getenv("REDIS_URL", "redis://redis:6379/0")

celery_app = Celery("telegram_bot_worker", broker=redis_url, backend=redis_url)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    # Keep only one copy of the polling task alive at a time.
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)


@celery_app.task(name="bot.run_telegram_bot", bind=True, max_retries=None)
def run_telegram_bot(self) -> None:  # type: ignore[override]
    """Start Telegram bot long-polling.  Runs until the worker is stopped."""
    from app.services.telegram_bot import TelegramBot  # local import avoids circular deps

    bot = TelegramBot()
    if not bot.is_configured():
        return  # nothing to do — token not set

    try:
        bot.run_polling()
    except Exception as exc:  # noqa: BLE001
        # Retry after 10 s so the bot recovers from transient network errors.
        raise self.retry(exc=exc, countdown=10)
