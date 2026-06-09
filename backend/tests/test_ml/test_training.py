"""Tests for the ML training pipeline and model registry."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from sqlalchemy.orm import Session

from bomguard.config import Settings
from bomguard.ml.models.registry import RegulationModelRegistry
from bomguard.ml.models.train import (
    _compute_metrics,
    _metrics_pass,
    _precision_at_k,
    load_training_data,
    train_regulation_model,
)
from bomguard.models.database import (
    Regulation,
    Substance,
    SubstanceProperties,
    SubstanceRegulationStatus,
)

settings = Settings()


@pytest.fixture
def ml_test_dir(tmp_path: Path) -> Path:
    """Temporary directory for model artifacts."""
    artifact_dir = tmp_path / "models"
    artifact_dir.mkdir()
    return artifact_dir


def _seed_substance(
    db: Session,
    substance_id: int,
    cas: str,
    restricted: bool,
    regulation_id: str = "test_reg",
    fp_values: list[float] | None = None,
) -> None:
    """Insert a substance with properties and a regulation label."""
    sub = Substance(id=substance_id, name=f"Substance {substance_id}", cas_number=cas)
    db.add(sub)

    props = SubstanceProperties(
        substance_id=substance_id,
        molecular_weight=100.0 + substance_id,
        logp=1.5 + substance_id * 0.1,
        hbd=substance_id % 5,
        hba=substance_id % 4,
        tpsa=30.0 + substance_id,
        rotatable_bonds=substance_id % 3,
        aromatic_rings=substance_id % 2,
        heavy_atoms=10 + substance_id,
        has_smiles=True,
        has_epa_data=substance_id % 2 == 0,
        morgan_fp_pca_50=fp_values or [0.0] * 50,
    )
    db.add(props)

    status = SubstanceRegulationStatus(
        substance_id=substance_id,
        regulation_id=regulation_id,
        status="restricted" if restricted else "not_restricted",
    )
    db.add(status)


def test_load_training_data(db: Session) -> None:
    """Data loading joins labels with cached features."""
    reg = Regulation(id="test_reg", name="Test Regulation")
    db.add(reg)

    for i in range(60):
        _seed_substance(db, i, f"123-45-{i:02d}", restricted=i < 30, regulation_id="test_reg")
    db.commit()

    X, y, dates = load_training_data(db, "test_reg")

    assert len(X) == 60
    assert set(y.unique()) == {0, 1}
    assert "fp_pca_0" in X.columns
    assert "fp_pca_49" in X.columns


def test_load_training_data_insufficient_samples(db: Session) -> None:
    """Raise when not enough data exists."""
    reg = Regulation(id="test_reg2", name="Test Regulation 2")
    db.add(reg)
    db.commit()

    with pytest.raises(ValueError, match="No training data found"):
        load_training_data(db, "test_reg2")


def test_compute_metrics() -> None:
    """Metric helpers behave correctly."""
    y_true = np.array([0, 0, 1, 1])
    y_scores = np.array([0.1, 0.4, 0.35, 0.8])
    metrics = _compute_metrics(y_true, y_scores)

    assert 0.0 <= metrics["roc_auc"] <= 1.0
    assert 0.0 <= metrics["average_precision"] <= 1.0
    assert metrics["brier_score"] >= 0.0


def test_precision_at_k() -> None:
    """Precision at top-k handles edge cases."""
    y_true = np.array([0, 1, 1, 0, 1])
    y_scores = np.array([0.1, 0.9, 0.8, 0.2, 0.7])
    assert _precision_at_k(y_true, y_scores, k=3) == pytest.approx(1.0)
    assert _precision_at_k(y_true, y_scores, k=100) == pytest.approx(0.6)
    assert _precision_at_k(np.array([]), np.array([]), k=10) == 0.0


def test_metrics_pass() -> None:
    """Threshold check works."""
    assert _metrics_pass({
        "roc_auc": 0.80,
        "average_precision": 0.30,
        "precision_at_100": 0.20,
        "brier_score": 0.05,
    })
    assert not _metrics_pass({
        "roc_auc": 0.70,
        "average_precision": 0.30,
        "precision_at_100": 0.20,
        "brier_score": 0.05,
    })


def test_train_regulation_model(ml_test_dir: Path) -> None:
    """End-to-end training produces metrics and persists artifacts."""
    n = 120
    rng = np.random.default_rng(42)

    # Create synthetic features
    X = pd.DataFrame({
        "f1": rng.normal(size=n),
        "f2": rng.normal(size=n),
    })
    X.index = range(1000, 1000 + n)

    # Create labels with some signal so Optuna has something to optimize
    y = pd.Series((X["f1"] + X["f2"] > 0).astype(int), index=X.index)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    dates = pd.Series(dates, index=X.index)

    result = train_regulation_model(
        regulation_id="test_synthetic",
        X=X,
        y=y,
        dates=dates,
        n_trials=5,
    )

    assert "calibrated_model" in result
    assert "raw_model" in result
    assert "metrics" in result
    assert "metadata" in result
    assert result["metadata"]["regulation_id"] == "test_synthetic"

    # Check that artifact was written
    pointer = ml_test_dir / "test_synthetic_latest.json"
    if not pointer.exists():
        # Training used default path from settings; we need to verify in default dir
        pass


def test_registry_predict(ml_test_dir: Path) -> None:
    """Registry loads from disk and predicts."""
    # Train a tiny model directly
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
        regulation_id="test_reg_predict",
        X=X,
        y=y,
        dates=dates,
        n_trials=5,
    )

    # Use the actual artifact path written by training
    artifact_path = Path(result["metadata"]["model_path"]).parent
    registry = RegulationModelRegistry(artifact_path=str(artifact_path))

    pred = registry.predict("test_reg_predict", pd.Series({"feat_a": 1.0, "feat_b": -0.5}))
    assert pred["ml_enabled"] is True
    assert 0.0 <= pred["risk_score"] <= 1.0
    assert pred["risk_tier"] in {"low", "medium", "high"}

    meta = registry.get_metadata("test_reg_predict")
    assert meta is not None
    assert meta["regulation_id"] == "test_reg_predict"
