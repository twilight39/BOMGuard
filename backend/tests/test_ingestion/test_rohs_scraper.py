"""Tests for the RoHS scraper."""

from bomguard.ingestion.base import RawSubstance
from bomguard.services.rohs_scraper import RoHSScraper


def test_fetch_all_returns_ten_substances() -> None:
    scraper = RoHSScraper()
    results = scraper.fetch_all()

    assert len(results) == 10
    assert all(isinstance(r, RawSubstance) for r in results)
    assert all(r.cas_number is not None for r in results)
    assert results[0].name == "Lead"
    assert results[0].cas_number == "7439-92-1"


def test_regulation_id() -> None:
    assert RoHSScraper.regulation_id == "eu_rohs"
    assert RoHSScraper.source_name == "eu_commission_rohs"
