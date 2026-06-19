"""Generic ingestion pipeline used by all regulation scrapers."""

import hashlib
import json
from datetime import date, datetime
from typing import Any

from sqlalchemy.orm import Session

from bomguard.ingestion.base import IngestionResult, RawSubstance, RegulationScraper
from bomguard.models.database import RegulatoryChange, Substance, SubstanceRegulationStatus
from bomguard.websocket import ws_manager


def _get_change_hash(raw_data: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(raw_data, sort_keys=True).encode()).hexdigest()


def _parse_date(date_str: str | None) -> date | None:
    if not date_str:
        return None
    for fmt in ("%d-%b-%Y", "%Y-%m-%d"):
        try:
            return datetime.strptime(date_str, fmt).date()
        except ValueError:
            continue
    return None


def _find_or_create_substance(db: Session, raw: RawSubstance) -> tuple[Substance, bool]:
    """Find existing substance by CAS or EC, or create a new one.

    Returns (substance, is_new).
    """
    substance: Substance | None = None

    if raw.cas_number:
        substance = db.query(Substance).filter_by(cas_number=raw.cas_number).first()

    if not substance and raw.ec_number:
        substance = db.query(Substance).filter_by(ec_number=raw.ec_number).first()

    if not substance:
        substance = Substance(
            name=raw.name,
            cas_number=raw.cas_number,
            ec_number=raw.ec_number,
        )
        db.add(substance)
        db.flush()
        return substance, True

    # Update name if it changed
    if substance.name != raw.name:
        substance.name = raw.name

    return substance, False


def run_scraper(scraper: RegulationScraper, db: Session) -> IngestionResult:
    """Run a scraper through the generic ingestion pipeline.

    Steps:
    1. Fetch all substances from source
    2. Find/create substance records
    3. Detect changes via SHA-256 hash comparison
    4. Upsert regulation status
    5. Commit and return stats
    """
    result = IngestionResult(
        regulation_id=scraper.regulation_id,
        source_name=scraper.source_name,
    )

    raw_substances = scraper.fetch_all()
    result.total_fetched = len(raw_substances)

    for raw in raw_substances:
        substance, is_new = _find_or_create_substance(db, raw)

        if is_new:
            result.substances_created += 1
            result.new_substance_ids.append(substance.id)
        else:
            result.substances_updated += 1

        # Build hashable representation of raw data
        raw_data: dict[str, Any] = {
            "name": raw.name,
            "cas_number": raw.cas_number,
            "ec_number": raw.ec_number,
            "reason_for_inclusion": raw.reason_for_inclusion,
            "date_added": raw.date_added,
        }
        new_hash = _get_change_hash(raw_data)

        # Detect changes
        if is_new:
            result.changes_detected += 1
            db.add(
                RegulatoryChange(
                    substance_id=substance.id,
                    regulation_id=scraper.regulation_id,
                    change_type="added",
                    new_hash=new_hash,
                )
            )
        elif substance.change_hash and substance.change_hash != new_hash:
            result.changes_detected += 1
            db.add(
                RegulatoryChange(
                    substance_id=substance.id,
                    regulation_id=scraper.regulation_id,
                    change_type="amended",
                    old_hash=substance.change_hash,
                    new_hash=new_hash,
                )
            )

        substance.change_hash = new_hash

        # Upsert regulation status
        status = (
            db.query(SubstanceRegulationStatus)
            .filter_by(
                substance_id=substance.id,
                regulation_id=scraper.regulation_id,
            )
            .first()
        )

        if status:
            if status.status != "restricted":
                status.status = "restricted"
                # SQLAlchemy Mapped fields need explicit cast for strict type checkers
                status.effective_date = _parse_date(raw.date_added)  # type: ignore[assignment]
                result.statuses_updated += 1
        else:
            db.add(
                SubstanceRegulationStatus(
                    substance_id=substance.id,
                    regulation_id=scraper.regulation_id,
                    status="restricted",
                    effective_date=_parse_date(raw.date_added),
                )
            )
            result.statuses_created += 1

    db.commit()

    if result.changes_detected > 0:
        ws_manager.broadcast_sync({
            "type": "regulatory_change",
            "regulation_id": scraper.regulation_id,
            "changes_detected": result.changes_detected,
            "substances_created": result.substances_created,
            "substances_updated": result.substances_updated,
        })

    return result
