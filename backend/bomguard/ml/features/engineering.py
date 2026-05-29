"""Regulation-agnostic feature engineering."""

from typing import Any

import pandas as pd
from sqlalchemy.orm import Session

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
        """Full feature vector for a substance."""
        features: dict[str, Any] = {"substance_id": substance_id, "cas_number": cas}
        return pd.Series(features)
