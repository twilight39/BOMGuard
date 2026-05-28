"""Regulatory data endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from bomguard.db import get_db
from bomguard.models.schemas import RegulationSchema

router = APIRouter(prefix="/api/regulations", tags=["Regulations"])


@router.get("/", response_model=list[RegulationSchema])
async def list_regulations(db: Session = Depends(get_db)) -> list[RegulationSchema]:
    """List all active regulations."""
    return []


@router.get("/{regulation_id}", response_model=RegulationSchema)
async def get_regulation(regulation_id: str, db: Session = Depends(get_db)) -> RegulationSchema:
    """Get regulation details and ML status."""
    return RegulationSchema(
        id=regulation_id,
        name="",
        ml_enabled=False,
        positive_label_count=0,
        negative_label_count=0,
    )


@router.get("/feed")
async def regulatory_feed(db: Session = Depends(get_db)) -> list[dict]:
    """Recent regulatory changes."""
    return []
