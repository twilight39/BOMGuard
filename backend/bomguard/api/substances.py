"""Substance risk profile and SHAP endpoints."""

from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/substances", tags=["Substances"])


@router.get("/{cas}/risk-profile")
async def risk_profile(cas: str) -> dict:
    """Risk across all regulations for a substance."""
    return {"cas": cas, "risks": []}


@router.get("/{cas}/shap")
async def shap_explanation(cas: str, reg: str = Query(...)) -> dict:
    """SHAP explanation per regulation."""
    return {"cas": cas, "regulation": reg, "features": []}
