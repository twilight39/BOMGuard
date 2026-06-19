"""Substance risk profile and SHAP endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from bomguard.db import get_db
from bomguard.ml.explainability import explain_substance
from bomguard.models.database import Substance, SubstanceProperties
from bomguard.models.schemas import ShapExplanationResponse, SubstanceSchema

router = APIRouter(prefix="/api/substances", tags=["Substances"])


def _build_feature_vector(props: SubstanceProperties | None) -> dict[str, float]:
    """Build a numeric feature dict from cached SubstanceProperties."""
    if props is None:
        return {}

    features: dict[str, float] = {
        "molecular_weight": props.molecular_weight or 0.0,
        "logp": props.logp or 0.0,
        "hbd": float(props.hbd or 0),
        "hba": float(props.hba or 0),
        "tpsa": props.tpsa or 0.0,
        "rotatable_bonds": float(props.rotatable_bonds or 0),
        "aromatic_rings": float(props.aromatic_rings or 0),
        "heavy_atoms": float(props.heavy_atoms or 0),
        "has_smiles": float(props.has_smiles or 0),
        "has_epa_data": float(props.has_epa_data or 0),
    }
    if props.morgan_fp_pca_50:
        for i, val in enumerate(props.morgan_fp_pca_50):
            features[f"fp_pca_{i}"] = val
    else:
        for i in range(50):
            features[f"fp_pca_{i}"] = 0.0
    return features


@router.get("/{cas}/risk-profile")
async def risk_profile(cas: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Risk across all regulations for a substance."""
    _ = db
    return {"cas": cas, "risks": []}


@router.get("/{cas}/shap", response_model=ShapExplanationResponse)
async def shap_explanation(
    cas: str, reg: str = Query(...), db: Session = Depends(get_db)
) -> ShapExplanationResponse:
    """SHAP explanation per regulation."""
    substance = db.query(Substance).filter_by(cas_number=cas).first()
    if not substance:
        raise HTTPException(status_code=404, detail=f"Substance {cas} not found")

    props = (
        db.query(SubstanceProperties)
        .filter_by(substance_id=substance.id)
        .first()
    )
    if not props:
        raise HTTPException(
            status_code=400, detail=f"No cached features for substance {cas}"
        )

    import pandas as pd

    feature_vector = pd.Series(_build_feature_vector(props))
    explanation = explain_substance(regulation_id=reg, feature_vector=feature_vector)

    if explanation is None:
        raise HTTPException(
            status_code=404,
            detail=f"No trained model available for regulation {reg}",
        )

    return ShapExplanationResponse(
        cas=cas,
        regulation=reg,
        predicted_risk=explanation["predicted_risk"],
        base_value=explanation["base_value"],
        top_features=explanation["top_features"],
    )


@router.get("/{cas}/summary", response_model=SubstanceSchema)
async def substance_summary(cas: str, db: Session = Depends(get_db)) -> SubstanceSchema:
    """Get substance summary."""
    _ = db
    return SubstanceSchema(id=0, name="", cas_number=cas)
