"""Celery tasks for ML model training."""

from typing import Any

from bomguard.celery_app import celery_app
from bomguard.db import SessionLocal
from bomguard.ml.models.train import train_and_persist


@celery_app.task(bind=True, max_retries=3)
def retrain_regulation_model(self: Any, regulation_id: str) -> dict[str, Any]:
    """Retrain and persist a regulation-specific model.

    Creates a fresh database session, loads labelled data, runs the full
    XGBoost + Optuna + calibration pipeline, persists the artifact, and
    updates the ``Regulation`` record.
    """
    db = SessionLocal()
    try:
        result = train_and_persist(db, regulation_id)
        return {
            "regulation_id": regulation_id,
            "status": "completed",
            "metrics": result["metrics"],
            "metadata": result["metadata"],
        }
    except Exception as exc:
        raise self.retry(exc=exc, countdown=60) from exc
    finally:
        db.close()
