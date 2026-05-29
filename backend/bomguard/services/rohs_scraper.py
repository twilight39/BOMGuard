"""EU RoHS Directive scraper.

Data source: curated JSON file at ``data/regulations/eu_rohs.json``.

RoHS restricts 10 substances in electrical/electronic equipment:
Lead, Mercury, Cadmium, Hexavalent Chromium, PBB, PBDE,
DEHP, BBP, DBP, DIBP.

The official source is the European Commission:
https://environment.ec.europa.eu/topics/waste-and-recycling/rohs-directive_en
"""

from typing import ClassVar

from bomguard.ingestion.static_scraper import StaticListScraper


class EuRoHSScraper(StaticListScraper):
    """Scraper for EU RoHS Directive 2011/65/EU.

    Reads the curated substance list from ``data/regulations/eu_rohs.json``.
    """

    regulation_id: ClassVar[str] = "eu_rohs"
    source_name: ClassVar[str] = "eu_commission_rohs"
