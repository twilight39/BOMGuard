"""Tests for SHAP explainability."""

from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy.orm import Session

from bomguard.ml.explainability import SHAPExplainer, explain_substance
from bomguard.ml.models.registry import RegulationModelRegistry
from bomguard.ml.models.train import train_regulation_model
from bomguard.models.database import (
    Regulation,
    Substance,
    SubstanceProperties,
    SubstanceRegulationStatus,
)


def _seed_substance_and_model(db: Session, regulation_id: str = "test_shap_reg") -> str:
    """Seed DB and train a tiny model so SHAP works end-to-end."""
    reg = Regulation(id=regulation_id, name="Test SHAP Regulation", ml_enabled=True)
    db.add(reg)

    n = 80
    rng = np.random.default_rng(99)
    for i in range(n):
        sub = Substance(id=1000 + i, name=f"Chem {i}", cas_number=f"111-11-{i:02d}")
        db.add(sub)
        props = SubstanceProperties(
            substance_id=1000 + i,
            molecular_weight=100.0 + i,
            logp=rng.normal(),
            hbd=i % 3,
            hba=i % 4,
            tpsa=20.0 + i,
            rotatable_bonds=i % 2,
            aromatic_rings=i % 2,
            heavy_atoms=10 + i,
            has_smiles=True,
            has_epa_data=i % 2 == 0,
            morgan_fp_pca_50=[rng.normal() for _ in range(50)],
        )
        db.add(props)
        status = SubstanceRegulationStatus(
            substance_id=1000 + i,
            regulation_id=regulation_id,
            status="restricted" if i < 30 else "not_restricted",
        )
        db.add(status)
    db.commit()

    # Train a tiny model
    from bomguard.ml.models.train import load_training_data

    X, y, dates = load_training_data(db, regulation_id)
    result = train_regulation_model(regulation_id, X, y, dates, n_trials=3)

    # Point registry to the artifact
    artifact_path = Path(result["metadata"]["model_path"]).parent
    return str(artifact_path)


def test_shap_explainer_output_shape() -> None:
    """SHAPExplainer returns expected keys and correct number of features."""
    n = 80
    rng = np.random.default_rng(7)
    X = pd.DataFrame({
        "feat_a": rng.normal(size=n),
        "feat_b": rng.normal(size=n),
    })
    X.index = range(2000, 2000 + n)
    y = pd.Series((X["feat_a"] > 0).astype(int), index=X.index)
    dates = pd.Series(pd.date_range("2024-06-01", periods=n, freq="D"), index=X.index)

    result = train_regulation_model(
        regulation_id="test_shap_explainer",
        X=X,
        y=y,
        dates=dates,
        n_trials=3,
    )

    raw_model = result["raw_model"]
    explainer = SHAPExplainer(raw_model, ["feat_a", "feat_b"])
    x_sample = pd.DataFrame([[1.0, -0.5]], columns=["feat_a", "feat_b"])
    explanation = explainer.explain(x_sample)

    assert "predicted_risk" in explanation
    assert "base_value" in explanation
    assert "top_features" in explanation
    assert len(explanation["top_features"]) <= 2
    assert all(
        {"feature", "value", "contribution"} <= set(f.keys())
        for f in explanation["top_features"]
    )

    # Predicted risk should be a probability
    assert 0.0 <= explanation["predicted_risk"] <= 1.0


def test_explain_substance_integration(db: Session) -> None:
    """explain_substance integrates with registry and returns contributions."""
    artifact_path = _seed_substance_and_model(db, "test_shap_integration")
    registry = RegulationModelRegistry(artifact_path=artifact_path)

    # Build a feature vector matching the training schema
    feature_vector = pd.Series({
        "molecular_weight": 150.0,
        "logp": 2.5,
        "hbd": 1.0,
        "hba": 2.0,
        "tpsa": 45.0,
        "rotatable_bonds": 1.0,
        "aromatic_rings": 1.0,
        "heavy_atoms": 20.0,
        "has_smiles": 1.0,
        "has_epa_data": 1.0,
        **{f"fp_pca_{i}": 0.1 for i in range(50)},
    })

    explanation = explain_substance(
        regulation_id="test_shap_integration",
        feature_vector=feature_vector,
        registry=registry,
    )

    assert explanation is not None
    assert "predicted_risk" in explanation
    assert "top_features" in explanation
    assert len(explanation["top_features"]) > 0

    # Verify sign consistency: contributions should be real floats
    for feat in explanation["top_features"]:
        assert isinstance(feat["contribution"], float)
        assert isinstance(feat["value"], float)


def test_explain_substance_no_model() -> None:
    """Returns None when no model exists for the regulation."""
    feature_vector = pd.Series({"foo": 1.0})
    result = explain_substance("nonexistent_reg", feature_vector)
    assert result is None
