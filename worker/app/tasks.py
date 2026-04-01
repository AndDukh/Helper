from .celery_app import celery_app


@celery_app.task(name="health.ping")
def ping() -> dict[str, str]:
    return {"worker": "ok"}
