"""EU RoHS Directive scraper.

RoHS restricts 10 substances in electrical/electronic equipment:
Lead, Mercury, Cadmium, Hexavalent Chromium, PBB, PBDE,
DEHP, BBP, DBP, DIBP.

There is no single public JSON API for RoHS. Data sources:
- European Commission RoHS FAQ/documents (PDF/HTML)
- National implementation lists (varies by member state)

This scraper is a skeleton; a full implementation would need:
- PDF text extraction (e.g. pypdf, pdfplumber)
- Or HTML table parsing from Commission websites
- Or manual curation with periodic verification
"""

from typing import Any, ClassVar, override

from bomguard.ingestion.base import RawSubstance, RegulationScraper

# The 10 RoHS restricted substances with CAS numbers
_ROHS_SUBSTANCES: list[dict[str, Any]] = [
    {"name": "Lead", "cas_number": "7439-92-1"},
    {"name": "Mercury", "cas_number": "7439-97-6"},
    {"name": "Cadmium", "cas_number": "7440-43-9"},
    {"name": "Hexavalent chromium", "cas_number": "18540-29-9"},
    {"name": "Polybrominated biphenyls (PBB)", "cas_number": "59536-65-1"},
    {"name": "Polybrominated diphenyl ethers (PBDE)", "cas_number": "63936-56-1"},
    {"name": "Bis(2-ethylhexyl) phthalate (DEHP)", "cas_number": "117-81-7"},
    {"name": "Butyl benzyl phthalate (BBP)", "cas_number": "85-68-7"},
    {"name": "Dibutyl phthalate (DBP)", "cas_number": "84-74-2"},
    {"name": "Diisobutyl phthalate (DIBP)", "cas_number": "84-69-5"},
]


class RoHSScraper(RegulationScraper):
    """Scraper for EU RoHS Directive 2011/65/EU.

    Currently returns a static curated list. A future implementation
    should verify this list against official Commission sources.
    """

    regulation_id: ClassVar[str] = "eu_rohs"
    source_name: ClassVar[str] = "eu_commission_rohs"

    @override
    def fetch_all(self) -> list[RawSubstance]:
        """Return the 10 RoHS restricted substances."""
        return [
            RawSubstance(
                name=item["name"],
                cas_number=item["cas_number"],
                reason_for_inclusion="Restricted under RoHS Directive 2011/65/EU",
            )
            for item in _ROHS_SUBSTANCES
        ]
