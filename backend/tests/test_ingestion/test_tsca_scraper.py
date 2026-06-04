"""Tests for the TSCA scraper."""

import re

from bomguard.ingestion.base import RawSubstance
from bomguard.services.tsca_scraper import TSCAScraper

CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")


def test_fetch_all_returns_five_substances() -> None:
    scraper = TSCAScraper()
    results = scraper.fetch_all()

    assert len(results) == 5
    assert all(isinstance(r, RawSubstance) for r in results)
    assert all(r.cas_number is not None for r in results)


def test_all_cas_numbers_valid() -> None:
    scraper = TSCAScraper()
    results = scraper.fetch_all()

    for r in results:
        assert r.cas_number is not None
        assert CAS_RE.match(r.cas_number), f"Invalid CAS: {r.cas_number}"


def test_first_substance_is_decabde() -> None:
    scraper = TSCAScraper()
    results = scraper.fetch_all()

    assert results[0].name == "Decabromodiphenyl ether (DecaBDE)"
    assert results[0].cas_number == "1163-19-5"
    assert results[0].reason_for_inclusion is not None
    assert "TSCA Section 6(h)" in results[0].reason_for_inclusion


def test_all_have_2021_effective_date() -> None:
    scraper = TSCAScraper()
    results = scraper.fetch_all()

    for r in results:
        assert r.date_added == "2021-03-08"


def test_regulation_id() -> None:
    assert TSCAScraper.regulation_id == "us_tsca_6h"
    assert TSCAScraper.source_name == "epa_tsca_6h"
