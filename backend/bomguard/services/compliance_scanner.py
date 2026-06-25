"""Rule-based compliance scanner for BOMs with ML risk overlay.

Matches CAS numbers from BOM parts against the substance_regulation_status
 table. For regulations with ``ml_enabled=True`` and at least 100 training
samples, also runs the trained model on enriched substances and records the
predicted risk in dedicated columns. ML predictions are kept separate from
rule-based severity so users do not confuse a model prediction with a legal
restriction.
"""

from sqlalchemy.orm import Session

from bomguard.ml.features.engineering import build_ml_feature_vector
from bomguard.ml.models.registry import RegulationModelRegistry
from bomguard.models.database import (
    Bom,
    BomPart,
    Regulation,
    ScanResult,
    Substance,
    SubstanceProperties,
    SubstanceRegulationStatus,
)

# Do not surface ML predictions unless the model was trained on a reasonable
# amount of data. Tiny training sets produce overfit, unreliable scores.
_MIN_ML_TRAINING_SAMPLES = 100


class ComplianceScanner:
    """Scan a BOM for regulatory compliance hits.

    Combines rule-based CAS matching with ML-based risk prediction for
    regulations that have a trained model available and sufficient training data.
    """

    def __init__(self, db: Session) -> None:
        self.db = db
        self._registry = RegulationModelRegistry()

    def _model_has_min_data(self, regulation_id: str) -> bool:
        """Return True if the loaded model was trained on enough samples."""
        metrics = self._registry.get_metrics(regulation_id)
        if not metrics:
            return False
        n_train = metrics.get("n_train")
        if n_train is None:
            return False
        return int(n_train) >= _MIN_ML_TRAINING_SAMPLES

    def scan_bom(self, bom_id: int) -> list[ScanResult]:
        """Run a compliance scan for a BOM and return hits.

        Steps:
        1. Load BOM parts
        2. For each part, parse CAS numbers
        3. Look up each CAS in substances → substance_regulation_status
        4. For ml_enabled regulations with sufficient training data, run ML risk
           prediction on enriched substances
        5. Write hits + unknown CAS entries to scan_results
        6. Update BOM compliance_status
        """
        bom = self.db.query(Bom).filter(Bom.id == bom_id).first()
        if not bom:
            raise ValueError(f"BOM {bom_id} not found")

        try:
            # Load all regulations for reference
            regulations = {r.id: r for r in self.db.query(Regulation).all()}
            ml_enabled_reg_ids = {r.id for r in regulations.values() if r.ml_enabled}

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
                        # Track unknown CAS so the user knows it couldn't be checked
                        hit = ScanResult(
                            bom_id=bom_id,
                            part_id=part.id,
                            cas_number=cas,
                            hit_type="unknown_cas",
                            risk_score=None,
                            severity="unknown",
                            ml_risk_score=None,
                            ml_risk_tier=None,
                            details={
                                "message": "CAS number not found in substance database — may require enrichment",
                            },
                        )
                        self.db.add(hit)
                        hits.append(hit)
                        continue

                    statuses = (
                        self.db.query(SubstanceRegulationStatus)
                        .filter(SubstanceRegulationStatus.substance_id == substance.id)
                        .all()
                    )

                    restricted_reg_ids: set[str] = set()
                    for status in statuses:
                        if status.status == "not_restricted":
                            continue
                        restricted_reg_ids.add(status.regulation_id)
                        severity = self._severity(status.status, regulations.get(status.regulation_id))
                        hit = ScanResult(
                            bom_id=bom_id,
                            part_id=part.id,
                            regulation_id=status.regulation_id,
                            cas_number=cas,
                            hit_type="direct_match",
                            risk_score=1.0 if status.status == "restricted" else 0.5,
                            severity=severity,
                            ml_risk_score=None,
                            ml_risk_tier=None,
                            details={
                                "substance_name": substance.name,
                                "status": status.status,
                                "effective_date": status.effective_date.isoformat() if status.effective_date else None,
                            },
                        )
                        self.db.add(hit)
                        hits.append(hit)

                    # ML risk overlay: for ml_enabled regulations where this
                    # substance is not already flagged as restricted, predict risk.
                    ml_regs_to_check = ml_enabled_reg_ids - restricted_reg_ids
                    if ml_regs_to_check:
                        props = (
                            self.db.query(SubstanceProperties)
                            .filter_by(substance_id=substance.id)
                            .first()
                        )
                        if props:
                            feature_vector = build_ml_feature_vector(props)
                            for reg_id in ml_regs_to_check:
                                if not self._model_has_min_data(reg_id):
                                    continue
                                prediction = self._registry.predict(reg_id, feature_vector)
                                if not prediction.get("ml_enabled"):
                                    continue
                                tier = prediction.get("risk_tier")
                                if tier not in ("high", "medium"):
                                    continue
                                risk_score = prediction.get("risk_score")
                                hit = ScanResult(
                                    bom_id=bom_id,
                                    part_id=part.id,
                                    regulation_id=reg_id,
                                    cas_number=cas,
                                    hit_type="ml_risk_prediction",
                                    risk_score=None,
                                    severity=None,
                                    ml_risk_score=risk_score,
                                    ml_risk_tier=tier,
                                    details={
                                        "substance_name": substance.name,
                                        "risk_tier": tier,
                                        "message": f"ML model predicts {tier} REACH SVHC risk ({risk_score:.2f})",
                                    },
                                )
                                self.db.add(hit)
                                hits.append(hit)

            # Update BOM compliance status
            direct_hits = [h for h in hits if h.hit_type == "direct_match"]
            ml_hits = [h for h in hits if h.hit_type == "ml_risk_prediction"]
            unknown_hits = [h for h in hits if h.hit_type == "unknown_cas"]

            if direct_hits:
                critical_count = sum(1 for h in direct_hits if h.severity == "critical")
                bom.compliance_status = "flagged" if critical_count > 0 else "review"
            elif ml_hits:
                high_ml_count = sum(1 for h in ml_hits if h.ml_risk_tier == "high")
                bom.compliance_status = "review" if high_ml_count > 0 else "review"
            elif unknown_hits:
                bom.compliance_status = "review"
            else:
                bom.compliance_status = "clean"

            self.db.commit()
            return hits
        except Exception:
            self.db.rollback()
            raise

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
