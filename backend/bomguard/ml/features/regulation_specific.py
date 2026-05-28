"""Per-regulation similarity features."""

import pandas as pd


def compute_regulation_features(
    base_vec: pd.Series,
    cas: str,
    regulation_id: str,
    restricted_fps: list,
) -> pd.Series:
    """Add per-regulation similarity features."""
    return base_vec
