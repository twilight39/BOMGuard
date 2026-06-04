"""Celery scraping tasks."""

from typing import Any

from bomguard.celery_app import celery_app
from bomguard.db import SessionLocal
from bomguard.enrichment.tasks import enrich_substance
from bomguard.ingestion.pipeline import run_scraper
from bomguard.ingestion.registry import get_all_scrapers, get_scraper


@celery_app.task(bind=True, max_retries=3)
def scrape_regulation(self: Any, regulation_id: str) -> dict[str, Any]:
    """Scrape a single regulation and trigger enrichment for new substances."""
    scraper = get_scraper(regulation_id)
    if not scraper:
        raise ValueError(f"No scraper found for regulation {regulation_id}")

    db = SessionLocal()
    try:
        result = run_scraper(scraper, db)
    finally:
        db.close()

    # Trigger enrichment for newly created substances
    for substance_id in result.new_substance_ids:
        enrich_substance.delay(substance_id)

    return {
        "regulation_id": result.regulation_id,
        "source_name": result.source_name,
        "total_fetched": result.total_fetched,
        "substances_created": result.substances_created,
        "substances_updated": result.substances_updated,
        "statuses_created": result.statuses_created,
        "changes_detected": result.changes_detected,
    }


@celery_app.task
def scrape_all_regulations() -> list[dict[str, Any]]:
    """Scrape all registered regulations and trigger enrichment for new substances."""
    scrapers = get_all_scrapers()
    results: list[dict[str, Any]] = []
    for scraper in scrapers:
        db = SessionLocal()
        try:
            result = run_scraper(scraper, db)
        finally:
            db.close()

        # Trigger enrichment for newly created substances
        for substance_id in result.new_substance_ids:
            enrich_substance.delay(substance_id)

        results.append(
            {
                "regulation_id": result.regulation_id,
                "source_name": result.source_name,
                "total_fetched": result.total_fetched,
                "changes_detected": result.changes_detected,
            }
        )
    return results
