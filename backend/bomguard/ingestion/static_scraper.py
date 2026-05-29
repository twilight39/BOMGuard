"""Base class for scrapers backed by static JSON data files."""

import json
from pathlib import Path
from typing import Any, ClassVar

from bomguard.ingestion.base import RawSubstance, RegulationScraper

REGULATIONS_DIR = Path(__file__).parent.parent / "data" / "regulations"


class StaticListScraper(RegulationScraper):
    """Scraper that reads substance lists from a JSON file.

    Subclasses must set ``regulation_id`` and ``source_name``.
    The JSON file is expected at ``data/regulations/{regulation_id}.json``.
    """

    regulation_id: ClassVar[str] = ""
    source_name: ClassVar[str] = ""

    def fetch_all(self) -> list[RawSubstance]:
        """Load substances from the regulation's JSON data file."""
        if not self.regulation_id:
            raise RuntimeError("regulation_id must be set on the scraper class")

        path = REGULATIONS_DIR / f"{self.regulation_id}.json"
        if not path.exists():
            raise FileNotFoundError(
                f"Regulation data file not found: {path}\n"
                f"Ensure {self.regulation_id}.json exists in {REGULATIONS_DIR}"
            )

        data: dict[str, Any] = json.loads(path.read_text())
        substances: list[dict[str, Any]] = data.get("substances", [])

        return [
            RawSubstance(
                name=item["name"],
                cas_number=item.get("cas_number"),
                ec_number=item.get("ec_number"),
                reason_for_inclusion=item.get("reason_for_inclusion"),
                date_added=item.get("date_added"),
            )
            for item in substances
        ]
