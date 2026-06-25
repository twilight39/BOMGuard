"""Temporal holdout evaluation and split strategies."""

import numpy as np
import pandas as pd
from sklearn.model_selection import StratifiedShuffleSplit


def _both_classes_present(y: pd.Series, idx: np.ndarray) -> bool:
    """Return True if both class labels (0 and 1) are present in idx."""
    labels = y.iloc[idx]
    return int(labels.sum()) > 0 and int(labels.sum()) < len(labels)


def _min_test_size(y: pd.Series, min_test_per_class: int) -> float:
    """Return the smallest stratified test_size that gives ``min_test_per_class`` of each class.

    For very imbalanced data a fixed 20% test split can leave < 5 samples of the
    minority class, making AUC unstable. This raises the test_size just enough to
    guarantee a usable minority-class count, capped at 50% so training data is not
    starved.
    """
    n = len(y)
    if n == 0:
        return 0.0
    n_pos = int(y.sum())
    n_neg = n - n_pos
    required = 0.0
    if n_pos > 0:
        required = max(required, min_test_per_class / n_pos)
    if n_neg > 0:
        required = max(required, min_test_per_class / n_neg)
    return float(min(max(required, 0.0), 0.5))


def _split_has_min_counts(y: pd.Series, idx: np.ndarray, min_test_per_class: int) -> bool:
    """Return True if the split indexed by ``idx`` has enough of both classes."""
    labels = y.iloc[idx]
    n_pos = int(labels.sum())
    n_neg = len(labels) - n_pos
    return n_pos >= min_test_per_class and n_neg >= min_test_per_class


def get_split_strategy(
    dates: pd.Series,
    y: pd.Series,
    test_size: float = 0.2,
    random_state: int = 42,
    min_test_per_class: int = 5,
) -> tuple[str, np.ndarray, np.ndarray]:
    """Return train/test indices preserving both classes and a minimum test count.

    Uses a temporal split when there are >= 6 months of history, but falls
    back to a stratified random split if the temporal split would place all
    samples of one class in either train or test, or if the test set would
    contain fewer than ``min_test_per_class`` samples of either class.

    Args:
        dates: Series of datetime-like values (e.g. effective_date).
        y: Binary labels aligned with dates.
        test_size: Fraction of data to hold out for testing. Will be raised
            automatically for imbalanced data to ensure ``min_test_per_class``.
        random_state: Random seed for reproducible stratified splits.
        min_test_per_class: Minimum number of positives and negatives required
            in the test split.

    Returns:
        Tuple of (strategy_name, train_indices, test_indices).
    """
    dates = pd.to_datetime(dates)
    n_batches = dates.dt.to_period("M").nunique()
    n = len(dates)

    effective_test_size = max(test_size, _min_test_size(y, min_test_per_class))

    if n_batches >= 6:
        cutoff = dates.quantile(1 - effective_test_size)
        train_mask = dates < cutoff
        train_idx = np.nonzero(np.asarray(train_mask))[0]
        test_idx = np.nonzero(~np.asarray(train_mask))[0]

        if (
            _both_classes_present(y, train_idx)
            and _both_classes_present(y, test_idx)
            and _split_has_min_counts(y, test_idx, min_test_per_class)
        ):
            return "temporal", train_idx, test_idx

    # Fall back to stratified shuffle split so both classes are guaranteed
    # in train and test even with imbalanced data.
    splitter = StratifiedShuffleSplit(
        n_splits=1, test_size=effective_test_size, random_state=random_state
    )
    train_idx, test_idx = next(splitter.split(np.zeros((n, 1)), y))
    return "random_stratified", train_idx, test_idx
