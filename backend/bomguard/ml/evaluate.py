"""Temporal holdout evaluation."""

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    import pandas as pd


def get_split_strategy(dates: "pd.Series") -> tuple[str, object, int]:
    """Auto-switch from random to temporal split."""
    n_batches = dates.dt.to_period("M").nunique()
    if n_batches >= 6:
        cutoff = dates.quantile(0.8)
        train_mask = dates < cutoff
        return "temporal", train_mask, n_batches

    return "random", None, n_batches
