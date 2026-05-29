"""Tests for the TSCA scraper."""

from bomguard.ingestion.base import RawSubstance
from bomguard.services.tsca_scraper import TSCAScraper


def test_fetch_all_returns_five_substances() -> None:
    scraper = TSCAScraper()
    results = scraper.fetch_all()

    assert len(results) == 5
    assert all(isinstance(r, RawSubstance) for r in results)
    assert all(r.cas_number is not None for r in results)
    assert results[0].name == "Decabromodiphenyl ether (DecaBDE)"
    assert results[0].cas_number == "1163-19-5"


def test_regulation_id() -> None:
    assert TSCAScraper.regulation_id == "us_tsca_6h"
    assert TSCAScraper.source_name == "epa_tsca_6h"
