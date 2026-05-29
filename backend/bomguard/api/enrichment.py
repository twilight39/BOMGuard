"""Enrichment API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from bomguard.config import Settings
from bomguard.db import get_db
from bomguard.enrichment.pipeline import EnrichmentPipeline
from bomguard.models.database import Substance

router = APIRouter(prefix="/api", tags=["Enrichment"])

settings = Settings()


def _require_admin_key(x_admin_api_key: str | None) -> None:
    if not settings.admin_api_key:
        # Admin key not configured — allow unrestricted access in dev
        return
    if x_admin_api_key != settings.admin_api_key:
        raise HTTPException(status_code=403, detail="Invalid admin API key")


@router.post("/substances/{substance_id}/enrich")
async def enrich_substance_endpoint(
    substance_id: int, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Manually trigger enrichment for a single substance."""
    substance = db.query(Substance).filter_by(id=substance_id).first()
    if not substance:
        raise HTTPException(status_code=404, detail="Substance not found")

    pipeline = EnrichmentPipeline(db)
    result = await pipeline.enrich_substance(substance)
    return {
        "substance_id": substance_id,
        "status": "enriched",
        "has_smiles": result.has_smiles,
        "has_epa_data": result.has_epa_data,
    }


@router.post("/admin/enrich-all")
async def enrich_all_endpoint(
    batch_size: int = 50,
    db: Session = Depends(get_db),
    x_admin_api_key: str | None = Header(default=None),
) -> dict[str, Any]:
    """Manually trigger batch enrichment for all missing substances."""
    _require_admin_key(x_admin_api_key)

    pipeline = EnrichmentPipeline(db)
    return await pipeline.enrich_all_missing(batch_size)
