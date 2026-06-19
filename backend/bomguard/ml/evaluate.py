"""Temporal holdout evaluation and split strategies."""

import numpy as np
import pandas as pd


def get_split_strategy(
    dates: pd.Series,
) -> tuple[str, np.ndarray, np.ndarray]:
    """Auto-switch from random stratified to temporal split.

    Args:
        dates: Series of datetime-like values (e.g. effective_date).

    Returns:
        Tuple of (strategy_name, train_indices, test_indices).
        Strategy is "temporal" when >= 6 months of history,
        otherwise "random" with an 80/20 stratified split.
    """
    dates = pd.to_datetime(dates)
    n_batches = dates.dt.to_period("M").nunique()

    if n_batches >= 6:
        cutoff = dates.quantile(0.8)
        train_mask = dates < cutoff
        strategy = "temporal"
    else:
        # Fallback to random 80/20 – caller should stratify by label
        rng = np.random.default_rng(42)
        n = len(dates)
        shuffled = rng.permutation(n)
        split_idx = int(n * 0.8)
        train_mask = np.zeros(n, dtype=bool)
        train_mask[shuffled[:split_idx]] = True
        strategy = "random"

    train_idx = np.nonzero(np.asarray(train_mask))[0]
    test_idx = np.nonzero(~np.asarray(train_mask))[0]
    return strategy, train_idx, test_idx
