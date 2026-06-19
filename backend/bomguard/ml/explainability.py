"""SHAP explainability for model predictions."""

from typing import Any, cast

import numpy as np
import pandas as pd
import shap
import xgboost as xgb

from bomguard.ml.models.registry import RegulationModelRegistry


class SHAPExplainer:
    """Generate SHAP explanations for predictions."""

    def __init__(self, model: xgb.XGBClassifier, feature_names: list[str]) -> None:
        self.model = model
        self.explainer = shap.TreeExplainer(model)
        self.feature_names = feature_names

    def explain(self, x_sample: pd.DataFrame) -> dict[str, Any]:
        """Explain a single prediction.

        Args:
            x_sample: DataFrame with one row, columns aligned to feature_names.

        Returns:
            Dict with predicted_risk, base_value, and top_features list.
        """
        shap_values = self.explainer.shap_values(x_sample)
        # shap_values may be a list for binary classifiers ([neg, pos])
        if isinstance(shap_values, list):
            shap_values = shap_values[1]

        shap_values = np.asarray(shap_values).flatten()
        expected = self.explainer.expected_value
        if isinstance(expected, np.ndarray):
            base_value = float(expected[1]) if len(expected) > 1 else float(expected)
        else:
            base_value = float(expected)

        proba = float(self.model.predict_proba(x_sample)[0, 1])

        contributions = []
        for idx, name in enumerate(self.feature_names):
            contributions.append({
                "feature": name,
                "value": float(x_sample.iloc[0, idx]),
                "contribution": float(shap_values[idx]),
            })

        # Sort by absolute contribution descending
        contributions.sort(key=lambda x: abs(cast("float", x["contribution"])), reverse=True)

        return {
            "predicted_risk": proba,
            "base_value": base_value,
            "top_features": contributions[:20],
        }


def explain_substance(
    regulation_id: str,
    feature_vector: pd.Series,
    registry: RegulationModelRegistry | None = None,
) -> dict[str, Any] | None:
    """Generate SHAP explanation for a substance under a regulation.

    Args:
        regulation_id: Target regulation.
        feature_vector: Series of feature values with feature names as index.
        registry: Optional model registry instance.

    Returns:
        Explanation dict or None if no model is available.
    """
    reg = registry or RegulationModelRegistry()
    raw_model = reg.get_raw_model(regulation_id)
    feature_names = reg.get_feature_names(regulation_id)

    if raw_model is None or feature_names is None:
        return None

    # Align to training columns
    x = pd.DataFrame([feature_vector.values], columns=feature_vector.index)
    x = x.reindex(columns=feature_names, fill_value=0.0)

    explainer = SHAPExplainer(raw_model, feature_names)
    return explainer.explain(x)
