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
