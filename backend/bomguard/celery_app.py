"""Celery configuration."""

from celery import Celery

from bomguard.config import Settings

settings = Settings()

celery_app = Celery(
    "bomguard",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["bomguard.ingestion.tasks", "bomguard.enrichment.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,
)
