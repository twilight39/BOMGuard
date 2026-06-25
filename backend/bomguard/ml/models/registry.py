"""Multi-regulation model registry with disk persistence."""

import json
from pathlib import Path
from typing import Any, cast

import joblib
import pandas as pd
import xgboost as xgb

from bomguard.config import Settings

settings = Settings()


class RegulationModelRegistry:
    """Maintains one trained model per regulation, loading from disk."""

    def __init__(self, artifact_path: str | None = None) -> None:
        self._artifact_path = Path(artifact_path or settings.model_artifact_path)
        self._cache: dict[str, dict[str, Any]] = {}

    def _latest_pointer(self, regulation_id: str) -> Path | None:
        pointer = self._artifact_path / f"{regulation_id}_latest.json"
        if not pointer.exists():
            return None
        data = json.loads(pointer.read_text())
        return Path(data["path"])

    def load_model(self, regulation_id: str) -> dict[str, Any] | None:
        """Load model artifact from disk into memory cache.

        Returns the artifact dict or None if not found.
        """
        if regulation_id in self._cache:
            return self._cache[regulation_id]

        path = self._latest_pointer(regulation_id)
        if path is None or not path.exists():
            return None

        artifact: dict[str, Any] = joblib.load(path)
        self._cache[regulation_id] = artifact
        return artifact

    def get_model(self, regulation_id: str) -> object | None:
        """Return the calibrated model for a regulation."""
        artifact = self.load_model(regulation_id)
        if artifact is None:
            return None
        return cast("object", artifact["calibrated_model"])

    def get_raw_model(self, regulation_id: str) -> xgb.XGBClassifier | None:
        """Return the raw (uncalibrated) XGBoost model for SHAP."""
        artifact = self.load_model(regulation_id)
        if artifact is None:
            return None
        return cast("xgb.XGBClassifier", artifact["raw_model"])

    def get_feature_names(self, regulation_id: str) -> list[str] | None:
        """Return feature names used during training."""
        artifact = self.load_model(regulation_id)
        if artifact is None:
            return None
        return artifact.get("feature_names")

    def get_metadata(self, regulation_id: str) -> dict[str, Any] | None:
        """Return training metadata for a regulation."""
        artifact = self.load_model(regulation_id)
        if artifact is None:
            return None
        return artifact.get("metadata")

    def get_metrics(self, regulation_id: str) -> dict[str, Any] | None:
        """Return training metrics for a regulation."""
        artifact = self.load_model(regulation_id)
        if artifact is None:
            return None
        return artifact.get("metrics")

    def predict(self, regulation_id: str, feature_vector: pd.Series) -> dict[str, Any]:
        """Predict risk for a substance under a regulation.

        Args:
            regulation_id: Target regulation.
            feature_vector: Series of feature values aligned to training columns.

        Returns:
            Dict with ml_enabled, risk_score (probability), and risk_tier.
        """
        artifact = self.load_model(regulation_id)
        if artifact is None:
            return {"ml_enabled": False, "risk_score": None, "risk_tier": "unknown"}

        model = artifact["calibrated_model"]
        feature_names = artifact["feature_names"]

        # Align vector to training columns
        X = pd.DataFrame([feature_vector.values], columns=feature_vector.index)
        X = X.reindex(columns=feature_names, fill_value=0.0)

        proba = model.predict_proba(X)[0, 1]

        if proba >= 0.7:
            tier = "high"
        elif proba >= 0.4:
            tier = "medium"
        else:
            tier = "low"

        return {
            "ml_enabled": True,
            "risk_score": float(proba),
            "risk_tier": tier,
        }

    def invalidate(self, regulation_id: str) -> None:
        """Remove a regulation from the in-memory cache."""
        self._cache.pop(regulation_id, None)
