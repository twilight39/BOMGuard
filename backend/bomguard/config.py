"""Pydantic settings for BOMGuard."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://bomguard:bomguard@localhost:5432/bomguard"
    redis_url: str = "redis://localhost:6379/0"
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:5173"]

    gemini_api_key: str | None = None
    mlflow_tracking_uri: str = "http://localhost:5000"

    # WorkOS auth
    workos_api_key: str | None = None
    workos_client_id: str | None = None

    # Session cookie signing (required for auth)
    secret_key: str = "dev-secret-change-in-prod"
    frontend_url: str = "http://localhost:3000"
