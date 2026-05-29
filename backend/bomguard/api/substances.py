"""Substance risk profile and SHAP endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from bomguard.db import get_db
from bomguard.models.schemas import SubstanceSchema

router = APIRouter(prefix="/api/substances", tags=["Substances"])


@router.get("/{cas}/risk-profile")
async def risk_profile(cas: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Risk across all regulations for a substance."""
    _ = db
    return {"cas": cas, "risks": []}


@router.get("/{cas}/shap")
async def shap_explanation(
    cas: str, reg: str = Query(...), db: Session = Depends(get_db)
) -> dict[str, Any]:
    """SHAP explanation per regulation."""
    _ = db
    return {"cas": cas, "regulation": reg, "features": []}


@router.get("/{cas}/summary", response_model=SubstanceSchema)
async def substance_summary(cas: str, db: Session = Depends(get_db)) -> SubstanceSchema:
    """Get substance summary."""
    _ = db
    return SubstanceSchema(id=0, name="", cas_number=cas)
