"""Pytest fixtures and configuration."""

from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from bomguard.models.database import Base

TEST_DB_URL = "postgresql://bomguard:bomguard@localhost:5432/bomguard_test"


def _ensure_test_db() -> None:
    """Create the test database if it doesn't exist."""
    admin_engine = create_engine(
        "postgresql://bomguard:bomguard@localhost:5432/bomguard"
    )
    with admin_engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.execute(text("SELECT 1"))
    with admin_engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = 'bomguard_test'")
        )
        if not result.scalar():
            conn.execute(text("CREATE DATABASE bomguard_test"))
    admin_engine.dispose()


@pytest.fixture(scope="session")
def engine() -> Generator[Engine, None, None]:
    """Create a test database engine."""
    _ensure_test_db()
    test_engine = create_engine(TEST_DB_URL)
    with test_engine.connect() as conn:
        conn.execution_options(isolation_level="AUTOCOMMIT")
        conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
    Base.metadata.create_all(test_engine)
    yield test_engine
    test_engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Generator[Session, None, None]:
    """Provide a transactional database session for each test."""
    connection = engine.connect()
    transaction = connection.begin()
    session_factory = sessionmaker(bind=connection)
    session = session_factory()

    yield session

    session.close()
    transaction.rollback()
    connection.close()
