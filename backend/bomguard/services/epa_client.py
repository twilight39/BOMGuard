"""EPA CompTox API client."""

from typing import Any

import httpx


class EPACompToxClient:
    """Client for EPA CompTox Dashboard API.

    Docs: https://comptox.epa.gov/dashboard-api
    """

    BASE_URL: str = "https://comptox.epa.gov/dashboard-api"

    def __init__(self) -> None:
        self.client: httpx.AsyncClient = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "BOMGuard-OpenSource/1.0"},
        )

    async def get_properties(self, cas_number: str) -> dict[str, Any]:
        """Fetch chemical properties by CAS number.

        Returns a dict with EPA-specific properties like bioaccumulation
        factor, half-life, LC50, etc.

        Note: The public CompTox API endpoints are limited. A full
        implementation may need authenticated access or screen scraping.
        """
        _ = cas_number
        return {}
