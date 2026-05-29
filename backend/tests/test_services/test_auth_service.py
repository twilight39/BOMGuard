"""Tests for WorkOS auth service."""

from unittest.mock import MagicMock, patch

import pytest

from bomguard.services.auth_service import WorkOSAuthService


@pytest.fixture
def mock_settings():
    with patch(
        "bomguard.services.auth_service.settings"
    ) as s:
        s.workos_api_key = "test_api_key"
        s.workos_client_id = "test_client_id"
        yield s


@pytest.fixture
def auth_service(mock_settings):
    return WorkOSAuthService()


def test_get_authorization_url(auth_service):
    with patch.object(
        auth_service.client.user_management,
        "get_authorization_url",
        return_value="https://auth.workos.com/oauth/authorize?test=1",
    ) as mock_url:
        url = auth_service.get_authorization_url(
            redirect_uri="http://localhost:8000/api/auth/callback",
            state="abc123",
        )
        mock_url.assert_called_once_with(
            provider="GoogleOAuth",
            redirect_uri="http://localhost:8000/api/auth/callback",
            state="abc123",
        )
        assert url == "https://auth.workos.com/oauth/authorize?test=1"


def test_authenticate_with_code(auth_service):
    mock_response = MagicMock()
    mock_response.user.id = "user_123"
    mock_response.user.email = "test@example.com"

    with patch.object(
        auth_service.client.user_management,
        "authenticate_with_code",
        return_value=mock_response,
    ) as mock_auth:
        result = auth_service.authenticate_with_code("auth_code_123")
        mock_auth.assert_called_once_with(code="auth_code_123")
        assert result.user.id == "user_123"
        assert result.user.email == "test@example.com"


def test_get_user(auth_service):
    mock_user = MagicMock()
    mock_user.id = "user_123"
    mock_user.email = "test@example.com"

    with patch.object(
        auth_service.client.user_management,
        "get_user",
        return_value=mock_user,
    ) as mock_get:
        user = auth_service.get_user("user_123")
        mock_get.assert_called_once_with("user_123")
        assert user.id == "user_123"
