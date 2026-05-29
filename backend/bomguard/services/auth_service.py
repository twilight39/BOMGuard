"""WorkOS authentication service."""

from workos import WorkOSClient
from workos.user_management.models import AuthenticateResponse, User

from bomguard.config import Settings

settings = Settings()


class WorkOSAuthService:
    """Wraps WorkOS SDK for OAuth + user management."""

    def __init__(self) -> None:
        self.client = WorkOSClient(
            api_key=settings.workos_api_key,
            client_id=settings.workos_client_id,
        )

    def get_authorization_url(self, redirect_uri: str, state: str) -> str:
        """Build WorkOS OAuth authorization URL (Google provider)."""
        return self.client.user_management.get_authorization_url(
            provider="GoogleOAuth",
            redirect_uri=redirect_uri,
            state=state,
        )

    def authenticate_with_code(self, code: str) -> AuthenticateResponse:
        """Exchange authorization code for user info."""
        return self.client.user_management.authenticate_with_code(
            code=code,
        )

    def get_user(self, user_id: str) -> User:
        """Fetch user from WorkOS."""
        return self.client.user_management.get_user(user_id)
