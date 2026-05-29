"""Tests for the StaticListScraper base class."""

import json
from pathlib import Path
from unittest.mock import patch

import pytest

from bomguard.ingestion.base import RawSubstance
from bomguard.ingestion.static_scraper import StaticListScraper


class DummyScraper(StaticListScraper):
    """Test scraper with a known regulation ID."""

    regulation_id = "test_dummy"
    source_name = "test_source"


def test_fetch_all_loads_substances(tmp_path: Path) -> None:
    data = {
        "regulation_id": "test_dummy",
        "source_name": "test_source",
        "substances": [
            {
                "name": "Test Substance",
                "cas_number": "123-45-6",
                "ec_number": "231-100-4",
                "reason_for_inclusion": "Test reason",
                "date_added": "2024-01-01",
            }
        ],
    }
    with patch.object(
        StaticListScraper, "__init__", lambda _: None
    ), patch(
        "bomguard.ingestion.static_scraper.REGULATIONS_DIR", tmp_path
    ):
        path = tmp_path / "test_dummy.json"
        path.write_text(json.dumps(data))

        scraper = DummyScraper.__new__(DummyScraper)
        results = scraper.fetch_all()

    assert len(results) == 1
    assert isinstance(results[0], RawSubstance)
    assert results[0].name == "Test Substance"
    assert results[0].cas_number == "123-45-6"
    assert results[0].ec_number == "231-100-4"
    assert results[0].reason_for_inclusion == "Test reason"
    assert results[0].date_added == "2024-01-01"


def test_fetch_all_missing_file_raises() -> None:
    scraper = DummyScraper.__new__(DummyScraper)
    with pytest.raises(FileNotFoundError) as exc_info:
        scraper.fetch_all()
    assert "test_dummy.json" in str(exc_info.value)


def test_fetch_all_empty_regulation_id_raises() -> None:
    class BadScraper(StaticListScraper):
        regulation_id = ""
        source_name = "bad"

    scraper = BadScraper.__new__(BadScraper)
    with pytest.raises(RuntimeError) as exc_info:
        scraper.fetch_all()
    assert "regulation_id must be set" in str(exc_info.value)


def test_fetch_all_skips_optional_fields(tmp_path: Path) -> None:
    data = {
        "regulation_id": "test_dummy",
        "substances": [
            {"name": "Minimal Substance", "cas_number": "123-45-6"}
        ],
    }
    with patch.object(
        StaticListScraper, "__init__", lambda _: None
    ), patch(
        "bomguard.ingestion.static_scraper.REGULATIONS_DIR", tmp_path
    ):
        path = tmp_path / "test_dummy.json"
        path.write_text(json.dumps(data))

        scraper = DummyScraper.__new__(DummyScraper)
        results = scraper.fetch_all()

    assert len(results) == 1
    assert results[0].name == "Minimal Substance"
    assert results[0].cas_number == "123-45-6"
    assert results[0].ec_number is None
    assert results[0].reason_for_inclusion is None
    assert results[0].date_added is None
