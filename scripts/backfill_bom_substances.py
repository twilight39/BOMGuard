"""Backfill Substance rows from CAS numbers in existing BOMs.

Run this once to create substances for any CAS numbers referenced by already-
uploaded BOMs. New substances are marked not_restricted for all regulations so
they enter the ML training set.

Usage:
    cd backend && uv run python ../scripts/backfill_bom_substances.py
"""

from bomguard.db import SessionLocal
from bomguard.models.database import BomPart
from bomguard.services.bom_substances import sync_bom_substances


def main() -> None:
    db = SessionLocal()
    try:
        parts = db.query(BomPart).all()
        created = sync_bom_substances(db, parts)
        print(f"Created {len(created)} substances from existing BOM CAS numbers")
    finally:
        db.close()


if __name__ == "__main__":
    main()
