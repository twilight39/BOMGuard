"""Seed script for initial database data."""

import os
from pathlib import Path

from sqlalchemy.orm import Session

from bomguard.models.database import Bom, BomPart, Regulation
from bomguard.services.bom_parser import parse_bom

REGULATIONS = [
    {
        "id": "eu_reach_svhc",
        "name": "EU REACH SVHC Candidate List",
        "authority": "ECHA",
        "scope": "Substances of Very High Concern in the EU",
        "ml_enabled": True,
    },
    {
        "id": "us_state_pfas",
        "name": "US State PFAS Restrictions",
        "authority": "Multi-state",
        "scope": "Per- and polyfluoroalkyl substances restrictions across US states",
        "ml_enabled": True,
    },
    {
        "id": "eu_rohs",
        "name": "EU RoHS Directive 2011/65/EU",
        "authority": "European Commission",
        "scope": "Restriction of Hazardous Substances in electrical and electronic equipment",
        "ml_enabled": False,
    },
    {
        "id": "us_tsca_6h",
        "name": "US TSCA Section 6(h) PBT",
        "authority": "US EPA",
        "scope": "Persistent Bioaccumulative and Toxic chemicals under TSCA",
        "ml_enabled": False,
    },
    {
        "id": "cn_rohs",
        "name": "China RoHS 2 (SJ/T 11363)",
        "authority": "MIIT China",
        "scope": "Restriction of Hazardous Substances in China",
        "ml_enabled": False,
    },
]


def seed_regulations(db: Session) -> None:
    """Seed regulation definitions if they don't exist."""
    for reg_data in REGULATIONS:
        existing = db.query(Regulation).filter_by(id=reg_data["id"]).first()
        if not existing:
            db.add(Regulation(**reg_data))
    db.commit()


def _find_samples_dir() -> Path:
    """Find the samples directory in local dev or Docker."""
    # Try relative to this file first (local dev: backend/../samples)
    candidates = [
        Path(__file__).parent.parent.parent / "samples",
        Path(__file__).parent.parent / "samples",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return candidates[0]  # fallback


SAMPLE_DIR = _find_samples_dir()

SAMPLE_BOMS = [
    ("iot_sensor_bom.csv", "IoT Sensor BOM"),
    ("power_supply_bom.csv", "Power Supply BOM"),
    ("smartphone_pcb_bom.csv", "Smartphone PCB BOM"),
]


SAMPLE_MAP: dict[str, tuple[str, str]] = {
    "iot_sensor": ("iot_sensor_bom.csv", "IoT Sensor BOM"),
    "power_supply": ("power_supply_bom.csv", "Power Supply BOM"),
    "smartphone_pcb": ("smartphone_pcb_bom.csv", "Smartphone PCB BOM"),
}


def load_sample_bom(db: Session, sample_id: str, user_id: str | None = None) -> Bom:
    """Load a single sample BOM file into the database.

    Args:
        db: Database session.
        sample_id: Key from SAMPLE_MAP (e.g. "iot_sensor").
        user_id: Optional user ID to assign ownership.

    Returns:
        The created Bom instance.

    Raises:
        ValueError: If sample_id is unknown or file cannot be parsed.
    """
    if sample_id not in SAMPLE_MAP:
        raise ValueError(f"Unknown sample: {sample_id}")

    filename, display_name = SAMPLE_MAP[sample_id]
    filepath = SAMPLE_DIR / filename
    if not filepath.exists():
        raise ValueError(f"Sample file not found: {filepath}")

    with open(filepath, "rb") as f:
        contents = f.read()

    parts = parse_bom(contents, filename)

    bom = Bom(
        name=display_name,
        source_type="sample",
        file_format=filename.rsplit(".", 1)[-1].lower(),
        total_parts=len(parts),
        compliance_status="pending",
        user_id=user_id,
    )
    db.add(bom)
    db.flush()

    for parsed in parts:
        bom_part = BomPart(
            bom_id=bom.id,
            line_number=parsed.line_number,
            part_number=parsed.part_number,
            description=parsed.description,
            manufacturer=parsed.manufacturer,
            supplier=parsed.supplier,
            quantity=parsed.quantity,
            unit=parsed.unit or "pcs",
            cas_numbers=parsed.cas_numbers,
        )
        db.add(bom_part)

    db.commit()
    return bom


def seed_sample_boms(db: Session) -> None:
    """Seed sample BOMs from /samples if none exist."""
    existing = db.query(Bom).filter(Bom.source_type == "sample").first()
    if existing:
        return

    for sample_id, _ in SAMPLE_MAP.items():
        try:
            load_sample_bom(db, sample_id, user_id=None)
        except ValueError:
            continue
