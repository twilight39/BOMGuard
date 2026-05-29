"""Per-regulation similarity features."""

from typing import Any

import pandas as pd


def compute_regulation_features(
    base_vec: pd.Series,
    cas: str,
    regulation_id: str,
    restricted_fps: list[Any],
) -> pd.Series:
    """Add per-regulation similarity features."""
    return base_vec
