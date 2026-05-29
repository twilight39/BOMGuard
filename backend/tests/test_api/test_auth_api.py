"""Tests for auth API endpoints."""

import os
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

from bomguard.config import Settings
from bomguard.main import create_app


TEST_DB_URL = "postgresql://bomguard:bomguard@localhost:5432/bomguard_test"


@pytest.fixture
def test_client(db):
    os.environ["DATABASE_URL"] = TEST_DB_URL
    os.environ["WORKOS_API_KEY"] = "test_api_key"
    os.environ["WORKOS_CLIENT_ID"] = "test_client_id"
    settings = Settings(database_url=TEST_DB_URL)
    app = create_app(settings=settings)
    # Add session middleware for testing
    app.add_middleware(
        SessionMiddleware,
        secret_key="test-secret-key",
        max_age=604800,
        same_site="lax",
        https_only=False,
    )
    client = TestClient(app)
    yield client
    client.close()


def test_login_redirect(test_client):
    with patch(
        "bomguard.api.auth.WorkOSAuthService.get_authorization_url",
        return_value="https://auth.workos.com/oauth/authorize?test=1",
    ):
        response = test_client.get("/api/auth/login", follow_redirects=False)
        assert response.status_code == 307
        assert (
            response.headers["location"]
            == "https://auth.workos.com/oauth/authorize?test=1"
        )


def test_me_unauthenticated(test_client):
    response = test_client.get("/api/auth/me")
    assert response.status_code == 401
    assert response.json()["detail"] == "Not authenticated"


def test_logout_without_session(test_client):
    response = test_client.post("/api/auth/logout")
    assert response.status_code == 200
    assert response.json()["status"] == "logged_out"
