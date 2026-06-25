"""Helpers for syncing BOM CAS numbers into the substance registry."""

from sqlalchemy.orm import Session

from bomguard.ingestion.pipeline import ensure_negative_labels
from bomguard.models.database import Regulation, Substance
from bomguard.services.bom_parser import ParsedPart


def _extract_cas_numbers(parts: list[ParsedPart]) -> set[str]:
    """Return the set of valid CAS numbers referenced by BOM parts."""
    cas_numbers: set[str] = set()
    for part in parts:
        if not part.cas_numbers:
            continue
        for cas in part.cas_numbers.split("|"):
            cas = cas.strip()
            if cas:
                cas_numbers.add(cas)
    return cas_numbers


def sync_bom_substances(
    db: Session,
    parts: list[ParsedPart],
) -> list[Substance]:
    """Ensure every CAS referenced by a BOM exists as a Substance.

    New substances are created with the CAS number as a temporary name.
    PubChem/enrichment will fill in the proper name and properties later.
    After creation, each new substance is marked ``not_restricted`` for every
    regulation so the ML training set covers the full BOM-relevant chemical
    space.

    Returns the list of newly created Substance rows.
    """
    cas_numbers = _extract_cas_numbers(parts)
    if not cas_numbers:
        return []

    existing = {
        cas for (cas,) in db.query(Substance.cas_number).filter(Substance.cas_number.in_(cas_numbers)).all() if cas
    }
    missing = cas_numbers - existing

    created: list[Substance] = []
    for cas in missing:
        substance = Substance(
            name=cas,  # temporary; enrichment will update via PubChem
            cas_number=cas,
        )
        db.add(substance)
        created.append(substance)

    if created:
        db.flush()
        db.commit()

        # Ensure new substances have a not_restricted status for every regulation
        # so they become negative examples for ML training.
        for regulation in db.query(Regulation).all():
            ensure_negative_labels(db, regulation.id)

    return created
