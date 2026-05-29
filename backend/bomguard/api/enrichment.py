"""Enrichment API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from bomguard.db import get_db
from bomguard.enrichment.pipeline import EnrichmentPipeline
from bomguard.models.database import Substance

router = APIRouter(prefix="/api", tags=["Enrichment"])


@router.post("/substances/{substance_id}/enrich")
async def enrich_substance_endpoint(
    substance_id: int, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Manually trigger enrichment for a single substance."""
    import asyncio

    substance = db.query(Substance).filter_by(id=substance_id).first()
    if not substance:
        raise HTTPException(status_code=404, detail="Substance not found")

    pipeline = EnrichmentPipeline(db)
    result = asyncio.run(pipeline.enrich_substance(substance))
    return {
        "substance_id": substance_id,
        "status": "enriched",
        "has_smiles": result.has_smiles,
        "has_epa_data": result.has_epa_data,
    }


@router.post("/admin/enrich-all")
async def enrich_all_endpoint(
    batch_size: int = 50, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Manually trigger batch enrichment for all missing substances."""
    import asyncio

    pipeline = EnrichmentPipeline(db)
    return asyncio.run(pipeline.enrich_all_missing(batch_size))
