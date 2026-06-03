"""Celery tasks for regulatory summary generation."""

import asyncio
from typing import Any

from bomguard.celery_app import celery_app
from bomguard.config import Settings
from bomguard.db import SessionLocal
from bomguard.services.openrouter_client import OpenRouterClient
from bomguard.services.summary_generator import SummaryGenerator

settings = Settings()


def _get_generator() -> SummaryGenerator:
    """Create a SummaryGenerator from application settings."""
    client = OpenRouterClient(
        api_key=settings.openrouter_api_key or "",
        http_referer="https://github.com/effyyang/bomguard",
        x_title="BOMGuard",
    )
    return SummaryGenerator(
        openrouter_client=client,
        gemini_api_key=settings.gemini_api_key,
    )


@celery_app.task(bind=True, max_retries=3)
def generate_regulatory_summaries(
    self: Any, batch_size: int = 50
) -> dict[str, Any]:
    """Generate summaries for a batch of substances without them."""
    generator = _get_generator()
    db = SessionLocal()
    try:
        summaries = asyncio.run(
            generator.process_batch(db, batch_size=batch_size)
        )
        return {
            "generated": len(summaries),
            "substance_ids": [
                s.substance_id for s in summaries if s.substance_id
            ],
        }
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60) from exc
    finally:
        db.close()


@celery_app.task
def generate_all_summaries(batch_size: int = 50) -> dict[str, Any]:
    """Backfill summaries for all substances that lack them."""
    generator = _get_generator()
    db = SessionLocal()
    total_generated = 0
    try:
        while True:
            batch = asyncio.run(
                generator.process_batch(db, batch_size=batch_size)
            )
            if not batch:
                break
            total_generated += len(batch)
        return {"total_generated": total_generated}
    finally:
        db.close()
