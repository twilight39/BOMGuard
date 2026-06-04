"""Tests for the BOM file parser."""

import io

import pandas as pd
import pytest

from bomguard.services.bom_parser import parse_bom


def _csv_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.StringIO()
    df.to_csv(buffer, index=False)
    return buffer.getvalue().encode("utf-8")


def _xlsx_bytes(df: pd.DataFrame) -> bytes:
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine="openpyxl")
    buffer.seek(0)
    return buffer.read()


def test_parse_csv_basic() -> None:
    df = pd.DataFrame({
        "Part Number": ["R1", "C1", "U1"],
        "Description": ["10k resistor", "100nF cap", "MCU"],
        "Manufacturer": ["Yageo", "Murata", "ST"],
        "Quantity": [10, 20, 1],
    })
    parts = parse_bom(_csv_bytes(df), "test.csv")
    assert len(parts) == 3
    assert parts[0].part_number == "R1"
    assert parts[0].manufacturer == "Yageo"
    assert parts[0].quantity == 10
    assert parts[2].part_number == "U1"


def test_parse_xlsx_basic() -> None:
    df = pd.DataFrame({
        "PartNumber": ["R1", "C1"],
        "Mfg": ["Yageo", "Murata"],
        "Qty": [5, 10],
    })
    parts = parse_bom(_xlsx_bytes(df), "test.xlsx")
    assert len(parts) == 2
    assert parts[0].part_number == "R1"
    assert parts[0].quantity == 5


def test_parse_fuzzy_headers() -> None:
    df = pd.DataFrame({
        "PN": ["A1", "B2"],
        "CAS Number": ["123-45-6", None],
        "Ref Des": ["R1", "C1"],
    })
    parts = parse_bom(_csv_bytes(df), "fuzzy.csv")
    assert len(parts) == 2
    assert parts[0].part_number == "A1"
    assert parts[0].cas_numbers == "123-45-6"
    assert parts[1].cas_numbers is None


def test_parse_latin1_fallback() -> None:
    df = pd.DataFrame({
        "Part Number": ["Résistor"],
        "Quantity": [1],
    })
    csv = df.to_csv(index=False).encode("latin-1")
    parts = parse_bom(csv, "latin1.csv")
    assert len(parts) == 1
    assert parts[0].part_number == "Résistor"


def test_parse_empty_file() -> None:
    with pytest.raises(ValueError, match="empty"):
        parse_bom(b"", "empty.csv")


def test_parse_no_data_rows() -> None:
    df = pd.DataFrame({"Part Number": []})
    with pytest.raises(ValueError, match="no data"):
        parse_bom(_csv_bytes(df), "nodata.csv")


def test_parse_no_part_number_column() -> None:
    df = pd.DataFrame({
        "Description": ["A", "B"],
        "Qty": [1, 2],
    })
    with pytest.raises(ValueError, match="part number"):
        parse_bom(_csv_bytes(df), "nopn.csv")


def test_parse_too_many_rows() -> None:
    df = pd.DataFrame({
        "Part Number": [f"P{i}" for i in range(10001)],
    })
    with pytest.raises(ValueError, match="maximum"):
        parse_bom(_csv_bytes(df), "huge.csv")


def test_parse_no_valid_parts() -> None:
    df = pd.DataFrame({
        "Part Number": [None, None],
        "Qty": [1, 2],
    })
    with pytest.raises(ValueError, match="No valid parts"):
        parse_bom(_csv_bytes(df), "empty_parts.csv")


def test_parse_skips_empty_part_numbers() -> None:
    df = pd.DataFrame({
        "Part Number": ["R1", "", "R2"],
        "Qty": [1, 2, 3],
    })
    parts = parse_bom(_csv_bytes(df), "skip_empty.csv")
    assert len(parts) == 2
    assert parts[0].part_number == "R1"
    assert parts[1].part_number == "R2"
