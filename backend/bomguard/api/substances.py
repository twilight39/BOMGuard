"""Substance risk profile and SHAP endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from bomguard.db import get_db
from bomguard.models.schemas import SubstanceSchema

router = APIRouter(prefix="/api/substances", tags=["Substances"])


@router.get("/{cas}/risk-profile")
async def risk_profile(cas: str, db: Session = Depends(get_db)) -> dict:
    """Risk across all regulations for a substance."""
    return {"cas": cas, "risks": []}


@router.get("/{cas}/shap")
async def shap_explanation(cas: str, reg: str = Query(...), db: Session = Depends(get_db)) -> dict:
    """SHAP explanation per regulation."""
    return {"cas": cas, "regulation": reg, "features": []}


@router.get("/{cas}/summary", response_model=SubstanceSchema)
async def substance_summary(cas: str, db: Session = Depends(get_db)) -> SubstanceSchema:
    """Get substance summary."""
    return SubstanceSchema(id=0, name="", cas_number=cas)
