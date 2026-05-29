"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from bomguard.api.admin import router as admin_router
from bomguard.api.ask import router as ask_router
from bomguard.api.boms import router as boms_router
from bomguard.api.regulations import router as regulations_router
from bomguard.api.scan import router as scan_router
from bomguard.api.substances import router as substances_router
from bomguard.config import Settings
from bomguard.models.schemas import HealthCheckResponse


def run_migrations() -> None:
    """Run Alembic migrations on application startup."""
    alembic_cfg = Config("alembic.ini")
    command.upgrade(alembic_cfg, "head")


def seed_regulations_if_empty() -> None:
    """Seed regulation definitions if the table is empty."""
    from bomguard.db import SessionLocal
    from bomguard.models.database import Regulation
    from bomguard.seed import seed_regulations

    db = SessionLocal()
    try:
        count = db.query(Regulation).count()
        if count == 0:
            seed_regulations(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan events."""
    run_migrations()
    seed_regulations_if_empty()
    yield


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the FastAPI application."""
    settings = settings or Settings()

    app = FastAPI(
        title="BOMGuard",
        description="BOM compliance scanner with ML risk prediction and LLM RAG",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(boms_router)
    app.include_router(scan_router)
    app.include_router(regulations_router)
    app.include_router(substances_router)
    app.include_router(ask_router)
    app.include_router(admin_router)

    @app.get("/api/health", response_model=HealthCheckResponse)
    async def health_check() -> HealthCheckResponse:
        return HealthCheckResponse(status="ok")

    return app
