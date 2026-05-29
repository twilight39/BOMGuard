"""US State PFAS restrictions scraper.

Data source: curated JSON file at ``data/regulations/us_state_pfas.json``.

US state PFAS restrictions are fragmented across multiple states
(Maine, Washington, Vermont, California, Minnesota, New York, etc.)
with no unified federal API. This scraper returns the union of the
most commonly restricted PFAS compounds.

The EPA maintains PFAS resources at: https://www.epa.gov/pfas
"""

from typing import ClassVar

from bomguard.ingestion.static_scraper import StaticListScraper


class USStatePFASScraper(StaticListScraper):
    """Scraper for US State PFAS restrictions.

    Reads the curated substance list from ``data/regulations/us_state_pfas.json``.
    """

    regulation_id: ClassVar[str] = "us_state_pfas"
    source_name: ClassVar[str] = "multi_state_pfas"
