"""Basic health check tests."""

import pytest
from fastapi.testclient import TestClient

from bomguard.config import Settings
from bomguard.main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app(Settings())
    return TestClient(app)


def test_health_check(client: TestClient) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
