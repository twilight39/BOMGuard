"""Tests for the hardened PubChem client."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from bomguard.services.pubchem_client import PubChemClient


@pytest.fixture
def client() -> PubChemClient:
    return PubChemClient(max_concurrency=1)


def _make_response(json_data: dict[str, Any], status_code: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.status_code = status_code
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "error", request=MagicMock(), response=resp
        )
    return resp


@pytest.mark.asyncio
async def test_get_smiles_success(client: PubChemClient) -> None:
    data = {"PropertyTable": {"Properties": [{"IsomericSMILES": "CCO"}]}}
    with patch.object(client.client, "get", new_callable=AsyncMock, return_value=_make_response(data)) as mock_get:
        result = await client.get_smiles("64-17-5")
    assert result == "CCO"
    mock_get.assert_awaited_once()


@pytest.mark.asyncio
async def test_get_smiles_not_found_returns_none(client: PubChemClient) -> None:
    resp = _make_response({}, status_code=404)
    with patch.object(client.client, "get", new_callable=AsyncMock, return_value=resp):
        result = await client.get_smiles("999-99-9")
    assert result is None


@pytest.mark.asyncio
async def test_get_smiles_retry_then_success(client: PubChemClient) -> None:
    data = {"PropertyTable": {"Properties": [{"IsomericSMILES": "CCO"}]}}
    side_effects = [
        httpx.ConnectError("connection failed"),
        _make_response(data),
    ]
    with patch.object(client.client, "get", new_callable=AsyncMock, side_effect=side_effects):
        result = await client.get_smiles("64-17-5")
    assert result == "CCO"


@pytest.mark.asyncio
async def test_get_smiles_retry_exhausted_raises(client: PubChemClient) -> None:
    with patch.object(
        client.client, "get", new_callable=AsyncMock, side_effect=httpx.ConnectError("fail")
    ), pytest.raises(httpx.ConnectError):
        await client.get_smiles("64-17-5")


@pytest.mark.asyncio
async def test_get_properties_success(client: PubChemClient) -> None:
    data: dict[str, Any] = {
        "PropertyTable": {
            "Properties": [
                {
                    "MolecularWeight": 46.07,
                    "XLogP": -0.14,
                    "HBondDonorCount": 1,
                }
            ]
        }
    }
    with patch.object(client.client, "get", new_callable=AsyncMock, return_value=_make_response(data)):
        result = await client.get_properties("64-17-5")
    assert result.get("MolecularWeight") == 46.07
    assert result.get("HBondDonorCount") == 1


@pytest.mark.asyncio
async def test_url_encodes_cas_number(client: PubChemClient) -> None:
    data: dict[str, Any] = {"PropertyTable": {"Properties": []}}
    with patch.object(client.client, "get", new_callable=AsyncMock, return_value=_make_response(data)) as mock_get:
        await client.get_smiles("64-17-5")
    call_args = mock_get.await_args
    assert call_args is not None
    assert "64-17-5" in call_args[0][0]
