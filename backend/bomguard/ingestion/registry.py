"""Scraper registry — manual map for now, auto-discovery later."""

from bomguard.ingestion.base import RegulationScraper
from bomguard.services.echa_scraper import ECHAChemScraper

_SCRAPERS: dict[str, type[RegulationScraper]] = {}


def register_scraper(scraper_cls: type[RegulationScraper]) -> None:
    """Register a scraper class."""
    _SCRAPERS[scraper_cls.regulation_id] = scraper_cls


def get_scraper(regulation_id: str) -> RegulationScraper | None:
    """Get a scraper instance by regulation ID."""
    cls = _SCRAPERS.get(regulation_id)
    return cls() if cls else None


def get_all_scrapers() -> list[RegulationScraper]:
    """Get all registered scraper instances."""
    return [cls() for cls in _SCRAPERS.values()]


# Register built-in scrapers
register_scraper(ECHAChemScraper)
