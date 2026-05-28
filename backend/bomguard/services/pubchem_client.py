"""PubChem PUG REST client."""

import httpx


class PubChemClient:
    """Client for PubChem PUG REST API."""

    BASE_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"

    def __init__(self) -> None:
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={"User-Agent": "BOMGuard-OpenSource/1.0"},
        )

    async def get_smiles(self, cas_number: str) -> str | None:
        """Get canonical SMILES for a CAS number."""
        return None
