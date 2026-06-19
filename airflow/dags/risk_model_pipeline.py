"""Airflow DAG for weekly ML risk model retraining."""

import logging
from datetime import datetime, timedelta
from typing import Any

from airflow import DAG
from airflow.operators.python import PythonOperator

logger = logging.getLogger(__name__)

ML_ENABLED_REGULATIONS = ["eu_reach_svhc", "us_state_pfas"]


def _alert_on_failure(context: dict[str, Any]) -> None:
    """Placeholder alert hook for failed task instances."""
    task_instance = context.get("task_instance")
    dag_id = task_instance.dag_id if task_instance else "unknown"
    task_id = task_instance.task_id if task_instance else "unknown"
    logger.error("DAG task failed: %s - %s", dag_id, task_id)
    logger.info("Would alert via email/Slack for failure.")


def refresh_substance_database() -> dict[str, Any]:
    """Run all registered regulation scrapers and ingest changes."""
    from bomguard.db import SessionLocal
    from bomguard.ingestion.pipeline import run_scraper
    from bomguard.ingestion.registry import get_all_scrapers

    db = SessionLocal()
    try:
        scrapers = get_all_scrapers()
        totals = {
            "substances_created": 0,
            "substances_updated": 0,
            "changes_detected": 0,
            "total_fetched": 0,
            "scrapers_run": 0,
        }
        for scraper in scrapers:
            result = run_scraper(scraper, db)
            totals["substances_created"] += result.substances_created
            totals["substances_updated"] += result.substances_updated
            totals["changes_detected"] += result.changes_detected
            totals["total_fetched"] += result.total_fetched
            totals["scrapers_run"] += 1
            logger.info(
                "Scraper %s completed: fetched=%d created=%d updated=%d changes=%d",
                scraper.regulation_id,
                result.total_fetched,
                result.substances_created,
                result.substances_updated,
                result.changes_detected,
            )
        db.commit()
        logger.info(
            "Refresh completed: scrapers=%d fetched=%d created=%d updated=%d changes=%d",
            totals["scrapers_run"],
            totals["total_fetched"],
            totals["substances_created"],
            totals["substances_updated"],
            totals["changes_detected"],
        )
        return totals
    finally:
        db.close()


def enrich_missing_features(batch_size: int = 50) -> dict[str, Any]:
    """Queue enrichment for substances missing properties."""
    from sqlalchemy import func

    from bomguard.db import SessionLocal
    from bomguard.enrichment.tasks import enrich_all_missing
    from bomguard.models.database import Substance, SubstanceProperties

    db = SessionLocal()
    try:
        missing_count = (
            db.query(func.count(Substance.id))
            .outerjoin(SubstanceProperties)
            .filter(SubstanceProperties.substance_id.is_(None))
            .scalar()
        ) or 0

        task = enrich_all_missing.delay(batch_size=batch_size)
        logger.info(
            "Queued enrichment for up to %d missing substances (task_id=%s, batch_size=%d)",
            missing_count,
            task.id,
            batch_size,
        )
        return {
            "missing_substances": missing_count,
            "task_id": task.id,
            "batch_size": batch_size,
        }
    finally:
        db.close()


def train_for_regulation(regulation_id: str) -> dict[str, Any]:
    """Train and persist a model for a single regulation."""
    from bomguard.db import SessionLocal
    from bomguard.ml.models.train import train_and_persist

    db = SessionLocal()
    try:
        result = train_and_persist(db, regulation_id)
        metrics = result["metrics"]
        metadata = result["metadata"]
        logger.info(
            "Training completed for %s: roc_auc=%.4f version=%s path=%s",
            regulation_id,
            metrics.get("roc_auc", 0.0),
            metadata.get("version"),
            metadata.get("model_path"),
        )
        return {
            "regulation_id": regulation_id,
            "metrics": metrics,
            "model_path": metadata.get("model_path"),
            "version": metadata.get("version"),
        }
    finally:
        db.close()


def _changes_to_df(changes: list[Any]) -> Any:
    """Convert regulatory changes to a simple feature DataFrame for drift."""
    from datetime import UTC, datetime

    import pandas as pd

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


def evaluate_all_models() -> dict[str, Any]:
    """Evaluate newly trained models against production and persist metrics."""
    from datetime import UTC, datetime

    from bomguard.config import Settings
    from bomguard.db import SessionLocal
    from bomguard.ml.models.registry import RegulationModelRegistry
    from bomguard.models.database import MLModelPerformance, Regulation

    settings = Settings()
    db = SessionLocal()
    try:
        registry = RegulationModelRegistry(settings.model_artifact_path)
        result: dict[str, Any] = {}

        for regulation_id in ML_ENABLED_REGULATIONS:
            artifact = registry.load_model(regulation_id)
            reg = db.query(Regulation).filter_by(id=regulation_id).first()
            if not reg:
                logger.warning("Regulation %s not found in database", regulation_id)
                result[regulation_id] = {
                    "new_roc_auc": None,
                    "production_roc_auc": None,
                    "model_version": None,
                    "performance_id": None,
                    "model_exists": False,
                    "message": "regulation_not_found",
                }
                continue

            if not artifact:
                logger.warning("No trained model found for %s", regulation_id)
                result[regulation_id] = {
                    "new_roc_auc": None,
                    "production_roc_auc": None,
                    "model_version": None,
                    "performance_id": None,
                    "model_exists": False,
                    "message": "no_model_artifact",
                }
                continue

            metadata = artifact.get("metadata", {})
            metrics = artifact.get("metrics", {})
            model_version = metadata.get("version")
            new_roc_auc = metrics.get("roc_auc")

            production = (
                db.query(MLModelPerformance)
                .filter_by(regulation_id=regulation_id, promoted_to_production=True)
                .order_by(MLModelPerformance.trained_at.desc().nullslast())
                .first()
            )
            production_roc_auc = production.roc_auc if production else None

            # Avoid duplicate performance rows for the same model version.
            perf = (
                db.query(MLModelPerformance)
                .filter_by(regulation_id=regulation_id, model_version=model_version)
                .first()
            )
            if not perf:
                perf = MLModelPerformance(
                    regulation_id=regulation_id,
                    model_version=model_version,
                    trained_at=datetime.now(UTC),
                    roc_auc=metrics.get("roc_auc"),
                    average_precision=metrics.get("average_precision"),
                    precision_at_100=metrics.get("precision_at_100"),
                    brier_score=metrics.get("brier_score"),
                    n_train_positive=metrics.get("n_train_positive"),
                    n_train_negative=metrics.get("n_train_negative"),
                    n_test_positive=metrics.get("n_test_positive"),
                    n_test_negative=metrics.get("n_test_negative"),
                    promoted_to_production=False,
                )
                db.add(perf)
                db.commit()

            result[regulation_id] = {
                "new_roc_auc": new_roc_auc,
                "production_roc_auc": production_roc_auc,
                "model_version": model_version,
                "performance_id": perf.id if perf else None,
                "model_exists": True,
            }
            logger.info(
                "Evaluation for %s: new_roc_auc=%s production_roc_auc=%s version=%s",
                regulation_id,
                new_roc_auc,
                production_roc_auc,
                model_version,
            )

        return result
    finally:
        db.close()


def promote_if_gates_pass(min_roc_auc: float = 0.75) -> dict[str, Any]:
    """Promote newly trained models if they pass ROC-AUC gates."""
    from datetime import UTC, datetime

    from airflow.operators.python import get_current_context

    from bomguard.db import SessionLocal
    from bomguard.models.database import MLModelPerformance, Regulation

    context = get_current_context()
    ti = context["ti"]
    eval_dict = ti.xcom_pull(task_ids="evaluate", key="return_value") or {}

    db = SessionLocal()
    try:
        decisions: dict[str, Any] = {}
        for regulation_id, data in eval_dict.items():
            if not isinstance(data, dict):
                decisions[regulation_id] = "invalid_eval_data"
                continue
            if not data.get("model_exists"):
                decisions[regulation_id] = "no_model"
                continue

            new_roc = data.get("new_roc_auc")
            production_roc = data.get("production_roc_auc")
            performance_id = data.get("performance_id")
            model_version = data.get("model_version")

            if new_roc is None:
                decisions[regulation_id] = "missing_metrics"
                continue

            beats_production = (
                production_roc is None or new_roc >= production_roc * 1.01
            )

            if new_roc >= min_roc_auc and beats_production:
                perf = (
                    db.query(MLModelPerformance)
                    .filter_by(id=performance_id)
                    .first()
                )
                if perf:
                    perf.promoted_to_production = True
                reg = db.query(Regulation).filter_by(id=regulation_id).first()
                if reg and model_version:
                    reg.ml_model_version = model_version
                    reg.last_model_trained = datetime.now(UTC)
                db.commit()
                decisions[regulation_id] = {
                    "action": "promoted",
                    "new_roc_auc": new_roc,
                    "previous_production_roc_auc": production_roc,
                    "model_version": model_version,
                }
                logger.info(
                    "Promoted %s to production (ROC-AUC %.4f, version %s)",
                    regulation_id,
                    new_roc,
                    model_version,
                )
            else:
                decisions[regulation_id] = {
                    "action": "rejected",
                    "new_roc_auc": new_roc,
                    "production_roc_auc": production_roc,
                    "reason": (
                        "below_min_threshold"
                        if new_roc < min_roc_auc
                        else "insufficient_improvement"
                    ),
                }
                logger.info(
                    "Rejected promotion for %s (ROC-AUC %.4f, production %.4f)",
                    regulation_id,
                    new_roc,
                    production_roc,
                )

        return decisions
    finally:
        db.close()


def invalidate_risk_cache() -> dict[str, Any]:
    """Invalidate cached scan/risk results after model promotion."""
    from bomguard.config import Settings

    settings = Settings()
    deleted = 0
    try:
        import redis

        client = redis.Redis.from_url(settings.redis_url, socket_connect_timeout=5)
        for pattern in ("scan_results:*", "risk:*"):
            for key in client.scan_iter(match=pattern):
                client.delete(key)
                deleted += 1
        client.close()
        logger.info("Deleted %d cache keys", deleted)
        return {"deleted_keys": deleted}
    except Exception as exc:
        logger.warning("Redis cache invalidation failed: %s", exc)
        return {"deleted_keys": 0, "warning": str(exc)}


def generate_evidently_report() -> dict[str, Any]:
    """Run Evidently drift checks on recent regulatory changes."""
    from datetime import UTC, datetime, timedelta

    from bomguard.db import SessionLocal
    from bomguard.models.database import RegulatoryChange

    db = SessionLocal()
    try:
        now = datetime.now(UTC)
        current_start = now - timedelta(days=30)
        baseline_start = now - timedelta(days=60)
        summary: dict[str, Any] = {}

        for regulation_id in ML_ENABLED_REGULATIONS:
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
                summary[regulation_id] = {
                    "drift_detected": False,
                    "drift_score": 0.0,
                    "detected_features": [],
                    "message": "Insufficient data for drift detection (need at least 5 changes in each window).",
                }
                continue

            try:
                from evidently.metric_preset import DataDriftPreset
                from evidently.report import Report

                current_df = _changes_to_df(current_changes)
                baseline_df = _changes_to_df(baseline_changes)

                report = Report(metrics=[DataDriftPreset()])
                report.run(reference_data=baseline_df, current_data=current_df)
                result = report.as_dict()

                drift_detected = False
                drift_score = 0.0
                detected_features: list[str] = []
                for metric in result.get("metrics", []):
                    metric_result = metric.get("result", {})
                    if "dataset_drift" in metric_result:
                        drift_detected = bool(
                            metric_result.get("dataset_drift", False)
                        )
                        drift_score = float(metric_result.get("drift_share", 0.0))
                    for feature, feature_result in metric_result.get(
                        "drift_by_columns", {}
                    ).items():
                        if feature_result.get("drift_detected"):
                            detected_features.append(str(feature))

                summary[regulation_id] = {
                    "drift_detected": drift_detected,
                    "drift_score": drift_score,
                    "detected_features": detected_features,
                }
                logger.info(
                    "Drift check for %s: detected=%s score=%.4f features=%s",
                    regulation_id,
                    drift_detected,
                    drift_score,
                    detected_features,
                )
            except Exception as exc:
                summary[regulation_id] = {
                    "drift_detected": False,
                    "drift_score": 0.0,
                    "detected_features": [],
                    "message": f"Drift analysis failed: {exc}",
                }
                logger.warning("Drift analysis failed for %s: %s", regulation_id, exc)

        return summary
    finally:
        db.close()


default_args = {
    "retries": 3,
    "retry_exponential_backoff": True,
    "retry_delay": timedelta(minutes=5),
    "on_failure_callback": _alert_on_failure,
}

with DAG(
    "risk_model_pipeline",
    schedule_interval="@weekly",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
) as dag:
    t1 = PythonOperator(
        task_id="refresh_substances",
        python_callable=refresh_substance_database,
    )
    t2 = PythonOperator(
        task_id="enrich_features",
        python_callable=enrich_missing_features,
        op_kwargs={"batch_size": 50},
    )
    t3 = PythonOperator(
        task_id="train_reach_model",
        python_callable=lambda: train_for_regulation("eu_reach_svhc"),
    )
    t4 = PythonOperator(
        task_id="train_pfas_model",
        python_callable=lambda: train_for_regulation("us_state_pfas"),
    )
    t5 = PythonOperator(
        task_id="evaluate",
        python_callable=evaluate_all_models,
    )
    t6 = PythonOperator(
        task_id="promote",
        python_callable=promote_if_gates_pass,
        op_kwargs={"min_roc_auc": 0.75},
    )
    t7 = PythonOperator(
        task_id="drift_check",
        python_callable=generate_evidently_report,
    )
    t8 = PythonOperator(
        task_id="invalidate_cache",
        python_callable=invalidate_risk_cache,
    )

    t1 >> t2 >> [t3, t4] >> t5 >> t6 >> t8
    t6 >> t7
