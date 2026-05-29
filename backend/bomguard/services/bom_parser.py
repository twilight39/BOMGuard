"""BOM file parser supporting CSV and Excel formats."""

import logging
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)

MAX_ROWS = 10_000

# Fuzzy header mappings: canonical -> list of possible headers
COLUMN_ALIASES: dict[str, list[str]] = {
    "part_number": [
        "part number",
        "partnumber",
        "pn",
        "part no",
        "part no.",
        "item number",
        "item no",
        "item",
        "reference",
        "ref des",
        "refdes",
        "designator",
    ],
    "manufacturer": [
        "manufacturer",
        "mfg",
        "mfr",
        "maker",
        "brand",
        "manufacturer name",
    ],
    "description": [
        "description",
        "desc",
        "part description",
        "value",
        "component",
    ],
    "cas_numbers": [
        "cas",
        "cas number",
        "cas no",
        "cas no.",
        "cas #",
        "cas_numbers",
        "cas number(s)",
    ],
    "quantity": [
        "quantity",
        "qty",
        "qnty",
        "count",
        "amount",
    ],
    "unit": [
        "unit",
        "units",
        "uom",
        "unit of measure",
    ],
    "supplier": [
        "supplier",
        "vendor",
        "distributor",
        "source",
    ],
}


@dataclass
class ParsedPart:
    """A single BOM part parsed from a row."""

    line_number: int | None = None
    part_number: str = ""
    description: str | None = None
    manufacturer: str | None = None
    supplier: str | None = None
    quantity: int = 1
    unit: str = "pcs"
    cas_numbers: str | None = None


def _normalize_header(header: str) -> str:
    """Normalize a header string for fuzzy matching."""
    return header.strip().lower().replace("_", " ").replace("-", " ")


def _detect_columns(headers: list[str]) -> dict[str, str]:
    """Map canonical column names to actual DataFrame column names."""
    normalized = {h: _normalize_header(h) for h in headers}
    mapping: dict[str, str] = {}
    used = set()

    for canonical, aliases in COLUMN_ALIASES.items():
        for header, norm in normalized.items():
            if header in used:
                continue
            if norm in aliases:
                mapping[canonical] = header
                used.add(header)
                break

    return mapping


def _read_file(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """Read CSV or Excel into a DataFrame."""
    ext = Path(filename).suffix.lower()
    buffer = BytesIO(file_bytes)

    if ext == ".csv":
        # Try UTF-8 first, then latin-1 fallback
        try:
            return pd.read_csv(buffer, encoding="utf-8")
        except UnicodeDecodeError:
            buffer.seek(0)
            return pd.read_csv(buffer, encoding="latin-1")

    if ext in (".xlsx", ".xls"):
        return pd.read_excel(buffer)

    raise ValueError(f"Unsupported file format: {ext}")


def _to_int(value: Any) -> int:
    """Safely convert a value to int."""
    if pd.isna(value):
        return 1
    try:
        return int(float(value))
    except (ValueError, TypeError):
        return 1


def _to_str(value: Any) -> str | None:
    """Safely convert a value to stripped string or None."""
    if pd.isna(value):
        return None
    s = str(value).strip()
    return s if s else None


def parse_bom(file_bytes: bytes, filename: str) -> list[ParsedPart]:
    """Parse a BOM file and return a list of parts.

    Args:
        file_bytes: Raw file contents.
        filename: Original filename for format detection.

    Returns:
        List of parsed parts.

    Raises:
        ValueError: If file is empty, too large, or has no recognizable columns.
    """
    if not file_bytes:
        raise ValueError("File is empty.")

    df = _read_file(file_bytes, filename)

    if df.empty:
        raise ValueError("File contains no data rows.")

    if len(df) > MAX_ROWS:
        raise ValueError(f"File exceeds maximum of {MAX_ROWS} rows.")

    mapping = _detect_columns(list(df.columns))

    if "part_number" not in mapping:
        raise ValueError(
            "Could not detect a part number column. "
            f"Recognized columns: {list(mapping.keys())}"
        )

    parts: list[ParsedPart] = []
    for idx, row in df.iterrows():
        line_number = idx + 1  # type: ignore[operator]
        part_number = _to_str(row[mapping["part_number"]])
        if not part_number:
            continue

        parts.append(
            ParsedPart(
                line_number=line_number,
                part_number=part_number,
                description=_to_str(row.get(mapping.get("description"))),
                manufacturer=_to_str(row.get(mapping.get("manufacturer"))),
                supplier=_to_str(row.get(mapping.get("supplier"))),
                quantity=_to_int(row.get(mapping.get("quantity"))),
                unit=_to_str(row.get(mapping.get("unit"))) or "pcs",
                cas_numbers=_to_str(row.get(mapping.get("cas_numbers"))),
            )
        )

    if not parts:
        raise ValueError("No valid parts found in file.")

    logger.info("Parsed %d parts from %s (columns: %s)", len(parts), filename, list(mapping.keys()))
    return parts
