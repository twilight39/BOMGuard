"""Tests for the enrichment pipeline."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.orm import Session

from bomguard.enrichment.pipeline import EnrichmentPipeline
from bomguard.models.database import Substance, SubstanceProperties


@pytest.fixture
def mock_pubchem() -> MagicMock:
    client = MagicMock()
    client.get_smiles = AsyncMock(return_value="CCO")
    client.get_properties = AsyncMock(
        return_value={
            "MolecularWeight": 46.07,
            "XLogP": -0.14,
            "HBondDonorCount": 1,
            "HBondAcceptorCount": 1,
            "TPSA": 20.23,
            "RotatableBondCount": 0,
        }
    )
    return client


def test_enrich_substance_creates_properties(
    db: Session, seed_regulation: Any, mock_pubchem: MagicMock
) -> None:
    _ = seed_regulation
    sub = Substance(name="Ethanol", cas_number="64-17-5")
    db.add(sub)
    db.commit()

    pipeline = EnrichmentPipeline(db, pubchem=mock_pubchem)
    import asyncio

    props = asyncio.run(pipeline.enrich_substance(sub))

    assert props.substance_id == sub.id
    assert props.has_smiles is True
    assert sub.smiles == "CCO"
    assert props.molecular_weight == pytest.approx(46.07, abs=0.01)
    assert props.hbd == 1
    assert props.hba == 1

    # Verify stored in DB
    fetched = db.query(SubstanceProperties).filter_by(substance_id=sub.id).first()
    assert fetched is not None
    assert fetched.has_smiles is True


def test_enrich_substance_idempotent(
    db: Session, seed_regulation: Any, mock_pubchem: MagicMock
) -> None:
    _ = seed_regulation
    sub = Substance(name="Ethanol", cas_number="64-17-5")
    db.add(sub)
    db.commit()

    pipeline = EnrichmentPipeline(db, pubchem=mock_pubchem)
    import asyncio

    _ = asyncio.run(pipeline.enrich_substance(sub))
    _ = asyncio.run(pipeline.enrich_substance(sub))

    # Should still be exactly one properties row
    count = db.query(SubstanceProperties).filter_by(substance_id=sub.id).count()
    assert count == 1


def test_enrich_all_missing_counts(db: Session, mock_pubchem: MagicMock) -> None:
    # Seed two substances
    s1 = Substance(name="Ethanol", cas_number="64-17-5")
    s2 = Substance(name="Water", cas_number="7732-18-5")
    db.add_all([s1, s2])
    db.commit()

    pipeline = EnrichmentPipeline(db, pubchem=mock_pubchem)
    import asyncio

    result = asyncio.run(pipeline.enrich_all_missing(batch_size=10))

    assert result["processed"] == 2
    assert result["enriched"] == 2
    assert result["failed"] == 0
    assert result["total_substances"] == 2
    assert result["with_smiles"] == 2
    assert result["coverage_pct"] == 100.0


def test_enrich_all_missing_skips_already_enriched(
    db: Session, mock_pubchem: MagicMock
) -> None:
    s1 = Substance(name="Ethanol", cas_number="64-17-5")
    db.add(s1)
    db.commit()

    # First enrichment
    pipeline = EnrichmentPipeline(db, pubchem=mock_pubchem)
    import asyncio

    _ = asyncio.run(pipeline.enrich_all_missing(batch_size=10))

    # Second enrichment — should find nothing to process
    result = asyncio.run(pipeline.enrich_all_missing(batch_size=10))
    assert result["processed"] == 0
    assert result["enriched"] == 0


def test_enrich_substance_pubchem_404(
    db: Session, seed_regulation: Any
) -> None:
    _ = seed_regulation
    sub = Substance(name="Unknown", cas_number="999-99-9")
    db.add(sub)
    db.commit()

    mock_client = MagicMock()
    mock_client.get_smiles = AsyncMock(return_value=None)
    mock_client.get_properties = AsyncMock(return_value={})

    pipeline = EnrichmentPipeline(db, pubchem=mock_client)
    import asyncio

    props = asyncio.run(pipeline.enrich_substance(sub))

    assert props.has_smiles is False
    assert sub.smiles is None
