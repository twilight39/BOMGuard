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


def seed_sample_boms(db: Session) -> None:
    """Seed sample BOMs from /samples if none exist."""
    existing = db.query(Bom).filter(Bom.source_type == "sample").first()
    if existing:
        return

    for filename, display_name in SAMPLE_BOMS:
        filepath = SAMPLE_DIR / filename
        if not filepath.exists():
            continue

        with open(filepath, "rb") as f:
            contents = f.read()

        try:
            parts = parse_bom(contents, filename)
        except ValueError:
            continue

        bom = Bom(
            name=display_name,
            source_type="sample",
            file_format=filename.rsplit(".", 1)[-1].lower(),
            total_parts=len(parts),
            compliance_status="pending",
            user_id=None,
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
