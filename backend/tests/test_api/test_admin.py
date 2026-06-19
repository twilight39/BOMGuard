"""Tests for admin / MLOps endpoints."""

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text

from bomguard.api.admin import get_db
from bomguard.api.admin import router as admin_router
from bomguard.config import Settings
from bomguard.models.database import MLModelPerformance, RegulatoryChange


def _db_available() -> bool:
    """Check whether the local PostgreSQL test database is reachable."""
    try:
        engine = create_engine("postgresql://bomguard:bomguard@localhost:5432/bomguard")
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:  # noqa: BLE001
        return False


DB_AVAILABLE = _db_available()
requires_db = pytest.mark.skipif(
    not DB_AVAILABLE, reason="PostgreSQL test database not available"
)


def _make_admin_client(db: Any, admin_api_key: str | None) -> TestClient:
    """Build a minimal FastAPI app with the admin router and a DB override."""
    import bomguard.api.admin as admin_module

    app = FastAPI()
    app.include_router(admin_router)
    app.dependency_overrides[get_db] = lambda: db
    # Patching the module-level settings used by require_admin_key.
    admin_module.settings = Settings(admin_api_key=admin_api_key)
    return TestClient(app)


@pytest.fixture
def admin_client() -> TestClient:
    """Test client with a mocked DB and a configured admin key."""
    return _make_admin_client(MagicMock(), "test-admin-key")


@pytest.fixture
def admin_db_client(db: Any) -> TestClient:
    """Test client wired to the transactional test DB."""
    return _make_admin_client(db, "test-admin-key")


@requires_db
def test_performance_endpoint_with_record(
    admin_db_client: TestClient, db: Any, seed_regulation: Any
) -> None:
    """The performance endpoint returns the latest MLModelPerformance row."""
    perf = MLModelPerformance(
        regulation_id=seed_regulation.id,
        model_version="v1.2.3",
        mlflow_run_id="run-123",
        trained_at=datetime.now(UTC),
        roc_auc=0.91,
        average_precision=0.82,
        precision_at_100=0.73,
        brier_score=0.04,
        n_train_positive=100,
        n_train_negative=200,
        n_test_positive=25,
        n_test_negative=75,
        promoted_to_production=True,
    )
    db.add(perf)
    db.commit()

    response = admin_db_client.get(f"/api/admin/ml/regulations/{seed_regulation.id}/performance")
    assert response.status_code == 200
    data = response.json()
    assert data["regulation_id"] == seed_regulation.id
    assert data["model_version"] == "v1.2.3"
    assert data["mlflow_run_id"] == "run-123"
    assert data["promoted_to_production"] is True
    assert data["metrics"]["roc_auc"] == pytest.approx(0.91)
    assert data["metrics"]["average_precision"] == pytest.approx(0.82)
    assert data["sample_counts"]["n_train_positive"] == 100
    assert data["sample_counts"]["n_test_negative"] == 75


@requires_db
def test_performance_endpoint_not_found(admin_db_client: TestClient, seed_regulation: Any) -> None:
    """A 404 is returned when no performance record exists."""
    response = admin_db_client.get(f"/api/admin/ml/regulations/{seed_regulation.id}/performance")
    assert response.status_code == 404
    assert "No model performance records" in response.json()["detail"]


@requires_db
def test_drift_endpoint_returns_expected_keys(
    admin_db_client: TestClient, seed_regulation: Any
) -> None:
    """The drift endpoint always returns the expected keys."""
    response = admin_db_client.get(f"/api/admin/ml/regulations/{seed_regulation.id}/drift")
    assert response.status_code == 200
    data = response.json()
    assert "drift_detected" in data
    assert "drift_score" in data
    assert "detected_features" in data
    assert data["drift_detected"] is False


@requires_db
def test_drift_endpoint_with_mocked_evidently(
    admin_db_client: TestClient, db: Any, seed_regulation: Any, monkeypatch: Any
) -> None:
    """Drift detection returns parsed results when Evidently reports drift."""
    now = datetime.now(UTC)
    for i in range(5):
        db.add(
            RegulatoryChange(
                regulation_id=seed_regulation.id,
                change_type="added",
                detected_at=now - timedelta(days=5, hours=i),
            )
        )
        db.add(
            RegulatoryChange(
                regulation_id=seed_regulation.id,
                change_type="updated",
                detected_at=now - timedelta(days=35, hours=i),
            )
        )
    db.commit()

    mock_report = MagicMock()
    mock_report.as_dict.return_value = {
        "metrics": [
            {"result": {"dataset_drift": True, "drift_share": 0.42}},
            {
                "result": {
                    "drift_by_columns": {
                        "change_type": {"drift_detected": True},
                        "hour_of_day": {"drift_detected": False},
                    }
                }
            },
        ]
    }
    monkeypatch.setattr("evidently.report.Report", lambda _metrics: mock_report)
    monkeypatch.setattr("evidently.metric_preset.DataDriftPreset", lambda: MagicMock())

    response = admin_db_client.get(f"/api/admin/ml/regulations/{seed_regulation.id}/drift")
    assert response.status_code == 200
    data = response.json()
    assert data["drift_detected"] is True
    assert data["drift_score"] == pytest.approx(0.42)
    assert "change_type" in data["detected_features"]
    assert "hour_of_day" not in data["detected_features"]


def test_retrain_endpoint_queues_task(admin_client: TestClient) -> None:
    """The retrain endpoint enqueues a Celery task and returns its ID."""
    with patch("bomguard.ml.tasks.retrain_regulation_model") as mock_task:
        mock_task.delay.return_value = MagicMock(id="celery-task-id")
        response = admin_client.post(
            "/api/admin/ml/regulations/test_reg/retrain",
            headers={"X-Admin-API-Key": "test-admin-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["task_id"] == "celery-task-id"
        assert data["regulation_id"] == "test_reg"
        mock_task.delay.assert_called_once_with("test_reg")


def test_retrain_endpoint_requires_admin_key(admin_client: TestClient, monkeypatch: Any) -> None:
    """Retraining is rejected without a valid admin key."""
    import bomguard.api.admin as admin_module

    monkeypatch.setattr(admin_module, "settings", Settings(admin_api_key="secret-key"))
    response = admin_client.post("/api/admin/ml/regulations/test_reg/retrain")
    assert response.status_code == 403
    assert "admin API key" in response.json()["detail"]


def test_enrich_endpoint_requires_admin_key(admin_client: TestClient, monkeypatch: Any) -> None:
    """Bulk enrichment is rejected without a valid admin key."""
    import bomguard.api.admin as admin_module

    monkeypatch.setattr(admin_module, "settings", Settings(admin_api_key="secret-key"))
    response = admin_client.post("/api/admin/enrich")
    assert response.status_code == 403


def test_enrich_endpoint_with_valid_key(admin_client: TestClient) -> None:
    """Bulk enrichment queues the generate_all_summaries task."""
    with patch("bomguard.api.admin.generate_all_summaries") as mock_task:
        mock_task.delay.return_value = MagicMock(id="enrich-task-id")
        response = admin_client.post(
            "/api/admin/enrich?batch_size=10",
            headers={"X-Admin-API-Key": "test-admin-key"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "queued"
        assert data["task_id"] == "enrich-task-id"
        mock_task.delay.assert_called_once_with(batch_size=10)


@requires_db
def test_stats_endpoint_returns_aggregates(admin_db_client: TestClient, db: Any) -> None:
    """Stats include base counts plus trained/production model counts."""
    response = admin_db_client.get("/api/admin/ml/stats")
    assert response.status_code == 200
    data = response.json()
    assert "substances" in data
    assert "regulations" in data
    assert "boms" in data
    assert "summaries" in data
    assert "trained_models" in data
    assert "production_models" in data
    assert "pending_changes" in data
    assert "average_drift" in data


@requires_db
def test_enrichment_status_endpoint(admin_db_client: TestClient) -> None:
    """Enrichment status returns counts and a running flag."""
    response = admin_db_client.get("/api/admin/enrich/status")
    assert response.status_code == 200
    data = response.json()
    assert "substance_count" in data
    assert "summary_count" in data
    assert "missing" in data
    assert "complete" in data
    assert "enrichment_running" in data
