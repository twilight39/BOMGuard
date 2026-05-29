"""Tests for the China RoHS scraper."""

from bomguard.ingestion.base import RawSubstance
from bomguard.services.cn_rohs_scraper import CnRoHSScraper


def test_fetch_all_returns_ten_substances() -> None:
    scraper = CnRoHSScraper()
    results = scraper.fetch_all()

    assert len(results) == 10
    assert all(isinstance(r, RawSubstance) for r in results)
    assert all(r.cas_number is not None for r in results)


def test_first_substance_is_lead() -> None:
    scraper = CnRoHSScraper()
    results = scraper.fetch_all()

    assert results[0].name == "Lead"
    assert results[0].cas_number == "7439-92-1"
    assert results[0].reason_for_inclusion is not None
    assert "GB 26572-2025" in results[0].reason_for_inclusion


def test_phthalates_have_2026_date() -> None:
    scraper = CnRoHSScraper()
    results = scraper.fetch_all()

    dehp = next(r for r in results if "DEHP" in r.name)
    assert dehp.date_added == "2026-01-01"
    assert dehp.reason_for_inclusion is not None
    assert "GB 26572-2025" in dehp.reason_for_inclusion


def test_regulation_id() -> None:
    assert CnRoHSScraper.regulation_id == "cn_rohs"
    assert CnRoHSScraper.source_name == "miit_cn_rohs"
