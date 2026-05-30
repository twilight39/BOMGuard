"""Rule-based compliance scanner for BOMs.

Matches CAS numbers from BOM parts against the substance_regulation_status
table. ML-based risk prediction can be layered on later.
"""

from sqlalchemy.orm import Session

from bomguard.models.database import Bom, BomPart, Regulation, ScanResult, Substance, SubstanceRegulationStatus


class ComplianceScanner:
    """Scan a BOM for regulatory compliance hits.

    Currently implements rule-based CAS matching only.
    ML risk prediction will be added when models are trained.
    """

    def __init__(self, db: Session) -> None:
        self.db = db

    def scan_bom(self, bom_id: int) -> list[ScanResult]:
        """Run a compliance scan for a BOM and return hits.

        Steps:
        1. Load BOM parts
        2. For each part, parse CAS numbers
        3. Look up each CAS in substances → substance_regulation_status
        4. Write hits to scan_results
        5. Update BOM compliance_status
        """
        bom = self.db.query(Bom).filter(Bom.id == bom_id).first()
        if not bom:
            raise ValueError(f"BOM {bom_id} not found")

        # Load all regulations for reference
        regulations = {r.id: r for r in self.db.query(Regulation).all()}

        # Clear old scan results for this BOM
        self.db.query(ScanResult).filter(ScanResult.bom_id == bom_id).delete()

        hits: list[ScanResult] = []
        parts = self.db.query(BomPart).filter(BomPart.bom_id == bom_id).all()

        for part in parts:
            if not part.cas_numbers:
                continue

            cas_list = [c.strip() for c in part.cas_numbers.split("|") if c.strip()]
            for cas in cas_list:
                substance = (
                    self.db.query(Substance)
                    .filter(Substance.cas_number == cas)
                    .first()
                )
                if not substance:
                    continue

                statuses = (
                    self.db.query(SubstanceRegulationStatus)
                    .filter(SubstanceRegulationStatus.substance_id == substance.id)
                    .all()
                )

                for status in statuses:
                    if status.status == "not_restricted":
                        continue
                    severity = self._severity(status.status, regulations.get(status.regulation_id))
                    hit = ScanResult(
                        bom_id=bom_id,
                        part_id=part.id,
                        regulation_id=status.regulation_id,
                        cas_number=cas,
                        hit_type="direct_match",
                        risk_score=1.0 if status.status == "restricted" else 0.5,
                        severity=severity,
                        details={
                            "substance_name": substance.name,
                            "status": status.status,
                            "effective_date": status.effective_date.isoformat() if status.effective_date else None,
                        },
                    )
                    self.db.add(hit)
                    hits.append(hit)

        # Update BOM compliance status
        if hits:
            critical_count = sum(1 for h in hits if h.severity == "critical")
            bom.compliance_status = "flagged" if critical_count > 0 else "review"
        else:
            bom.compliance_status = "clean"

        self.db.commit()
        return hits

    @staticmethod
    def _severity(status: str, regulation: Regulation | None) -> str:
        if status == "restricted":
            return "critical"
        if status == "not_restricted":
            return "clean"
        # Consultation / candidate list
        if regulation and regulation.ml_enabled:
            return "high"
        return "medium"
