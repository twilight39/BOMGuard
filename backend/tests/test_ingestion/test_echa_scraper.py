"""Tests for the ECHA CHEM API scraper."""

from unittest.mock import MagicMock, patch

import pytest

from bomguard.services.echa_scraper import ECHAChemScraper


@pytest.fixture
def scraper() -> ECHAChemScraper:
    return ECHAChemScraper()


def _make_response(json_data: dict) -> MagicMock:
    resp = MagicMock()
    resp.json.return_value = json_data
    resp.raise_for_status.return_value = None
    return resp


def test_fetch_all_paginates(scraper: ECHAChemScraper) -> None:
    page1 = {
        "items": [
            {
                "substanceName": ["Lead"],
                "ecNumber": ["231-100-4"],
                "casNumber": ["7439-92-1"],
                "reasonForInclusion": ["Toxic for reproduction"],
                "dateOfInclusion": "04-Feb-2026",
            }
        ],
        "state": {
            "pageIndex": 1,
            "pageSize": 100,
            "totalItems": 2,
            "totalPages": 2,
        },
    }
    page2 = {
        "items": [
            {
                "substanceName": ["Cadmium"],
                "ecNumber": ["231-152-8"],
                "casNumber": ["7440-43-9"],
                "reasonForInclusion": ["Carcinogenic"],
                "dateOfInclusion": "15-Jan-2026",
            }
        ],
        "state": {
            "pageIndex": 2,
            "pageSize": 100,
            "totalItems": 2,
            "totalPages": 2,
        },
    }

    with patch.object(
        scraper.client, "get", side_effect=[_make_response(page1), _make_response(page2)]
    ) as mock_get:
        results = scraper.fetch_all()

    assert mock_get.call_count == 2
    assert len(results) == 2

    assert results[0].name == "Lead"
    assert results[0].cas_number == "7439-92-1"
    assert results[0].ec_number == "231-100-4"
    assert results[0].reason_for_inclusion == "Toxic for reproduction"
    assert results[0].date_added == "04-Feb-2026"

    assert results[1].name == "Cadmium"
    assert results[1].cas_number == "7440-43-9"


def test_parse_item_normalizes_dash(scraper: ECHAChemScraper) -> None:
    item = {
        "substanceName": ["Some Chemical"],
        "ecNumber": ["-"],
        "casNumber": ["-"],
        "reasonForInclusion": ["Test reason"],
        "dateOfInclusion": "01-Jan-2025",
    }

    raw = scraper._parse_item(item)  # noqa: SLF001

    assert raw.name == "Some Chemical"
    assert raw.cas_number is None
    assert raw.ec_number is None
    assert raw.reason_for_inclusion == "Test reason"


def test_parse_item_empty_arrays(scraper: ECHAChemScraper) -> None:
    item: dict[str, list[str] | None] = {
        "substanceName": [],
        "ecNumber": [],
        "casNumber": [],
        "reasonForInclusion": [],
        "dateOfInclusion": None,
    }

    raw = scraper._parse_item(item)  # noqa: SLF001

    assert raw.name == ""
    assert raw.cas_number is None
    assert raw.ec_number is None
    assert raw.reason_for_inclusion is None
    assert raw.date_added is None
