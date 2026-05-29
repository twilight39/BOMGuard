"""China RoHS scraper.

Data source: curated JSON file at ``data/regulations/cn_rohs.json``.

China RoHS 2 (GB 26572-2025) restricts 10 substances in electrical and
electronic products, aligned with the EU RoHS substance list.

The official source is the State Administration for Market Regulation (SAMR)
and the Ministry of Industry and Information Technology (MIIT).
"""

from typing import ClassVar

from bomguard.ingestion.static_scraper import StaticListScraper


class CnRoHSScraper(StaticListScraper):
    """Scraper for China RoHS 2 (GB 26572-2025).

    Reads the curated substance list from ``data/regulations/cn_rohs.json``.
    """

    regulation_id: ClassVar[str] = "cn_rohs"
    source_name: ClassVar[str] = "miit_cn_rohs"
