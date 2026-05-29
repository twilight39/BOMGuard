"""SHAP explainability for model predictions."""

from typing import Any

import shap


class SHAPExplainer:
    """Generate SHAP explanations for predictions."""

    def __init__(self, model: object, feature_names: list[str]) -> None:
        self.explainer = shap.TreeExplainer(model)
        self.feature_names = feature_names

    def explain(self, X_sample: object) -> dict[str, Any]:
        """Explain a single prediction."""
        return {"predicted_risk": 0.0, "top_features": []}
