"""US TSCA Section 6(h) PBT scraper.

Data source: curated JSON file at ``data/regulations/us_tsca_6h.json``.

TSCA Section 6(h) restricts 5 Persistent Bioaccumulative and Toxic (PBT)
chemicals: DecaBDE, PIP (3:1), 2,4,6-TTBP, HCBD, PCTP.

The official source is the US EPA:
https://www.epa.gov/assessing-and-managing-chemicals-under-tsca/persistent-bioaccumulative-and-toxic-pbt-chemicals-under
"""

from typing import ClassVar

from bomguard.ingestion.static_scraper import StaticListScraper


class TSCAScraper(StaticListScraper):
    """Scraper for US TSCA Section 6(h) PBT restrictions.

    Reads the curated substance list from ``data/regulations/us_tsca_6h.json``.
    """

    regulation_id: ClassVar[str] = "us_tsca_6h"
    source_name: ClassVar[str] = "epa_tsca_6h"
