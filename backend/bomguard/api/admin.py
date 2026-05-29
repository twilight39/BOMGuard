"""Admin / MLOps endpoints."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from bomguard.db import get_db

router = APIRouter(prefix="/api/admin/ml", tags=["Admin"])


@router.get("/regulations/{regulation_id}/performance")
async def model_performance(regulation_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Per-regulation training metrics."""
    _ = db
    return {"regulation_id": regulation_id, "metrics": {}}


@router.get("/regulations/{regulation_id}/drift")
async def model_drift(regulation_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Evidently drift report."""
    _ = db
    return {"regulation_id": regulation_id, "drift_detected": False}


@router.post("/regulations/{regulation_id}/retrain")
async def retrain_model(regulation_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Manual retrigger of model training."""
    _ = db
    return {"regulation_id": regulation_id, "status": "queued"}
