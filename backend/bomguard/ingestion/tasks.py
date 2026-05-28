"""Celery scraping tasks."""

from bomguard.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3)
def scrape_echa(self: object) -> dict:
    """Scrape ECHA REACH SVHC data."""
    return {"status": "not_implemented"}


@celery_app.task(bind=True, max_retries=3)
def scrape_epa(self: object) -> dict:
    """Scrape EPA CompTox data."""
    return {"status": "not_implemented"}
