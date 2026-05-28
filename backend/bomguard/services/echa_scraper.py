"""ECHA REACH SVHC web scraper."""

import hashlib
import random
import time

import requests
from bs4 import BeautifulSoup


class ECHAScraper:
    """Scraper for ECHA REACH SVHC Candidate List."""

    SOURCE_ID = "echa_reach"
    CANDIDATE_LIST_URL = "https://echa.europa.eu/candidate-list-table"

    def __init__(self) -> None:
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "BOMGuard-OpenSource/1.0"
        })

    def fetch_all(self) -> list[dict]:
        """Fetch all SVHC entries from paginated table."""
        substances = []
        for page in range(1, 7):
            resp = self._backoff_request(
                f"{self.CANDIDATE_LIST_URL}?p_p_id=disssimplesearch_WAR_disssearchportlet"
                f"&_disssimplesearch_WAR_disssearchportlet_formDate=1234567890"
                f"&_disssimplesearch_WAR_disssearchportlet_sspState=normal"
                f"&_disssimplesearch_WAR_disssearchportlet_cur={page}"
            )
            soup = BeautifulSoup(resp.text, "html.parser")
            rows = soup.select("table tbody tr")
            for row in rows:
                cells = row.find_all("td")
                if len(cells) >= 4:
                    substances.append({
                        "name": cells[0].text.strip(),
                        "ec_number": cells[1].text.strip() if cells[1].text.strip() != "-" else None,
                        "cas_number": cells[2].text.strip() if cells[2].text.strip() != "-" else None,
                        "date_added": cells[3].text.strip(),
                    })
        return substances

    def get_change_hash(self, raw_html: str) -> str:
        return hashlib.sha256(raw_html.encode()).hexdigest()

    def _backoff_request(self, url: str, max_retries: int = 3) -> requests.Response:
        for attempt in range(max_retries):
            try:
                resp = self.session.get(url, timeout=30)
                resp.raise_for_status()
                return resp
            except requests.RequestException:
                time.sleep(2 ** attempt + random.uniform(0, 1))
        raise RuntimeError(f"Failed to fetch {url} after {max_retries} retries")
