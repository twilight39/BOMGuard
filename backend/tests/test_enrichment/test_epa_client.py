"""Tests for the EPA CompTox client."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from bomguard.services.epa_client import EPACompToxClient, EPACompToxError


@pytest.fixture
def client() -> EPACompToxClient:
    return EPACompToxClient(api_key="test-key")


@pytest.mark.asyncio
async def test_search_by_cas_success(client: EPACompToxClient) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "dtxsid": "DTXSID9020584",
            "casrn": "64-17-5",
            "preferredName": "Ethanol",
            "smiles": "CCO",
        }
    ]

    with patch.object(
        client.client, "get", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await client.search_by_cas("64-17-5")

    assert result is not None
    assert result["dtxsid"] == "DTXSID9020584"
    assert result["casrn"] == "64-17-5"
    assert result["smiles"] == "CCO"


@pytest.mark.asyncio
async def test_search_by_cas_not_found_returns_none(
    client: EPACompToxClient,
) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        "Not found", request=MagicMock(), response=mock_response
    )

    with patch.object(
        client.client, "get", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await client.search_by_cas("999-99-9")

    assert result is None


@pytest.mark.asyncio
async def test_get_chemical_detail_success(client: EPACompToxClient) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "dtxsid": "DTXSID9020584",
        "bioconcentrationFactorOperaPred": 3.12,
        "biodegradationHalfLifeDays": 15.0,
        "hrFatheadMinnow": 2.5,
    }

    with patch.object(
        client.client, "get", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await client.get_chemical_detail("DTXSID9020584")

    assert result["bioconcentrationFactorOperaPred"] == pytest.approx(3.12)
    assert result["biodegradationHalfLifeDays"] == pytest.approx(15.0)


@pytest.mark.asyncio
async def test_get_fate_data_success(client: EPACompToxClient) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "propName": "Bioconcentration Factor",
            "predictedFateData": [
                {"prop_value": 3.14, "model_name": "OPERA_BCF"}
            ],
        }
    ]

    with patch.object(
        client.client, "get", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await client.get_fate_data("DTXSID9020584")

    assert len(result) == 1
    assert result[0]["propName"] == "Bioconcentration Factor"


@pytest.mark.asyncio
async def test_get_cancer_summary_success(client: EPACompToxClient) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = [
        {
            "dtxsid": "DTXSID9020584",
            "source": "IARC",
            "cancerCall": "Group 1 - Carcinogenic to humans",
        }
    ]

    with patch.object(
        client.client, "get", new_callable=AsyncMock, return_value=mock_response
    ):
        result = await client.get_cancer_summary("DTXSID9020584")

    assert len(result) == 1
    assert result[0]["source"] == "IARC"


@pytest.mark.asyncio
async def test_get_properties_integration(client: EPACompToxClient) -> None:
    """Test the high-level get_properties orchestration."""

    async def mock_search(cas: str) -> dict[str, Any] | None:
        _ = cas
        return {
            "dtxsid": "DTXSID9020584",
            "casrn": "64-17-5",
            "smiles": "CCO",
        }

    async def mock_detail(dtxsid: str) -> dict[str, Any]:
        _ = dtxsid
        return {
            "bioconcentrationFactorOperaPred": 3.12,
            "biodegradationHalfLifeDays": 15.0,
            "hrFatheadMinnow": 2.5,
        }

    async def mock_fate(dtxsid: str) -> list[dict[str, Any]]:
        _ = dtxsid
        return []

    async def mock_cancer(dtxsid: str) -> list[dict[str, Any]]:
        _ = dtxsid
        return [{"source": "IARC"}]

    with (
        patch.object(client, "search_by_cas", side_effect=mock_search),
        patch.object(client, "get_chemical_detail", side_effect=mock_detail),
        patch.object(client, "get_fate_data", side_effect=mock_fate),
        patch.object(client, "get_cancer_summary", side_effect=mock_cancer),
    ):
        result = await client.get_properties("64-17-5")

    assert result["has_epa_data"] is True
    assert result["bcf"] == pytest.approx(3.12)
    assert result["half_life_soil"] == pytest.approx(15.0)
    assert result["lc50_fish"] == pytest.approx(2.5)
    assert result["carcinogenicity_flag"] is True


@pytest.mark.asyncio
async def test_get_properties_no_match_returns_has_epa_data_false(
    client: EPACompToxClient,
) -> None:
    with patch.object(client, "search_by_cas", new_callable=AsyncMock, return_value=None):
        result = await client.get_properties("999-99-9")

    assert result["has_epa_data"] is False


@pytest.mark.asyncio
async def test_get_properties_no_values_returns_has_epa_data_false(
    client: EPACompToxClient,
) -> None:
    async def mock_search(cas: str) -> dict[str, Any] | None:
        _ = cas
        return {"dtxsid": "DTXSID9020584"}

    async def mock_detail(dtxsid: str) -> dict[str, Any]:
        _ = dtxsid
        return {}

    async def mock_fate(dtxsid: str) -> list[dict[str, Any]]:
        _ = dtxsid
        return []

    async def mock_cancer(dtxsid: str) -> list[dict[str, Any]]:
        _ = dtxsid
        return []

    with (
        patch.object(client, "search_by_cas", side_effect=mock_search),
        patch.object(client, "get_chemical_detail", side_effect=mock_detail),
        patch.object(client, "get_fate_data", side_effect=mock_fate),
        patch.object(client, "get_cancer_summary", side_effect=mock_cancer),
    ):
        result = await client.get_properties("64-17-5")

    assert result["has_epa_data"] is False
