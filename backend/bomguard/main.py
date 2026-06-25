"""FastAPI application factory."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from alembic import command
from alembic.config import Config
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from prometheus_client import CONTENT_TYPE_LATEST, Gauge, generate_latest
from prometheus_fastapi_instrumentator import Instrumentator
from starlette.middleware.sessions import SessionMiddleware

from bomguard.api.admin import router as admin_router
from bomguard.api.ask import router as ask_router
from bomguard.api.auth import router as auth_router
from bomguard.api.boms import router as boms_router
from bomguard.api.chat import router as chat_router
from bomguard.api.enrichment import router as enrichment_router
from bomguard.api.regulations import router as regulations_router
from bomguard.api.scan import router as scan_router
from bomguard.api.substances import router as substances_router
from bomguard.config import Settings
from bomguard.models.schemas import HealthCheckResponse

# Custom gauges for ML model performance and regulatory data.
# Defined at module level so they are only registered once even if create_app()
# is called multiple times in the same process (e.g. during tests).
_ml_roc_gauge = Gauge(
    "bomguard_ml_model_roc_auc",
    "Latest ROC-AUC per regulation",
    ["regulation_id"],
)
_ml_ap_gauge = Gauge(
    "bomguard_ml_model_average_precision",
    "Latest average precision per regulation",
    ["regulation_id"],
)
_ml_brier_gauge = Gauge(
    "bomguard_ml_model_brier_score",
    "Latest Brier score per regulation",
    ["regulation_id"],
)
_ml_promoted_gauge = Gauge(
    "bomguard_ml_model_promoted",
    "Whether the latest model is promoted to production",
    ["regulation_id"],
)
_ml_days_since_trained_gauge = Gauge(
    "bomguard_ml_model_days_since_trained",
    "Days since the last model training per regulation",
    ["regulation_id"],
)
_regulation_substances_gauge = Gauge(
    "bomguard_regulation_substances",
    "Number of restricted substances per regulation",
    ["regulation_id"],
)
_last_scrape_gauge = Gauge(
    "bomguard_last_scrape_timestamp_seconds",
    "Unix timestamp of the last detected regulatory change per regulation",
    ["regulation_id"],
)


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


def seed_sample_boms_if_empty() -> None:
    """Seed sample BOMs if none exist."""
    from bomguard.db import SessionLocal
    from bomguard.seed import seed_sample_boms

    db = SessionLocal()
    try:
        seed_sample_boms(db)
    finally:
        db.close()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Application lifespan events."""
    run_migrations()
    seed_regulations_if_empty()
    seed_sample_boms_if_empty()
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

    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.secret_key,
        max_age=604800,  # 7 days
        same_site="lax",
        https_only=False,
    )

    app.include_router(auth_router)
    app.include_router(boms_router)
    app.include_router(scan_router)
    app.include_router(regulations_router)
    app.include_router(substances_router)
    app.include_router(ask_router)
    app.include_router(chat_router)
    app.include_router(enrichment_router)
    app.include_router(admin_router)

    app.mount("/static", StaticFiles(directory="static"), name="static")

    @app.get("/api/health", response_model=HealthCheckResponse)
    async def health_check() -> HealthCheckResponse:
        return HealthCheckResponse(status="ok")

    # Instrument default request metrics (rate, latency, error rate).
    instrumentator = Instrumentator()
    instrumentator.instrument(app).expose(
        app, endpoint="/api/metrics/internal", include_in_schema=False
    )

    @app.get("/api/metrics")
    async def metrics() -> PlainTextResponse:
        """Expose Prometheus metrics including custom ML performance gauges."""
        from datetime import UTC, datetime

        from sqlalchemy import func

        from bomguard.db import SessionLocal
        from bomguard.models.database import (
            MLModelPerformance,
            Regulation,
            SubstanceRegulationStatus,
        )

        db = SessionLocal()
        try:
            # Latest performance per regulation
            for reg_id_row in db.query(MLModelPerformance.regulation_id).distinct().all():
                reg_id = reg_id_row[0]
                perf = (
                    db.query(MLModelPerformance)
                    .filter_by(regulation_id=reg_id)
                    .order_by(MLModelPerformance.trained_at.desc().nullslast())
                    .first()
                )
                if perf:
                    if perf.roc_auc is not None:
                        _ml_roc_gauge.labels(regulation_id=reg_id).set(perf.roc_auc)
                    if perf.average_precision is not None:
                        _ml_ap_gauge.labels(regulation_id=reg_id).set(perf.average_precision)
                    if perf.brier_score is not None:
                        _ml_brier_gauge.labels(regulation_id=reg_id).set(perf.brier_score)
                    _ml_promoted_gauge.labels(regulation_id=reg_id).set(
                        1 if perf.promoted_to_production else 0
                    )

            # Days since last training for ML-enabled regulations
            ml_regs = db.query(Regulation).filter(Regulation.ml_enabled.is_(True)).all()
            for reg in ml_regs:
                perf = (
                    db.query(MLModelPerformance)
                    .filter_by(regulation_id=reg.id)
                    .order_by(MLModelPerformance.trained_at.desc().nullslast())
                    .first()
                )
                if perf and perf.trained_at:
                    days = (datetime.now(UTC) - perf.trained_at).total_seconds() / 86400
                    _ml_days_since_trained_gauge.labels(regulation_id=reg.id).set(days)
                else:
                    _ml_days_since_trained_gauge.labels(regulation_id=reg.id).set(-1)

            # Substance counts per regulation
            counts = (
                db.query(
                    SubstanceRegulationStatus.regulation_id,
                    func.count(SubstanceRegulationStatus.substance_id).label("cnt"),
                )
                .filter(SubstanceRegulationStatus.status == "restricted")
                .group_by(SubstanceRegulationStatus.regulation_id)
                .all()
            )
            for reg_id, cnt in counts:
                _regulation_substances_gauge.labels(regulation_id=reg_id).set(cnt)

            # Last scrape timestamp per regulation
            from bomguard.models.database import RegulatoryChange

            for reg in db.query(Regulation).all():
                latest_change = (
                    db.query(RegulatoryChange)
                    .filter_by(regulation_id=reg.id)
                    .order_by(RegulatoryChange.detected_at.desc().nullslast())
                    .first()
                )
                if latest_change and latest_change.detected_at:
                    _last_scrape_gauge.labels(regulation_id=reg.id).set(
                        latest_change.detected_at.timestamp()
                    )
                else:
                    _last_scrape_gauge.labels(regulation_id=reg.id).set(0)
        finally:
            db.close()

        return PlainTextResponse(
            content=generate_latest().decode("utf-8"),
            media_type=CONTENT_TYPE_LATEST,
        )

    return app
