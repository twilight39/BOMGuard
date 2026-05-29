"""PubChem PUG REST client."""

from typing import Any

import httpx


class PubChemClient:
    """Client for PubChem PUG REST API.

    Docs: https://pubchem.ncbi.nlm.nih.gov/docs/pug-rest
    """

    BASE_URL: str = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    def __init__(self) -> None:
        self.client: httpx.AsyncClient = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "BOMGuard-OpenSource/1.0"},
            follow_redirects=True,
        )

    async def get_smiles(self, cas_number: str) -> str | None:
        """Get canonical SMILES for a CAS number via PubChem name lookup.

        Returns None if not found or on error.
        """
        url = f"{self.BASE_URL}/compound/name/{cas_number}/property/IsomericSMILES/JSON"
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            props: list[dict[str, Any]] = data.get("PropertyTable", {}).get("Properties", [])
            if props:
                return props[0].get("IsomericSMILES")
        except Exception:
            pass
        return None

    async def get_properties(self, cas_number: str) -> dict[str, Any]:
        """Fetch molecular properties by CAS number.

        Returns a dict with keys like MolecularWeight, XLogP, etc.
        """
        url = (
            f"{self.BASE_URL}/compound/name/{cas_number}/property/"
            "MolecularWeight,XLogP,HBondDonorCount,HBondAcceptorCount,"
            "TPSA,RotatableBondCount/JSON"
        )
        try:
            resp = await self.client.get(url)
            resp.raise_for_status()
            data: dict[str, Any] = resp.json()
            props: list[dict[str, Any]] = data.get("PropertyTable", {}).get("Properties", [])
            return props[0] if props else {}
        except Exception:
            return {}
