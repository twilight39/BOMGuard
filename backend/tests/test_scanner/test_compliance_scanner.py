"""Tests for the compliance scanner service."""

from datetime import date

import pytest
from sqlalchemy.orm import Session

from bomguard.models.database import (
    Bom,
    BomPart,
    Regulation,
    ScanResult,
    Substance,
    SubstanceRegulationStatus,
)
from bomguard.services.compliance_scanner import ComplianceScanner


@pytest.fixture
def regulations(db: Session) -> list[Regulation]:
    """Seed test regulations."""
    regs = [
        Regulation(id="eu_reach_svhc", name="EU REACH SVHC", ml_enabled=True),
        Regulation(id="eu_rohs", name="EU RoHS", ml_enabled=False),
    ]
    for r in regs:
        db.add(r)
    db.commit()
    return regs


@pytest.fixture
def substances(db: Session) -> list[Substance]:
    """Seed test substances with CAS numbers."""
    subs = [
        Substance(id=1, name="Lead", cas_number="7439-92-1"),
        Substance(id=2, name="Cadmium", cas_number="7440-43-9"),
        Substance(id=3, name="Water", cas_number="7732-18-5"),
    ]
    for s in subs:
        db.add(s)
    db.commit()
    return subs


@pytest.fixture
def restrictions(db: Session, substances: list[Substance], regulations: list[Regulation]) -> None:
    """Seed test restriction statuses."""
    statuses = [
        SubstanceRegulationStatus(
            substance_id=substances[0].id,
            regulation_id="eu_rohs",
            status="restricted",
            effective_date=date(2006, 7, 1),
        ),
        SubstanceRegulationStatus(
            substance_id=substances[1].id,
            regulation_id="eu_reach_svhc",
            status="restricted",
            effective_date=date(2013, 12, 16),
        ),
        SubstanceRegulationStatus(
            substance_id=substances[2].id,
            regulation_id="eu_rohs",
            status="not_restricted",
        ),
    ]
    for s in statuses:
        db.add(s)
    db.commit()


class TestComplianceScanner:
    def test_scan_finds_restricted_cas(self, db: Session, restrictions: None) -> None:
        """Scanner should flag parts with restricted CAS numbers."""
        bom = Bom(name="Test BOM", source_type="upload", total_parts=1)
        db.add(bom)
        db.commit()

        part = BomPart(
            bom_id=bom.id,
            line_number=1,
            part_number="CAP-001",
            cas_numbers="7439-92-1",
        )
        db.add(part)
        db.commit()

        scanner = ComplianceScanner(db)
        hits = scanner.scan_bom(bom.id)

        assert len(hits) == 1
        assert hits[0].cas_number == "7439-92-1"
        assert hits[0].regulation_id == "eu_rohs"
        assert hits[0].hit_type == "direct_match"
        assert hits[0].severity == "critical"
        assert bom.compliance_status == "flagged"

    def test_scan_multiple_cas_in_one_part(self, db: Session, restrictions: None) -> None:
        """Scanner should check all CAS numbers in a pipe-separated list."""
        bom = Bom(name="Multi-CAS BOM", source_type="upload", total_parts=1)
        db.add(bom)
        db.commit()

        part = BomPart(
            bom_id=bom.id,
            line_number=1,
            part_number="COMPLEX-001",
            cas_numbers="7439-92-1|7440-43-9|7732-18-5",
        )
        db.add(part)
        db.commit()

        scanner = ComplianceScanner(db)
        hits = scanner.scan_bom(bom.id)

        assert len(hits) == 2  # Lead and Cadmium are restricted; Water is not
        cas_list = [h.cas_number for h in hits]
        assert "7439-92-1" in cas_list
        assert "7440-43-9" in cas_list
        assert "7732-18-5" not in cas_list
        assert bom.compliance_status == "flagged"

    def test_scan_no_hits_returns_clean(self, db: Session, restrictions: None) -> None:
        """Scanner should mark BOM as clean when no restricted CAS is found.
        Unknown CAS numbers are tracked but don't affect compliance status."""
        bom = Bom(name="Clean BOM", source_type="upload", total_parts=1)
        db.add(bom)
        db.commit()

        part = BomPart(
            bom_id=bom.id,
            line_number=1,
            part_number="R-001",
            cas_numbers="9999-99-9",  # Unknown CAS
        )
        db.add(part)
        db.commit()

        scanner = ComplianceScanner(db)
        hits = scanner.scan_bom(bom.id)

        assert len(hits) == 1
        assert hits[0].hit_type == "unknown_cas"
        assert hits[0].severity == "unknown"
        assert bom.compliance_status == "clean"

    def test_scan_clears_old_results(self, db: Session, restrictions: None) -> None:
        """Re-scanning should replace old results, not append."""
        bom = Bom(name="Re-scan BOM", source_type="upload", total_parts=1)
        db.add(bom)
        db.commit()

        part = BomPart(
            bom_id=bom.id,
            line_number=1,
            part_number="X-001",
            cas_numbers="7439-92-1",
        )
        db.add(part)
        db.commit()

        scanner = ComplianceScanner(db)
        scanner.scan_bom(bom.id)
        first_count = db.query(ScanResult).filter(ScanResult.bom_id == bom.id).count()
        assert first_count == 1

        # Re-scan
        scanner.scan_bom(bom.id)
        second_count = db.query(ScanResult).filter(ScanResult.bom_id == bom.id).count()
        assert second_count == 1

    def test_scan_part_without_cas_is_skipped(self, db: Session, restrictions: None) -> None:
        """Parts with no CAS numbers should be skipped."""
        bom = Bom(name="No-CAS BOM", source_type="upload", total_parts=1)
        db.add(bom)
        db.commit()

        part = BomPart(
            bom_id=bom.id,
            line_number=1,
            part_number="PCB-001",
            cas_numbers=None,
        )
        db.add(part)
        db.commit()

        scanner = ComplianceScanner(db)
        hits = scanner.scan_bom(bom.id)

        assert len(hits) == 0
        assert bom.compliance_status == "clean"
