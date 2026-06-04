"""Tests for the EU RoHS scraper."""

import re

from bomguard.ingestion.base import RawSubstance
from bomguard.services.rohs_scraper import EuRoHSScraper

CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")


def test_fetch_all_returns_ten_substances() -> None:
    scraper = EuRoHSScraper()
    results = scraper.fetch_all()

    assert len(results) == 10
    assert all(isinstance(r, RawSubstance) for r in results)
    assert all(r.cas_number is not None for r in results)


def test_all_cas_numbers_valid() -> None:
    scraper = EuRoHSScraper()
    results = scraper.fetch_all()

    for r in results:
        assert r.cas_number is not None
        assert CAS_RE.match(r.cas_number), f"Invalid CAS: {r.cas_number}"


def test_first_substance_is_lead() -> None:
    scraper = EuRoHSScraper()
    results = scraper.fetch_all()

    assert results[0].name == "Lead"
    assert results[0].cas_number == "7439-92-1"
    assert results[0].ec_number == "231-100-4"
    assert results[0].reason_for_inclusion is not None
    assert "RoHS Directive" in results[0].reason_for_inclusion


def test_phthalates_have_2019_date() -> None:
    scraper = EuRoHSScraper()
    results = scraper.fetch_all()

    dehp = next(r for r in results if "DEHP" in r.name)
    assert dehp.date_added == "2019-07-22"


def test_regulation_id() -> None:
    assert EuRoHSScraper.regulation_id == "eu_rohs"
    assert EuRoHSScraper.source_name == "eu_commission_rohs"
