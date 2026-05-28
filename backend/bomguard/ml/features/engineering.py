"""Regulation-agnostic feature engineering."""

import pandas as pd


class FeatureEngineeringPipeline:
    """Regulation-agnostic feature computation. Runs once per substance."""

    def __init__(self, db: object, epa_client: object, pubchem_client: object) -> None:
        self.db = db
        self.epa = epa_client
        self.pubchem = pubchem_client

    def compute_all_features(self, substance_id: int, cas: str) -> pd.Series:
        """Full feature vector for a substance."""
        features = {"substance_id": substance_id, "cas_number": cas}
        return pd.Series(features)
