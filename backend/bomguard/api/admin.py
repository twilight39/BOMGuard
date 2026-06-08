"""Admin / MLOps endpoints."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from bomguard.db import get_db
from bomguard.enrichment.summary_tasks import generate_all_summaries
from bomguard.models.database import (
    Bom,
    Regulation,
    RegulatorySummary,
    Substance,
)

router = APIRouter(prefix="/api/admin/ml", tags=["Admin"])


@router.get("/regulations/{regulation_id}/performance")
async def model_performance(
    regulation_id: str, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Per-regulation training metrics."""
    _ = db
    return {"regulation_id": regulation_id, "metrics": {}}


@router.get("/regulations/{regulation_id}/drift")
async def model_drift(
    regulation_id: str, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Evidently drift report."""
    _ = db
    return {"regulation_id": regulation_id, "drift_detected": False}


@router.post("/regulations/{regulation_id}/retrain")
async def retrain_model(
    regulation_id: str, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Manual retrigger of model training."""
    _ = db
    return {"regulation_id": regulation_id, "status": "queued"}


@router.get("/stats")
async def get_stats(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Dashboard stats: counts of substances, regulations, BOMs."""
    substance_count = db.query(Substance).count()
    regulation_count = db.query(Regulation).count()
    bom_count = db.query(Bom).count()
    summary_count = db.query(RegulatorySummary).count()
    return {
        "substances": substance_count,
        "regulations": regulation_count,
        "boms": bom_count,
        "summaries": summary_count,
    }


@router.post("/enrich")
async def trigger_enrichment(
    batch_size: int = 50, db: Session = Depends(get_db)
) -> dict[str, Any]:
    """Trigger backfill of regulatory summaries for all substances."""
    _ = db
    task = generate_all_summaries.delay(batch_size=batch_size)
    return {"status": "queued", "task_id": task.id}


@router.get("/enrich/status")
async def enrichment_status(
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Check enrichment status: how many summaries exist vs substances."""
    substance_count = db.query(Substance).count()
    summary_count = db.query(RegulatorySummary).count()
    return {
        "substance_count": substance_count,
        "summary_count": summary_count,
        "missing": max(0, substance_count - summary_count),
        "complete": summary_count >= substance_count,
    }
