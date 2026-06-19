"""Admin / MLOps endpoints."""

from datetime import UTC, datetime, timedelta
from typing import Any

import pandas as pd
from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from bomguard.celery_app import celery_app
from bomguard.config import Settings
from bomguard.db import get_db
from bomguard.enrichment.summary_tasks import generate_all_summaries
from bomguard.models.database import (
    Bom,
    MLModelPerformance,
    Regulation,
    RegulatoryChange,
    RegulatorySummary,
    Substance,
)

settings = Settings()
router = APIRouter(prefix="/api/admin", tags=["Admin"])


def _changes_to_df(changes: list[RegulatoryChange]) -> pd.DataFrame:
    """Convert regulatory changes to a simple feature DataFrame for drift."""
    records: list[dict[str, Any]] = []
    for change in changes:
        dt = change.detected_at or datetime.now(UTC)
        records.append(
            {
                "change_type": change.change_type,
                "hour_of_day": dt.hour,
                "day_of_week": dt.weekday(),
            }
        )
    return pd.DataFrame.from_records(records)


async def require_admin_key(
    x_admin_api_key: str | None = Header(None, alias="X-Admin-API-Key"),
) -> None:
    """Require a valid admin API key for sensitive endpoints.

    In production ``ADMIN_API_KEY`` must be set and the caller must supply it
    in the ``X-Admin-API-Key`` header. When the key is not configured we allow
    access for local development convenience, but this should never happen in
    production deployments.
    """
    if not settings.admin_api_key:
        # Dev fallback: key not configured, allow access.
        return
    if x_admin_api_key != settings.admin_api_key:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or missing admin API key.",
        )


@router.get("/ml/regulations/{regulation_id}/performance")
async def model_performance(regulation_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Return the latest training metrics for a regulation."""
    record = (
        db.query(MLModelPerformance)
        .filter_by(regulation_id=regulation_id)
        .order_by(MLModelPerformance.trained_at.desc().nullslast(), MLModelPerformance.id.desc())
        .first()
    )
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No model performance records found for this regulation.",
        )
    return {
        "regulation_id": regulation_id,
        "model_version": record.model_version,
        "mlflow_run_id": record.mlflow_run_id,
        "trained_at": record.trained_at.isoformat() if record.trained_at else None,
        "metrics": {
            "roc_auc": record.roc_auc,
            "average_precision": record.average_precision,
            "precision_at_100": record.precision_at_100,
            "brier_score": record.brier_score,
        },
        "promoted_to_production": record.promoted_to_production,
        "sample_counts": {
            "n_train_positive": record.n_train_positive,
            "n_train_negative": record.n_train_negative,
            "n_test_positive": record.n_test_positive,
            "n_test_negative": record.n_test_negative,
        },
    }


@router.get("/ml/regulations/{regulation_id}/drift")
async def model_drift(regulation_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Compare recent regulatory changes against a baseline using Evidently AI."""
    now = datetime.now(UTC)
    current_start = now - timedelta(days=30)
    baseline_start = now - timedelta(days=60)

    current_changes = (
        db.query(RegulatoryChange)
        .filter_by(regulation_id=regulation_id)
        .filter(RegulatoryChange.detected_at >= current_start)
        .all()
    )
    baseline_changes = (
        db.query(RegulatoryChange)
        .filter_by(regulation_id=regulation_id)
        .filter(RegulatoryChange.detected_at >= baseline_start)
        .filter(RegulatoryChange.detected_at < current_start)
        .all()
    )

    if len(current_changes) < 5 or len(baseline_changes) < 5:
        return {
            "regulation_id": regulation_id,
            "drift_detected": False,
            "drift_score": 0.0,
            "detected_features": [],
            "message": "Insufficient data for drift detection (need at least 5 changes in each window).",
        }

    try:
        current_df = _changes_to_df(current_changes)
        baseline_df = _changes_to_df(baseline_changes)

        from evidently.metric_preset import DataDriftPreset
        from evidently.report import Report

        report = Report(metrics=[DataDriftPreset()])
        report.run(reference_data=baseline_df, current_data=current_df)
        result = report.as_dict()

        drift_detected = False
        drift_score = 0.0
        detected_features: list[str] = []

        for metric in result.get("metrics", []):
            metric_result = metric.get("result", {})
            if "dataset_drift" in metric_result:
                drift_detected = bool(metric_result.get("dataset_drift", False))
                drift_score = float(metric_result.get("drift_share", 0.0))
            drift_by_columns = metric_result.get("drift_by_columns", {})
            for feature, feature_result in drift_by_columns.items():
                if feature_result.get("drift_detected"):
                    detected_features.append(str(feature))

        return {
            "regulation_id": regulation_id,
            "drift_detected": drift_detected,
            "drift_score": drift_score,
            "detected_features": detected_features,
        }
    except Exception as exc:
        return {
            "regulation_id": regulation_id,
            "drift_detected": False,
            "drift_score": 0.0,
            "detected_features": [],
            "message": f"Drift analysis failed: {exc}",
        }


@router.post(
    "/ml/regulations/{regulation_id}/retrain",
    dependencies=[Depends(require_admin_key)],
)
async def retrain_model(regulation_id: str, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Enqueue a manual retraining job for a regulation."""
    from bomguard.ml.tasks import retrain_regulation_model

    reg = db.query(Regulation).filter_by(id=regulation_id).first()
    if not reg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Regulation not found.",
        )
    task = retrain_regulation_model.delay(regulation_id)
    return {
        "regulation_id": regulation_id,
        "status": "queued",
        "task_id": task.id,
    }


@router.get("/ml/stats")
async def get_stats(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Dashboard stats for the admin MLOps dashboard."""
    substance_count = db.query(Substance).count()
    regulation_count = db.query(Regulation).count()
    bom_count = db.query(Bom).count()
    summary_count = db.query(RegulatorySummary).count()
    trained_models = db.query(MLModelPerformance.regulation_id).distinct().count()
    production_models = (
        db.query(MLModelPerformance.regulation_id)
        .filter(MLModelPerformance.promoted_to_production.is_(True))
        .distinct()
        .count()
    )
    pending_changes = (
        db.query(RegulatoryChange).filter(RegulatoryChange.processed.is_(False)).count()
    )
    return {
        "substances": substance_count,
        "regulations": regulation_count,
        "boms": bom_count,
        "summaries": summary_count,
        "trained_models": trained_models,
        "production_models": production_models,
        "pending_changes": pending_changes,
        "average_drift": 0.0,
    }


async def _trigger_enrichment(batch_size: int = 50) -> dict[str, Any]:
    """Trigger backfill of regulatory summaries for all substances."""
    task = generate_all_summaries.delay(batch_size=batch_size)
    return {"status": "queued", "task_id": task.id}


@router.post("/enrich", dependencies=[Depends(require_admin_key)])
async def trigger_enrichment(batch_size: int = 50) -> dict[str, Any]:
    """Trigger backfill of regulatory summaries for all substances."""
    return await _trigger_enrichment(batch_size)


@router.post("/ml/enrich", dependencies=[Depends(require_admin_key)])
async def trigger_enrichment_legacy(batch_size: int = 50) -> dict[str, Any]:
    """Legacy path for frontend compatibility."""
    return await _trigger_enrichment(batch_size)


async def _enrichment_status(db: Session) -> dict[str, Any]:
    """Check enrichment status and whether the backfill task is running."""
    substance_count = db.query(Substance).count()
    summary_count = db.query(RegulatorySummary).count()

    task_name = "bomguard.enrichment.summary_tasks.generate_all_summaries"
    running = False
    error_message: str | None = None

    try:
        inspect = celery_app.control.inspect()
        if inspect:
            for task_list in (inspect.active() or {}).values():
                if any(t.get("name") == task_name for t in task_list):
                    running = True
                    break
            if not running:
                for task_list in (inspect.scheduled() or {}).values():
                    if any(t.get("name") == task_name for t in task_list):
                        running = True
                        break
            if not running:
                for task_list in (inspect.reserved() or {}).values():
                    if any(t.get("name") == task_name for t in task_list):
                        running = True
                        break
    except Exception as exc:  # noqa: BLE001
        error_message = f"Could not inspect Celery workers: {exc}"

    response: dict[str, Any] = {
        "substance_count": substance_count,
        "summary_count": summary_count,
        "missing": max(0, substance_count - summary_count),
        "complete": summary_count >= substance_count,
        "enrichment_running": running,
    }
    if error_message:
        response["error"] = error_message
    return response


@router.get("/enrich/status")
async def enrichment_status(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Check enrichment status and whether the backfill task is running."""
    return await _enrichment_status(db)


@router.get("/ml/enrich/status")
async def enrichment_status_legacy(db: Session = Depends(get_db)) -> dict[str, Any]:
    """Legacy path for frontend compatibility."""
    return await _enrichment_status(db)
