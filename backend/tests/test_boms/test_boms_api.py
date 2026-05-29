"""Tests for the BOM API endpoints."""

import io
from collections.abc import Generator

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from bomguard.db import get_db
from bomguard.main import create_app
from bomguard.models.database import Bom, BomPart

app = create_app()
client = TestClient(app)


def _csv_file(df: pd.DataFrame, filename: str = "test.csv") -> tuple[bytes, str]:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8"), filename


@pytest.fixture(autouse=True)
def override_get_db(db: Session) -> Generator[None, None, None]:
    """Override the get_db dependency to use the test session."""
    def _get_db() -> Generator[Session, None, None]:
        yield db

    app.dependency_overrides[get_db] = _get_db
    yield
    app.dependency_overrides.clear()


def test_upload_csv(db: Session) -> None:
    data, name = _csv_file(pd.DataFrame({
        "Part Number": ["R1", "C1"],
        "Manufacturer": ["Yageo", "Murata"],
        "Quantity": [10, 20],
    }))
    response = client.post(
        "/api/boms/upload",
        files={"file": (name, io.BytesIO(data), "text/csv")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == name
    assert body["status"] == "pending"
    assert isinstance(body["id"], int)


def test_upload_invalid_format(db: Session) -> None:
    response = client.post(
        "/api/boms/upload",
        files={"file": ("test.txt", io.BytesIO(b"hello"), "text/plain")},
    )
    assert response.status_code == 422


def test_upload_empty_file(db: Session) -> None:
    response = client.post(
        "/api/boms/upload",
        files={"file": ("empty.csv", io.BytesIO(b""), "text/csv")},
    )
    assert response.status_code == 422


def test_list_boms(db: Session) -> None:
    # Seed a BOM
    bom = Bom(name="test", source_type="upload", total_parts=2)
    db.add(bom)
    db.commit()

    response = client.get("/api/boms/")
    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["name"] == "test"


def test_get_bom_detail(db: Session) -> None:
    bom = Bom(name="detail", source_type="upload", total_parts=1)
    db.add(bom)
    db.flush()
    part = BomPart(bom_id=bom.id, part_number="R1", quantity=10)
    db.add(part)
    db.commit()

    response = client.get(f"/api/boms/{bom.id}")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "detail"
    assert len(body["parts"]) == 1
    assert body["parts"][0]["part_number"] == "R1"


def test_get_bom_not_found(db: Session) -> None:
    response = client.get("/api/boms/99999")
    assert response.status_code == 404


def test_delete_bom(db: Session) -> None:
    bom = Bom(name="delete_me", source_type="upload", total_parts=0)
    db.add(bom)
    db.commit()

    response = client.delete(f"/api/boms/{bom.id}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True

    # Verify gone
    response = client.get(f"/api/boms/{bom.id}")
    assert response.status_code == 404


def test_delete_bom_not_found(db: Session) -> None:
    response = client.delete("/api/boms/99999")
    assert response.status_code == 404
