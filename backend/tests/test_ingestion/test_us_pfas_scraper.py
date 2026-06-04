"""Tests for the US State PFAS scraper."""

import re

from bomguard.ingestion.base import RawSubstance
from bomguard.services.us_pfas_scraper import USStatePFASScraper

CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")


def test_fetch_all_returns_substances() -> None:
    scraper = USStatePFASScraper()
    results = scraper.fetch_all()

    assert len(results) >= 10
    assert all(isinstance(r, RawSubstance) for r in results)
    assert all(r.cas_number is not None for r in results)


def test_all_cas_numbers_valid() -> None:
    scraper = USStatePFASScraper()
    results = scraper.fetch_all()

    for r in results:
        assert r.cas_number is not None
        assert CAS_RE.match(r.cas_number), f"Invalid CAS: {r.cas_number}"


def test_first_substance_is_pfoa() -> None:
    scraper = USStatePFASScraper()
    results = scraper.fetch_all()

    assert results[0].name == "Perfluorooctanoic acid (PFOA)"
    assert results[0].cas_number == "335-67-1"


def test_no_duplicate_cas_numbers() -> None:
    scraper = USStatePFASScraper()
    results = scraper.fetch_all()

    cas_numbers = [r.cas_number for r in results]
    assert len(cas_numbers) == len(set(cas_numbers))


def test_regulation_id() -> None:
    assert USStatePFASScraper.regulation_id == "us_state_pfas"
    assert USStatePFASScraper.source_name == "multi_state_pfas"
