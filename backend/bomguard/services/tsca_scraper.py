"""US TSCA Section 6(h) PBT scraper.

TSCA Section 6(h) restricts 5 Persistent Bioaccumulative and Toxic (PBT)
chemicals: DecaBDE, PIP (3:1), 2,4,6-TTBP, HCBD, PCTP.

Data sources:
- US EPA TSCA Section 6(h) rulemaking documents
- Federal Register publications

This scraper is a skeleton; a full implementation would parse EPA
HTML or PDF publications for the official restricted substance list.
"""

from typing import Any, ClassVar, override

from bomguard.ingestion.base import RawSubstance, RegulationScraper

# The 5 TSCA 6(h) PBT chemicals with CAS numbers
_TSCA_PBT_SUBSTANCES: list[dict[str, Any]] = [
    {"name": "Decabromodiphenyl ether (DecaBDE)", "cas_number": "1163-19-5"},
    {"name": "Phenol, isopropylated phosphate (3:1) (PIP 3:1)", "cas_number": "68937-41-7"},
    {"name": "2,4,6-Tris(tert-butyl)phenol (2,4,6-TTBP)", "cas_number": "732-26-3"},
    {"name": "Hexachlorobutadiene (HCBD)", "cas_number": "87-68-3"},
    {"name": "Pentachlorothiophenol (PCTP)", "cas_number": "133-49-3"},
]


class TSCAScraper(RegulationScraper):
    """Scraper for US TSCA Section 6(h) PBT restrictions.

    Currently returns a static curated list. A future implementation
    should verify against EPA Federal Register publications.
    """

    regulation_id: ClassVar[str] = "us_tsca_6h"
    source_name: ClassVar[str] = "epa_tsca_6h"

    @override
    def fetch_all(self) -> list[RawSubstance]:
        """Return the 5 TSCA 6(h) PBT chemicals."""
        return [
            RawSubstance(
                name=item["name"],
                cas_number=item["cas_number"],
                reason_for_inclusion="Restricted under TSCA Section 6(h) PBT rule",
            )
            for item in _TSCA_PBT_SUBSTANCES
        ]
