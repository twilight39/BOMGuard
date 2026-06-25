"""Regulation-agnostic feature engineering."""

from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

from bomguard.models.database import SubstanceProperties
from bomguard.services.epa_client import EPACompToxClient
from bomguard.services.pubchem_client import PubChemClient


class FeatureEngineeringPipeline:
    """Regulation-agnostic feature computation. Runs once per substance."""

    def __init__(
        self,
        db: Session,
        epa_client: EPACompToxClient | None = None,
        pubchem_client: PubChemClient | None = None,
    ) -> None:
        self.db = db
        self.epa = epa_client or EPACompToxClient()
        self.pubchem = pubchem_client or PubChemClient()

    def compute_all_features(self, substance_id: int, cas: str) -> pd.Series:
        """Full feature vector for a substance.

        Reads from cached SubstanceProperties if available.
        Falls back to a minimal feature vector if not yet enriched.
        """
        props = (
            self.db.query(SubstanceProperties)
            .filter_by(substance_id=substance_id)
            .first()
        )

        features: dict[str, Any] = {
            "substance_id": substance_id,
            "cas_number": cas,
        }

        if props:
            features.update({
                "molecular_weight": props.molecular_weight,
                "logp": props.logp,
                "hbd": props.hbd,
                "hba": props.hba,
                "tpsa": props.tpsa,
                "rotatable_bonds": props.rotatable_bonds,
                "aromatic_rings": props.aromatic_rings,
                "heavy_atoms": props.heavy_atoms,
                "has_smiles": props.has_smiles,
                "has_epa_data": props.has_epa_data,
            })
            if props.morgan_fp_pca_50:
                for i, val in enumerate(props.morgan_fp_pca_50):
                    features[f"fp_pca_{i}"] = val

        return pd.Series(features)


def build_ml_feature_vector(props: SubstanceProperties | None) -> pd.Series:
    """Build a feature vector matching the columns used by RegulationModelRegistry.

    Falls back to zeros for any missing descriptor or fingerprint component so
    that substances without enrichment can still receive an ML risk score.
    """
    rec: dict[str, Any] = {
        "molecular_weight": getattr(props, "molecular_weight", None),
        "logp": getattr(props, "logp", None),
        "hbd": getattr(props, "hbd", None),
        "hba": getattr(props, "hba", None),
        "tpsa": getattr(props, "tpsa", None),
        "rotatable_bonds": getattr(props, "rotatable_bonds", None),
        "aromatic_rings": getattr(props, "aromatic_rings", None),
        "heavy_atoms": getattr(props, "heavy_atoms", None),
        "has_smiles": float(getattr(props, "has_smiles", False) or 0),
        "has_epa_data": float(getattr(props, "has_epa_data", False) or 0),
    }

    if props and props.morgan_fp_pca_50:
        for i, val in enumerate(props.morgan_fp_pca_50):
            rec[f"fp_pca_{i}"] = val

    for i in range(50):
        rec.setdefault(f"fp_pca_{i}", 0.0)

    return pd.Series(rec).fillna(0.0)
