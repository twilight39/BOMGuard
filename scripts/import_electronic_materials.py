"""Import a curated list of common electronic materials as negative training examples.

Real electronics BOMs are proprietary, but material declarations (IEC 62474,
manufacturer SDS sheets) consistently report the same set of common substances
used in PCBs, passives, semiconductors, batteries, connectors, and housings.
This script imports ~80 of those substances, marks them as ``not_restricted``
for every regulation, and optionally enqueues enrichment so they enter the ML
pipeline.

Usage (inside the api container):
    uv run python ../scripts/import_electronic_materials.py

Usage (from host with local uv env):
    export DATABASE_URL=postgresql://bomguard:bomguard@localhost:5432/bomguard
    uv run python ../scripts/import_electronic_materials.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import TYPE_CHECKING

# Make the backend package importable when running from scripts/
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from bomguard.db import SessionLocal
from bomguard.enrichment.tasks import enrich_substance
from bomguard.models.database import Regulation, Substance, SubstanceRegulationStatus

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


# Curated CAS numbers for substances commonly found in electrical/electronic
# equipment. Sources: IEC 62474 material classes, IPC-1752A FMDs, component
# SDS sheets, and typical PCB/passive/semiconductor/battery compositions.
COMMON_ELECTRONIC_MATERIALS: list[tuple[str, str]] = [
    ("Silicon", "7440-21-3"),
    ("Silicon dioxide", "14808-60-7"),
    ("Aluminum oxide", "1344-28-1"),
    ("Barium titanate", "12047-27-7"),
    ("Tantalum pentoxide", "1314-61-0"),
    ("Ruthenium(IV) oxide", "12036-10-1"),
    ("Tin", "7440-31-5"),
    ("Silver", "7440-22-4"),
    ("Copper", "7440-50-8"),
    ("Gold", "7440-57-5"),
    ("Nickel", "7440-02-0"),
    ("Palladium", "7440-05-3"),
    ("Platinum", "7440-06-4"),
    ("Cobalt", "7440-48-4"),
    ("Aluminum", "7429-90-5"),
    ("Tantalum", "7440-25-7"),
    ("Niobium", "7440-03-1"),
    ("Tungsten", "7440-33-7"),
    ("Molybdenum", "7439-98-7"),
    ("Chromium", "7440-47-3"),
    ("Manganese dioxide", "1313-13-9"),
    ("Graphite", "7782-42-5"),
    ("Lithium cobalt oxide", "12190-79-3"),
    ("Lithium manganese oxide", "12057-17-9"),
    ("Lithium iron phosphate", "15365-14-7"),
    ("Propylene carbonate", "108-32-7"),
    ("1,2-Dimethoxyethane", "110-71-4"),
    ("Bisphenol A diglycidyl ether", "1675-54-3"),
    ("Bisphenol A", "80-05-7"),
    ("Polyimide", "25036-53-7"),
    ("Polycarbonate", "24936-68-3"),
    ("Polypropylene", "9003-07-0"),
    ("Polyethylene", "9002-88-4"),
    ("Acrylonitrile butadiene styrene", "9003-56-9"),
    ("Nylon 6,6", "32131-17-2"),
    ("Polytetrafluoroethylene", "9002-84-0"),
    ("Tetrabromobisphenol A", "79-94-7"),
    ("Antimony trioxide", "1309-64-4"),
    ("Zinc oxide", "1314-13-2"),
    ("Titanium dioxide", "13463-67-7"),
    ("Carbon black", "1333-86-4"),
    ("Iron(III) oxide", "1309-37-1"),
    ("Strontium ferrite", "12023-91-5"),
    ("Gallium arsenide", "1303-00-0"),
    ("Gallium nitride", "25617-97-4"),
    ("Indium phosphide", "22398-80-7"),
    ("Indium tin oxide", "50926-11-9"),
    ("Indium oxide", "1312-43-2"),
    ("Tin(IV) oxide", "2166-19-4"),
    ("Zinc sulfide", "1314-98-3"),
    ("Silicon carbide", "409-21-2"),
    ("Aluminum nitride", "24304-00-5"),
    ("Boron trioxide", "1303-86-2"),
    ("Borosilicate glass", "65997-17-3"),
    ("Phenol formaldehyde resin", "9003-35-4"),
    ("Melamine formaldehyde", "9003-08-1"),
    ("Urea formaldehyde", "9011-05-6"),
    ("Polyurethane", "9009-54-5"),
    ("Silicone rubber", "63394-02-5"),
    ("Ethylene vinyl acetate", "24937-78-8"),
    ("Polyvinyl chloride", "9002-86-2"),
    ("Polystyrene", "9003-53-6"),
    ("Polyethylene terephthalate", "25038-59-9"),
    ("Polymethyl methacrylate", "9011-14-7"),
    ("Rosin", "8050-09-7"),
    ("Stearic acid", "57-11-4"),
    ("Palmitic acid", "57-10-3"),
    ("Oleic acid", "112-80-1"),
    ("Beeswax", "8012-89-3"),
    ("Paraffin wax", "8002-74-2"),
    ("Polyethylene glycol", "25322-68-3"),
    ("Glycerol", "56-81-5"),
    ("Ethylene glycol", "107-21-1"),
    ("Propylene glycol", "57-55-6"),
    ("Isopropanol", "67-63-0"),
    ("Acetone", "67-64-1"),
    ("Ethanol", "64-17-5"),
    ("Toluene", "108-88-3"),
    ("Xylene", "1330-20-7"),
    ("n-Butyl acetate", "123-86-4"),
    ("Methyl ethyl ketone", "78-93-3"),
    ("N-Methyl-2-pyrrolidone", "872-50-4"),
    ("Tetrahydrofuran", "109-99-9"),
    ("Dichloromethane", "75-09-2"),
    ("n-Hexane", "110-54-3"),
    ("Cyclohexane", "110-82-7"),
    ("Benzene", "71-43-2"),
    ("Styrene", "100-42-5"),
    ("Acrylonitrile", "107-13-1"),
    ("Butadiene", "106-99-0"),
    ("Formaldehyde", "50-00-0"),
    ("Phenol", "108-95-2"),
    ("Phthalic anhydride", "85-44-9"),
    ("Adipic acid", "124-04-9"),
    ("Terephthalic acid", "100-21-0"),
    ("Maleic anhydride", "108-31-6"),
    ("Citric acid", "77-92-9"),
    ("Acetic acid", "64-19-7"),
]


def _load_restricted_cas(data_dir: Path) -> set[str]:
    """Load all CAS numbers already listed as restricted in the static JSON files."""
    restricted: set[str] = set()
    for path in data_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            continue
        for entry in data.get("substances", []):
            cas = entry.get("cas_number")
            if cas:
                restricted.add(cas.strip())
    return restricted


def import_electronic_materials(db: Session, enqueue_enrichment: bool = True) -> dict[str, int]:
    """Insert common electronic materials as not_restricted substances."""
    data_dir = Path(__file__).resolve().parent.parent / "backend" / "bomguard" / "data" / "regulations"
    restricted_cas = _load_restricted_cas(data_dir)

    regulations = db.query(Regulation).all()
    if not regulations:
        raise RuntimeError("No regulations found; seed the database first.")

    created_substances = 0
    created_statuses = 0
    skipped_restricted = 0

    for name, cas in COMMON_ELECTRONIC_MATERIALS:
        if cas in restricted_cas:
            skipped_restricted += 1
            continue

        substance = db.query(Substance).filter_by(cas_number=cas).first()
        if not substance:
            substance = Substance(name=name, cas_number=cas)
            db.add(substance)
            db.flush()
            created_substances += 1

        for regulation in regulations:
            status = (
                db.query(SubstanceRegulationStatus)
                .filter_by(substance_id=substance.id, regulation_id=regulation.id)
                .first()
            )
            if not status:
                db.add(
                    SubstanceRegulationStatus(
                        substance_id=substance.id,
                        regulation_id=regulation.id,
                        status="not_restricted",
                    )
                )
                created_statuses += 1

    db.commit()

    if enqueue_enrichment:
        for _, cas in COMMON_ELECTRONIC_MATERIALS:
            if cas in restricted_cas:
                continue
            substance = db.query(Substance).filter_by(cas_number=cas).first()
            if substance:
                enrich_substance.delay(substance.id)

    return {
        "created_substances": created_substances,
        "created_statuses": created_statuses,
        "skipped_restricted": skipped_restricted,
        "total_candidates": len(COMMON_ELECTRONIC_MATERIALS),
    }


if __name__ == "__main__":
    if "DATABASE_URL" not in os.environ:
        print("WARNING: DATABASE_URL not set; using default from bomguard.config")

    db = SessionLocal()
    try:
        stats = import_electronic_materials(db, enqueue_enrichment=True)
        print("Import complete:", stats)
    finally:
        db.close()
