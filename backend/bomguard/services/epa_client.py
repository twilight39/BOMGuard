"""EPA CompTox Dashboard API client."""

from typing import Any

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from bomguard.config import Settings


class EPACompToxError(Exception):
    """Raised when EPA CompTox API returns an unexpected error."""

    def __init__(
        self,
        message: str,
        *,
        cas_number: str | None = None,
        status_code: int | None = None,
        url: str | None = None,
    ) -> None:
        super().__init__(message)
        self.cas_number = cas_number
        self.status_code = status_code
        self.url = url


class EPACompToxClient:
    """Async client for EPA CompTox Dashboard CTX API.

    Docs: https://www.epa.gov/comptox-tools/computational-toxicology-and-exposure-apis-about
    API key required (free, request at ccte_api@epa.gov).
    """

    BASE_URL: str = "https://comptox.epa.gov/ctx-api"

    def __init__(self, api_key: str | None = None) -> None:
        self.api_key = api_key or Settings().comptox_api_key
        headers: dict[str, str] = {
            "User-Agent": "BOMGuard-OpenSource/1.0",
            "accept": "application/json",
        }
        if self.api_key:
            headers["X-Api-Key"] = self.api_key

        self.client: httpx.AsyncClient = httpx.AsyncClient(
            timeout=60.0,
            headers=headers,
            follow_redirects=True,
        )

    async def _get(self, url: str) -> dict[str, Any] | list[Any]:
        """Make a GET request and return JSON."""
        resp = await self.client.get(url)
        resp.raise_for_status()
        data: dict[str, Any] | list[Any] = resp.json()
        return data

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout)),
        reraise=True,
    )
    async def search_by_cas(self, cas_number: str) -> dict[str, Any] | None:
        """Search for a chemical by CAS number.

        Returns the first match dict with keys like dtxsid, casrn, smiles,
        preferredName, or None if not found.
        """
        url = f"{self.BASE_URL}/chemical/search/equal/{cas_number}"
        try:
            data = await self._get(url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code in (400, 404):
                return None
            raise EPACompToxError(
                f"CompTox search failed: {exc}",
                cas_number=cas_number,
                status_code=exc.response.status_code,
                url=url,
            ) from exc

        if isinstance(data, list) and data:
            return data[0]
        return None

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout)),
        reraise=True,
    )
    async def get_chemical_detail(self, dtxsid: str) -> dict[str, Any]:
        """Fetch detailed chemical information by DTXSID.

        Returns a dict with predicted properties (BCF, half-life, etc.).
        """
        url = f"{self.BASE_URL}/chemical/detail/search/by-dtxsid/{dtxsid}"
        try:
            data = await self._get(url)
        except httpx.HTTPStatusError as exc:
            raise EPACompToxError(
                f"CompTox detail lookup failed: {exc}",
                status_code=exc.response.status_code,
                url=url,
            ) from exc

        if isinstance(data, dict):
            return data
        return {}

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout)),
        reraise=True,
    )
    async def get_fate_data(self, dtxsid: str) -> list[dict[str, Any]]:
        """Fetch environmental fate data by DTXSID.

        Returns a list of property dicts with experimental and predicted fate data.
        """
        url = f"{self.BASE_URL}/chemical/fate/search/by-dtxsid/{dtxsid}"
        try:
            data = await self._get(url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return []
            raise EPACompToxError(
                f"CompTox fate lookup failed: {exc}",
                status_code=exc.response.status_code,
                url=url,
            ) from exc

        if isinstance(data, list):
            return data
        return []

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError, httpx.ReadTimeout)),
        reraise=True,
    )
    async def get_cancer_summary(self, dtxsid: str) -> list[dict[str, Any]]:
        """Fetch cancer summary/hazard data by DTXSID.

        Returns a list of cancer classification dicts.
        """
        url = f"{self.BASE_URL}/hazard/cancer-summary/search/by-dtxsid/{dtxsid}"
        try:
            data = await self._get(url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return []
            raise EPACompToxError(
                f"CompTox cancer summary lookup failed: {exc}",
                status_code=exc.response.status_code,
                url=url,
            ) from exc

        if isinstance(data, list):
            return data
        return []

    async def get_properties(self, cas_number: str) -> dict[str, Any]:
        """Fetch chemical properties by CAS number.

        Returns a dict with EPA-specific properties like bioaccumulation
        factor (bcf), half-life (half_life_soil), LC50 (lc50_fish),
        carcinogenicity_flag, and has_epa_data.
        """
        search_result = await self.search_by_cas(cas_number)
        if not search_result:
            return {"has_epa_data": False}

        dtxsid: str = search_result.get("dtxsid", "")
        if not dtxsid:
            return {"has_epa_data": False}

        # Fetch detail, fate, and hazard in parallel
        import asyncio

        detail, fate_data, cancer_data = await asyncio.gather(
            self.get_chemical_detail(dtxsid),
            self.get_fate_data(dtxsid),
            self.get_cancer_summary(dtxsid),
            return_exceptions=True,
        )

        if isinstance(detail, Exception):
            detail = {}
        if isinstance(fate_data, Exception):
            fate_data = []
        if isinstance(cancer_data, Exception):
            cancer_data = []

        result: dict[str, Any] = {"has_epa_data": True}

        # Extract BCF from detail (predicted values)
        bcf_test = detail.get("bioconcentrationFactorTestPred")
        bcf_opera = detail.get("bioconcentrationFactorOperaPred")
        result["bcf"] = bcf_test or bcf_opera

        # Extract half-life from detail
        result["half_life_soil"] = detail.get("biodegradationHalfLifeDays")

        # Extract fish toxicity proxies from detail
        result["lc50_fish"] = detail.get("hrFatheadMinnow")

        # Carcinogenicity flag from cancer summary
        result["carcinogenicity_flag"] = bool(cancer_data)

        # Supplement with fate data if detail didn't have values
        if not result.get("bcf"):
            for prop in fate_data:
                if prop.get("propName") == "Bioconcentration Factor":
                    preds = prop.get("predictedFateData", [])
                    for p in preds:
                        val = p.get("prop_value")
                        if val is not None:
                            result["bcf"] = val
                            break
                    break

        if not result.get("half_life_soil"):
            for prop in fate_data:
                if prop.get("propName") == "Biodeg. Half-Life":
                    preds = prop.get("predictedFateData", [])
                    for p in preds:
                        val = p.get("prop_value")
                        if val is not None:
                            result["half_life_soil"] = val
                            break
                    break

        # If we still have no meaningful data, mark as not enriched.
        # False for carcinogenicity_flag counts as meaningful data only if
        # it came from an actual API response (i.e., cancer_data was non-empty).
        meaningful_keys = {"bcf", "half_life_soil", "lc50_fish"}
        has_any_value = any(
            result.get(k) is not None for k in meaningful_keys
        ) or bool(cancer_data)
        if not has_any_value:
            result["has_epa_data"] = False

        return result
