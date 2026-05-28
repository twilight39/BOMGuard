"""Admin / MLOps endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from bomguard.db import get_db

router = APIRouter(prefix="/api/admin/ml", tags=["Admin"])


@router.get("/regulations/{regulation_id}/performance")
async def model_performance(regulation_id: str, db: Session = Depends(get_db)) -> dict:
    """Per-regulation training metrics."""
    return {"regulation_id": regulation_id, "metrics": {}}


@router.get("/regulations/{regulation_id}/drift")
async def model_drift(regulation_id: str, db: Session = Depends(get_db)) -> dict:
    """Evidently drift report."""
    return {"regulation_id": regulation_id, "drift_detected": False}


@router.post("/regulations/{regulation_id}/retrain")
async def retrain_model(regulation_id: str, db: Session = Depends(get_db)) -> dict:
    """Manual retrigger of model training."""
    return {"regulation_id": regulation_id, "status": "queued"}
