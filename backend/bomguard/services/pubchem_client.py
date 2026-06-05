"""PubChem PUG REST client with retries and rate limiting."""

import asyncio
from typing import Any
from urllib.parse import quote

import httpx
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)


class PubChemError(Exception):
    """Raised when PubChem API returns an unexpected error."""

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


class PubChemClient:
    """Async client for PubChem PUG REST API.

    Docs: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
    Rate limit: ~5 requests/second (enforced via semaphore).
    """

    BASE_URL: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    def __init__(self, max_concurrency: int = 3) -> None:
        self.client: httpx.AsyncClient = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "BOMGuard-OpenSource/1.0"},
            follow_redirects=True,
        )
        self._semaphore: asyncio.Semaphore | None = (
            None if max_concurrency <= 0 else asyncio.Semaphore(max_concurrency)
        )

    async def _get(self, url: str) -> dict[str, Any]:
        """Make a rate-limited GET request with retries."""

        async def _fetch() -> dict[str, Any]:
            resp = await self.client.get(url)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            return data

        if self._semaphore is not None:
            async with self._semaphore:
                return await _fetch()
        return await _fetch()

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
        reraise=True,
    )
    async def get_smiles(self, cas_number: str) -> str | None:
        """Get canonical SMILES for a CAS number.

        Returns None if not found or on error.
        Raises PubChemError on unexpected failures.
        """
        encoded = quote(cas_number, safe="")
        url = f"{self.BASE_URL}/compound/name/{encoded}/property/IsomericSMILES/JSON"
        try:
            data = await self._get(url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise PubChemError(
                f"PubChem SMILES lookup failed: {exc}",
                cas_number=cas_number,
                status_code=exc.response.status_code,
                url=url,
            ) from exc

        props: list[dict[str, Any]] = data.get("PropertyTable", {}).get("Properties", [])
        if not props:
            return None
        return props[0].get("IsomericSMILES") or props[0].get("SMILES")

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPStatusError, httpx.ConnectError)),
        reraise=True,
    )
    async def get_properties(self, cas_number: str) -> dict[str, Any]:
        """Fetch molecular properties by CAS number.

        Returns a dict with keys like MolecularWeight, XLogP, HBondDonorCount, etc.
        Returns an empty dict on 404 or unexpected errors.
        """
        encoded = quote(cas_number, safe="")
        url = (
            f"{self.BASE_URL}/compound/name/{encoded}/property/"
            "MolecularWeight,XLogP,HBondDonorCount,HBondAcceptorCount,"
            "TPSA,RotatableBondCount/JSON"
        )
        try:
            data = await self._get(url)
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return {}
            raise PubChemError(
                f"PubChem properties lookup failed: {exc}",
                cas_number=cas_number,
                status_code=exc.response.status_code,
                url=url,
            ) from exc

        props: list[dict[str, Any]] = data.get("PropertyTable", {}).get("Properties", [])
        return props[0] if props else {}
