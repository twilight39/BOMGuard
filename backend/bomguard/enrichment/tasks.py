"""Celery enrichment tasks."""

from typing import Any

from bomguard.celery_app import celery_app
from bomguard.db import SessionLocal
from bomguard.enrichment.pipeline import EnrichmentPipeline


@celery_app.task
def enrich_substance(substance_id: int) -> dict[str, Any]:
    """Enrich a single substance by ID."""
    import asyncio

    db = SessionLocal()
    try:
        from bomguard.models.database import Substance

        substance = db.query(Substance).filter_by(id=substance_id).first()
        if not substance:
            return {"substance_id": substance_id, "status": "not_found"}

        pipeline = EnrichmentPipeline(db)
        result = asyncio.run(pipeline.enrich_substance(substance))
        return {
            "substance_id": substance_id,
            "status": "enriched",
            "has_smiles": result.has_smiles,
            "has_epa_data": result.has_epa_data,
        }
    finally:
        db.close()


@celery_app.task
def enrich_all_missing(batch_size: int = 50) -> dict[str, Any]:
    """Enrich all substances missing properties."""
    import asyncio

    db = SessionLocal()
    try:
        pipeline = EnrichmentPipeline(db)
        return asyncio.run(pipeline.enrich_all_missing(batch_size))
    finally:
        db.close()
