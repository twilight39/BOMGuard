"""XGBoost + Optuna training pipeline."""

from typing import TYPE_CHECKING

import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.model_selection import train_test_split

if TYPE_CHECKING:
    import pandas as pd


def train_regulation_model(
    regulation_id: str,
    X: "pd.DataFrame",
    y: "pd.Series",
    dates: "pd.Series",
) -> tuple:
    """Train XGBoost classifier for a specific regulation."""
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=6,
        learning_rate=0.1,
        tree_method="hist",
    )
    model.fit(X_train, y_train)

    calibrated = CalibratedClassifierCV(model, cv=3, method="isotonic")
    calibrated.fit(X_train, y_train)

    return calibrated, {}
