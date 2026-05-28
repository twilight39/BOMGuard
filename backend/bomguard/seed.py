"""Seed script for initial database data."""

from sqlalchemy.orm import Session

from bomguard.models.database import Regulation

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
