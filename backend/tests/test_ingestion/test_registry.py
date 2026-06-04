"""Tests for the scraper registry."""

from bomguard.ingestion.registry import get_all_scrapers, get_scraper
from bomguard.services.cn_rohs_scraper import CnRoHSScraper
from bomguard.services.echa_scraper import ECHAChemScraper
from bomguard.services.rohs_scraper import EuRoHSScraper
from bomguard.services.tsca_scraper import TSCAScraper
from bomguard.services.us_pfas_scraper import USStatePFASScraper

EXPECTED_SCRAPERS: dict[str, type] = {
    "eu_reach_svhc": ECHAChemScraper,
    "eu_rohs": EuRoHSScraper,
    "us_tsca_6h": TSCAScraper,
    "cn_rohs": CnRoHSScraper,
    "us_state_pfas": USStatePFASScraper,
}


def test_all_scrapers_registered() -> None:
    scrapers = get_all_scrapers()
    ids = {s.regulation_id for s in scrapers}
    assert ids == set(EXPECTED_SCRAPERS.keys())


def test_get_scraper_by_id() -> None:
    for reg_id, scraper_cls in EXPECTED_SCRAPERS.items():
        scraper = get_scraper(reg_id)
        assert scraper is not None
        assert isinstance(scraper, scraper_cls)
        assert scraper.regulation_id == reg_id


def test_get_scraper_unknown_returns_none() -> None:
    assert get_scraper("nonexistent") is None
