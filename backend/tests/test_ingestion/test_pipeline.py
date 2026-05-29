"""Tests for the generic ingestion pipeline."""

from typing import ClassVar, override

import pytest
from sqlalchemy.orm import Session

from bomguard.ingestion.base import RawSubstance, RegulationScraper
from bomguard.ingestion.pipeline import run_scraper
from bomguard.models.database import (
    Regulation,
    RegulatoryChange,
    Substance,
    SubstanceRegulationStatus,
)


class DummyScraper(RegulationScraper):
    """Test scraper that returns canned data."""

    regulation_id: ClassVar[str] = "test_reg"
    source_name: ClassVar[str] = "dummy"

    def __init__(self, items: list[RawSubstance]) -> None:
        self._items: list[RawSubstance] = items

    @override
    def fetch_all(self) -> list[RawSubstance]:
        return self._items


@pytest.fixture
def seed_regulation(db: Session) -> Regulation:
    """Seed a test regulation."""
    reg = Regulation(
        id="test_reg",
        name="Test Regulation",
    )
    db.add(reg)
    db.commit()
    return reg


def test_creates_new_substance_and_status(
    db: Session, seed_regulation: Regulation
) -> None:
    _ = seed_regulation
    scraper = DummyScraper(
        [
            RawSubstance(
                name="Lead",
                cas_number="7439-92-1",
                ec_number="231-100-4",
                date_added="04-Feb-2026",
            )
        ]
    )

    result = run_scraper(scraper, db)

    assert result.total_fetched == 1
    assert result.substances_created == 1
    assert result.statuses_created == 1
    assert result.changes_detected == 1

    sub = db.query(Substance).filter_by(cas_number="7439-92-1").first()
    assert sub is not None
    assert sub.name == "Lead"
    assert sub.ec_number == "231-100-4"
    assert sub.change_hash is not None

    status = (
        db.query(SubstanceRegulationStatus)
        .filter_by(substance_id=sub.id, regulation_id="test_reg")
        .first()
    )
    assert status is not None
    assert status.status == "restricted"

    change = (
        db.query(RegulatoryChange)
        .filter_by(substance_id=sub.id, regulation_id="test_reg")
        .first()
    )
    assert change is not None
    assert change.change_type == "added"
    assert change.new_hash == sub.change_hash


def test_detects_change_on_re_scrape(
    db: Session, seed_regulation: Regulation
) -> None:
    _ = seed_regulation
    # First scrape
    scraper1 = DummyScraper(
        [RawSubstance(name="Lead", cas_number="7439-92-1")]
    )
    run_scraper(scraper1, db)

    sub = db.query(Substance).filter_by(cas_number="7439-92-1").first()
    assert sub is not None
    original_hash = sub.change_hash

    # Second scrape with changed name
    scraper2 = DummyScraper(
        [RawSubstance(name="Lead (updated)", cas_number="7439-92-1")]
    )
    result = run_scraper(scraper2, db)

    assert result.substances_updated == 1
    assert result.changes_detected == 1
    assert result.statuses_created == 0

    sub = db.query(Substance).filter_by(cas_number="7439-92-1").first()
    assert sub is not None
    assert sub.name == "Lead (updated)"
    assert sub.change_hash != original_hash

    changes = (
        db.query(RegulatoryChange)
        .filter_by(substance_id=sub.id, regulation_id="test_reg")
        .all()
    )
    assert len(changes) == 2
    assert changes[1].change_type == "amended"
    assert changes[1].old_hash == original_hash


def test_no_change_on_identical_re_scrape(
    db: Session, seed_regulation: Regulation
) -> None:
    _ = seed_regulation
    scraper = DummyScraper(
        [RawSubstance(name="Lead", cas_number="7439-92-1")]
    )
    _ = run_scraper(scraper, db)
    result = run_scraper(scraper, db)

    assert result.changes_detected == 0
    assert result.substances_created == 0
    assert result.statuses_created == 0
