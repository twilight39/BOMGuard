"""Regulatory data endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from bomguard.db import get_db
from bomguard.ingestion.pipeline import run_scraper
from bomguard.ingestion.registry import get_scraper
from bomguard.models.schemas import RegulationSchema

router = APIRouter(prefix="/api/regulations", tags=["Regulations"])


@router.get("/", response_model=list[RegulationSchema])
async def list_regulations(db: Session = Depends(get_db)) -> list[RegulationSchema]:
    """List all active regulations."""
    from bomguard.models.database import Regulation

    return db.query(Regulation).all()  # type: ignore[return-value]


@router.get("/{regulation_id}", response_model=RegulationSchema)
async def get_regulation(regulation_id: str, db: Session = Depends(get_db)) -> RegulationSchema:
    """Get regulation details and ML status."""
    from bomguard.models.database import Regulation

    reg = db.query(Regulation).filter_by(id=regulation_id).first()
    if not reg:
        raise HTTPException(status_code=404, detail="Regulation not found")
    return reg  # type: ignore[return-value]


@router.get("/feed")
async def regulatory_feed(db: Session = Depends(get_db)) -> list[dict]:
    """Recent regulatory changes."""
    from bomguard.models.database import RegulatoryChange

    changes = db.query(RegulatoryChange).order_by(RegulatoryChange.detected_at.desc()).limit(50).all()
    return [
        {
            "id": c.id,
            "substance_id": c.substance_id,
            "regulation_id": c.regulation_id,
            "change_type": c.change_type,
            "detected_at": c.detected_at.isoformat() if c.detected_at else None,
        }
        for c in changes
    ]


@router.post("/{regulation_id}/refresh")
async def refresh_regulation(regulation_id: str, db: Session = Depends(get_db)) -> dict:
    """Manually trigger a scraper refresh for a regulation."""
    scraper = get_scraper(regulation_id)
    if not scraper:
        raise HTTPException(status_code=404, detail=f"No scraper found for {regulation_id}")

    result = run_scraper(scraper, db)
    return {
        "regulation_id": result.regulation_id,
        "source_name": result.source_name,
        "total_fetched": result.total_fetched,
        "substances_created": result.substances_created,
        "substances_updated": result.substances_updated,
        "statuses_created": result.statuses_created,
        "changes_detected": result.changes_detected,
    }
