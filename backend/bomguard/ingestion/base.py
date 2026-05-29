"""Base classes for regulation scraper plugins."""

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class RawSubstance:
    """Normalized substance record from any regulatory source."""

    name: str
    cas_number: str | None = None
    ec_number: str | None = None
    reason_for_inclusion: str | None = None
    date_added: str | None = None


@dataclass
class IngestionResult:
    """Statistics from a scraper run."""

    regulation_id: str = ""
    source_name: str = ""
    substances_created: int = 0
    substances_updated: int = 0
    statuses_created: int = 0
    statuses_updated: int = 0
    changes_detected: int = 0
    total_fetched: int = 0


class RegulationScraper(ABC):
    """Base class for all regulation data scrapers.

    To add a new regulation scraper:
    1. Subclass RegulationScraper
    2. Implement regulation_id, source_name, and fetch_all()
    3. Register in ingestion/registry.py
    """

    @property
    @abstractmethod
    def regulation_id(self) -> str:
        """Database ID for the regulation (e.g. 'eu_reach_svhc')."""

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Human-readable source name (e.g. 'echa_chem_api')."""

    @abstractmethod
    def fetch_all(self) -> list[RawSubstance]:
        """Fetch all substances from the source.

        Returns a list of normalized RawSubstance records.
        Pagination, auth, and rate-limiting are the scraper's responsibility.
        """
