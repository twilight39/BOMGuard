"""Backfill not_restricted labels for existing substances.

Run this once after deploying the negative-label change to an existing
 database so ML-enabled regulations have both classes available for training.

Usage:
    cd backend && uv run python ../scripts/backfill_negative_labels.py
"""

from bomguard.db import SessionLocal
from bomguard.ingestion.pipeline import ensure_negative_labels
from bomguard.ingestion.registry import get_all_scrapers


def main() -> None:
    db = SessionLocal()
    try:
        total = 0
        for scraper in get_all_scrapers():
            created = ensure_negative_labels(db, scraper.regulation_id)
            total += created
            print(f"{scraper.regulation_id}: created {created} not_restricted statuses")
        print(f"Total not_restricted statuses created: {total}")
    finally:
        db.close()


if __name__ == "__main__":
    main()
