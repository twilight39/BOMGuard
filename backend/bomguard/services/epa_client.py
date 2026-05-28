"""EPA CompTox API client."""

import httpx


class EPACompToxClient:
    """Client for EPA CompTox API."""

    BASE_URL = "https://comptox.epa.gov/dashboard-api"

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "BOMGuard-OpenSource/1.0"},
        )

    async def get_properties(self, cas_number: str) -> dict:
        """Fetch chemical properties by CAS number."""
        return {}
