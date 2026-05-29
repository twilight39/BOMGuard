#!/usr/bin/env python3
"""Validate regulation JSON data files.

Run from repo root:
    python scripts/validate_regulation_data.py
"""

import json
import re
import sys
from pathlib import Path

REGULATIONS_DIR = Path("backend/bomguard/data/regulations")
CAS_RE = re.compile(r"^\d{2,7}-\d{2}-\d$")


def validate_cas(cas: str | None) -> list[str]:
    """Return list of validation errors for a CAS number."""
    errors: list[str] = []
    if cas is None:
        return errors
    if not CAS_RE.match(cas):
        errors.append(f"Invalid CAS format: {cas!r}")
    return errors


def validate_file(path: Path) -> list[str]:
    """Validate a single regulation JSON file. Return list of errors."""
    errors: list[str] = []

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        errors.append(f"Invalid JSON: {exc}")
        return errors

    reg_id = data.get("regulation_id")
    if reg_id != path.stem:
        errors.append(
            f"regulation_id mismatch: file={path.stem}, json={reg_id}"
        )

    substances = data.get("substances", [])
    if not substances:
        errors.append("No substances found")

    seen_cas: set[str] = set()
    for idx, item in enumerate(substances, start=1):
        name = item.get("name", f"<item {idx}>")
        if not item.get("name"):
            errors.append(f"Item {idx}: missing 'name'")
        if not item.get("cas_number"):
            errors.append(f"{name}: missing 'cas_number'")
        else:
            cas = item["cas_number"]
            errors.extend(f"{name}: {e}" for e in validate_cas(cas))
            if cas in seen_cas:
                errors.append(f"{name}: duplicate CAS {cas}")
            seen_cas.add(cas)

    return errors


def main() -> int:
    if not REGULATIONS_DIR.exists():
        print(f"ERROR: Directory not found: {REGULATIONS_DIR}", file=sys.stderr)
        return 1

    json_files = sorted(REGULATIONS_DIR.glob("*.json"))
    if not json_files:
        print(f"ERROR: No JSON files found in {REGULATIONS_DIR}", file=sys.stderr)
        return 1

    total_errors = 0
    for path in json_files:
        errors = validate_file(path)
        if errors:
            print(f"\n{path.name}: {len(errors)} error(s)")
            for err in errors:
                print(f"  - {err}")
            total_errors += len(errors)
        else:
            print(f"{path.name}: OK")

    print(f"\n{'=' * 40}")
    print(f"Files checked: {len(json_files)}")
    print(f"Total errors: {total_errors}")
    return 1 if total_errors > 0 else 0


if __name__ == "__main__":
    sys.exit(main())
