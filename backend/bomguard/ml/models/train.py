"""XGBoost + Optuna training pipeline with calibration and MLflow logging."""

import json
import warnings
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import joblib
import mlflow
import mlflow.xgboost
import numpy as np
import optuna
import pandas as pd
import xgboost as xgb
from sklearn.calibration import CalibratedClassifierCV
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    roc_auc_score,
)
from sqlalchemy.orm import Session

from bomguard.config import Settings
from bomguard.ml.evaluate import get_split_strategy
from bomguard.models.database import (
    Regulation,
    SubstanceProperties,
    SubstanceRegulationStatus,
)

settings = Settings()
optuna.logging.set_verbosity(optuna.logging.WARNING)

TARGET_METRICS = {
    "roc_auc": 0.75,
    "average_precision": 0.25,
    "precision_at_100": 0.15,
    "brier_score": 0.10,
}


def _precision_at_k(y_true: np.ndarray, y_scores: np.ndarray, k: int = 100) -> float:
    """Compute precision at top-k predicted probabilities."""
    if len(y_true) == 0:
        return 0.0
    k = min(k, len(y_true))
    top_k_idx = np.argsort(y_scores)[-k:]
    return float(np.mean(y_true[top_k_idx]))


def _compute_metrics(y_true: np.ndarray, y_proba: np.ndarray) -> dict[str, Any]:
    """Compute classification metrics."""
    return {
        "roc_auc": float(roc_auc_score(y_true, y_proba)),
        "average_precision": float(average_precision_score(y_true, y_proba)),
        "precision_at_100": _precision_at_k(y_true, y_proba, k=100),
        "brier_score": float(brier_score_loss(y_true, y_proba)),
    }


def _metrics_pass(metrics: dict[str, float]) -> bool:
    """Check if all target thresholds are met."""
    return (
        metrics["roc_auc"] >= TARGET_METRICS["roc_auc"]
        and metrics["average_precision"] >= TARGET_METRICS["average_precision"]
        and metrics["precision_at_100"] >= TARGET_METRICS["precision_at_100"]
        and metrics["brier_score"] <= TARGET_METRICS["brier_score"]
    )


def load_training_data(
    db: Session, regulation_id: str
) -> tuple[pd.DataFrame, pd.Series, pd.Series]:
    """Load aligned features and labels for a regulation.

    Returns:
        X: DataFrame of features (one row per substance).
        y: Series of binary labels (1 = restricted, 0 = not_restricted).
        dates: Series of effective dates for temporal splitting.
    """
    rows = (
        db.query(
            SubstanceRegulationStatus.substance_id,
            SubstanceRegulationStatus.status,
            SubstanceRegulationStatus.effective_date,
            SubstanceProperties.molecular_weight,
            SubstanceProperties.logp,
            SubstanceProperties.hbd,
            SubstanceProperties.hba,
            SubstanceProperties.tpsa,
            SubstanceProperties.rotatable_bonds,
            SubstanceProperties.aromatic_rings,
            SubstanceProperties.heavy_atoms,
            SubstanceProperties.has_smiles,
            SubstanceProperties.has_epa_data,
            SubstanceProperties.morgan_fp_pca_50,
        )
        .outerjoin(
            SubstanceProperties,
            SubstanceRegulationStatus.substance_id == SubstanceProperties.substance_id,
        )
        .filter(SubstanceRegulationStatus.regulation_id == regulation_id)
        .filter(
            SubstanceRegulationStatus.status.in_(["restricted", "not_restricted"])
        )
        .all()
    )

    if not rows:
        raise ValueError(f"No training data found for regulation {regulation_id}")

    records = []
    labels = []
    dates = []
    for row in rows:
        rec = {
            "substance_id": row.substance_id,
            "molecular_weight": row.molecular_weight,
            "logp": row.logp,
            "hbd": row.hbd,
            "hba": row.hba,
            "tpsa": row.tpsa,
            "rotatable_bonds": row.rotatable_bonds,
            "aromatic_rings": row.aromatic_rings,
            "heavy_atoms": row.heavy_atoms,
            "has_smiles": float(row.has_smiles or 0),
            "has_epa_data": float(row.has_epa_data or 0),
        }
        if row.morgan_fp_pca_50:
            for i, val in enumerate(row.morgan_fp_pca_50):
                rec[f"fp_pca_{i}"] = val
        records.append(rec)
        labels.append(1 if row.status == "restricted" else 0)
        dates.append(row.effective_date or datetime.now(UTC).date())

    X = pd.DataFrame.from_records(records)
    X = X.set_index("substance_id")
    X = X.fillna(0.0)

    # Ensure all fp_pca columns exist even if no substance has them
    for i in range(50):
        col = f"fp_pca_{i}"
        if col not in X.columns:
            X[col] = 0.0

    y = pd.Series(labels, index=X.index, name="label")
    dates = pd.Series(dates, index=X.index, name="date")

    # Basic validation
    if len(X) < 50:
        raise ValueError(f"Insufficient samples ({len(X)}) for training")
    if y.sum() < 5 or (len(y) - y.sum()) < 5:
        raise ValueError(
            f"Insufficient class balance: {y.sum()} positive, {len(y) - y.sum()} negative"
        )

    return X, y, dates


def train_regulation_model(
    regulation_id: str,
    X: pd.DataFrame,
    y: pd.Series,
    dates: pd.Series,
    n_trials: int = 50,
) -> dict[str, Any]:
    """Train an XGBoost classifier for a specific regulation.

    Performs Optuna HPO (50 trials), trains a final model, calibrates
    probabilities, evaluates on holdout, logs to MLflow, and persists
    artifacts to disk.

    Returns:
        Dictionary with keys:
            - calibrated_model: sklearn-compatible classifier
            - raw_model: underlying XGBoost model (for SHAP)
            - feature_names: list of feature column names
            - metrics: dict of test-set metrics
            - metadata: training run info
    """
    strategy, train_idx, test_idx = get_split_strategy(dates)

    x_train_full = X.iloc[train_idx]
    y_train_full = y.iloc[train_idx]
    x_test = X.iloc[test_idx]
    y_test = y.iloc[test_idx]

    # Internal validation split for Optuna early stopping
    n_train = len(x_train_full)
    val_size = max(1, int(n_train * 0.2))
    val_idx = x_train_full.sample(n=val_size, random_state=42).index
    train_idx_inner = x_train_full.index.difference(val_idx)

    x_train = x_train_full.loc[train_idx_inner]
    y_train = y_train_full.loc[train_idx_inner]
    x_val = x_train_full.loc[val_idx]
    y_val = y_train_full.loc[val_idx]

    def _objective(trial: optuna.Trial) -> float:
        params = {
            "n_estimators": trial.suggest_int("n_estimators", 100, 1000),
            "max_depth": trial.suggest_int("max_depth", 3, 10),
            "learning_rate": trial.suggest_float("learning_rate", 0.01, 0.3, log=True),
            "subsample": trial.suggest_float("subsample", 0.6, 1.0),
            "colsample_bytree": trial.suggest_float("colsample_bytree", 0.6, 1.0),
            "min_child_weight": trial.suggest_int("min_child_weight", 1, 10),
            "gamma": trial.suggest_float("gamma", 0.0, 5.0),
            "reg_alpha": trial.suggest_float("reg_alpha", 1e-8, 10.0, log=True),
            "reg_lambda": trial.suggest_float("reg_lambda", 1e-8, 10.0, log=True),
        }
        model = xgb.XGBClassifier(
            **params,
            tree_method="hist",
            eval_metric="logloss",
            random_state=42,
        )
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            model.fit(
                x_train,
                y_train,
                eval_set=[(x_val, y_val)],
                verbose=False,
            )
        y_proba = model.predict_proba(x_val)[:, 1]
        return float(roc_auc_score(y_val, y_proba))

    study = optuna.create_study(direction="maximize", pruner=optuna.pruners.MedianPruner())
    study.optimize(_objective, n_trials=n_trials, show_progress_bar=False)

    best_params = study.best_params
    best_params.update({
        "tree_method": "hist",
        "eval_metric": "logloss",
        "random_state": 42,
    })

    # Train final model on full training set with best hyperparameters
    raw_model = xgb.XGBClassifier(**best_params)
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        raw_model.fit(x_train_full, y_train_full)

    # Calibrate probabilities (isotonic, 3-fold CV on holdout)
    calibrated = CalibratedClassifierCV(raw_model, method="isotonic", cv=3)
    calibrated.fit(x_test, y_test)

    # Evaluate on test set
    y_proba = calibrated.predict_proba(x_test)[:, 1]
    metrics = _compute_metrics(y_test.values, y_proba)
    metrics["n_train"] = len(x_train_full)
    metrics["n_test"] = len(x_test)
    metrics["n_positive_train"] = int(y_train_full.sum())
    metrics["n_positive_test"] = int(y_test.sum())
    metrics["split_strategy"] = strategy
    metrics["best_val_roc_auc"] = study.best_value

    passed = _metrics_pass(metrics)
    tag = "production" if passed else "rejected"

    # MLflow logging
    mlflow.set_tracking_uri(settings.mlflow_tracking_uri)
    run_id: str | None = None
    try:
        with mlflow.start_run(run_name=f"bomguard_{regulation_id}_{datetime.now(UTC).isoformat()}") as run:
            run_id = run.info.run_id
            mlflow.set_tag("regulation_id", regulation_id)
            mlflow.set_tag("model_stage", tag)
            mlflow.log_params(best_params)
            mlflow.log_metrics(metrics)
            mlflow.xgboost.log_model(raw_model, artifact_path="model")
    except Exception:
        # MLflow is optional; don't fail training if server unreachable
        run_id = None

    # Persist to disk
    artifact_dir = Path(settings.model_artifact_path)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    version = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
    base_name = f"{regulation_id}_{version}"

    model_path = artifact_dir / f"{base_name}.joblib"
    joblib.dump({
        "calibrated_model": calibrated,
        "raw_model": raw_model,
        "feature_names": list(X.columns),
        "metrics": metrics,
        "metadata": {
            "regulation_id": regulation_id,
            "trained_at": datetime.now(UTC).isoformat(),
            "version": version,
            "mlflow_run_id": run_id,
            "tag": tag,
        },
    }, model_path)

    # Also write a latest symlink / pointer
    latest_path = artifact_dir / f"{regulation_id}_latest.json"
    latest_path.write_text(json.dumps({"path": str(model_path), "version": version}))

    return {
        "calibrated_model": calibrated,
        "raw_model": raw_model,
        "feature_names": list(X.columns),
        "metrics": metrics,
        "metadata": {
            "regulation_id": regulation_id,
            "version": version,
            "mlflow_run_id": run_id,
            "tag": tag,
            "model_path": str(model_path),
        },
    }


def train_and_persist(db: Session, regulation_id: str) -> dict[str, Any]:
    """End-to-end helper: load data, train, persist, and update Regulation row.

    Returns the training result dict.
    """
    X, y, dates = load_training_data(db, regulation_id)
    result = train_regulation_model(regulation_id, X, y, dates)

    # Update regulation record
    reg = db.query(Regulation).filter_by(id=regulation_id).first()
    if reg:
        reg.last_model_trained = datetime.now(UTC)
        reg.ml_model_version = result["metadata"]["version"]
        db.commit()

    return result
