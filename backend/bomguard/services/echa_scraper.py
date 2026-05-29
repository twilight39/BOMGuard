"""ECHA CHEM API scraper for REACH SVHC Candidate List."""

from typing import Any, ClassVar, override

import httpx

from bomguard.ingestion.base import RawSubstance, RegulationScraper


class ECHAChemScraper(RegulationScraper):
    """Scraper for EU REACH SVHC Candidate List via ECHA CHEM API.

    Uses the internal ECHA CHEM obligation-list API:
    https://chem.echa.europa.eu/api-obligation-list/v1/candidateList
    """

    regulation_id: ClassVar[str] = "eu_reach_svhc"
    source_name: ClassVar[str] = "echa_chem_api"
    BASE_URL: str = "https://chem.echa.europa.eu/api-obligation-list/v1/candidateList"

    def __init__(self) -> None:
        self.client: httpx.Client = httpx.Client(
            timeout=30.0,
            headers={"User-Agent": "BOMGuard-OpenSource/1.0"},
        )

    @override
    def fetch_all(self) -> list[RawSubstance]:
        """Fetch all SVHC entries from paginated API."""
        substances: list[RawSubstance] = []
        page = 1
        total_pages = 1

        while page <= total_pages:
            resp = self.client.get(
                self.BASE_URL,
                params={
                    "pageIndex": page,
                    "pageSize": 100,
                    "showMembers": "false",
                },
            )
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()

            state: dict[str, Any] = data.get("state", {})
            total_pages = state.get("totalPages", 1)

            for item in data.get("items", []):
                substances.append(self._parse_item(item))

            page += 1

        return substances

    def _parse_item(self, item: dict[str, Any]) -> RawSubstance:
        names: list[str] = item.get("substanceName", [])
        ec_numbers: list[str] = item.get("ecNumber", [])
        cas_numbers: list[str] = item.get("casNumber", [])
        reasons: list[str] = item.get("reasonForInclusion", [])

        name: str = names[0] if names else ""
        ec: str | None = ec_numbers[0] if ec_numbers else None
        cas: str | None = cas_numbers[0] if cas_numbers else None

        # ECHA uses "-" for missing values
        if ec == "-":
            ec = None
        if cas == "-":
            cas = None

        reason: str | None = reasons[0] if reasons else None

        return RawSubstance(
            name=name,
            cas_number=cas,
            ec_number=ec,
            reason_for_inclusion=reason,
            date_added=item.get("dateOfInclusion"),
        )
