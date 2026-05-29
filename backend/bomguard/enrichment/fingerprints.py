"""Morgan fingerprint computation and PCA(50) reduction.

This module computes 2048-bit Morgan fingerprints via RDKit and reduces
them to 50 dimensions using scikit-learn PCA. The fitted PCA model is
persisted to disk so the same transform is applied consistently.
"""

import pickle
from pathlib import Path
from typing import Any

import numpy as np

# Attempt RDKit import at module level
try:
    from rdkit import Chem  # type: ignore[import]
    from rdkit.Chem.rdFingerprintGenerator import GetMorganGenerator  # type: ignore[import]

    _RDKIT_AVAILABLE = True
except Exception:
    _RDKIT_AVAILABLE = False

PCA_MODEL_PATH: Path = Path(__file__).parent.parent / "models" / "fingerprint_pca_50.pkl"


def _ensure_model_dir() -> None:
    PCA_MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)


def compute_morgan_fingerprint(smiles: str, radius: int = 2, n_bits: int = 2048) -> np.ndarray:
    """Compute a 2048-bit Morgan fingerprint from a SMILES string.

    Args:
        smiles: Canonical SMILES string.
        radius: Morgan fingerprint radius (default 2 = ECFP4).
        n_bits: Number of bits in the fingerprint vector.

    Returns:
        A 1-D numpy array of shape (n_bits,) with dtype float32.

    Raises:
        RuntimeError: If RDKit is not installed.
        ValueError: If the SMILES is invalid.
    """
    if not _RDKIT_AVAILABLE:
        raise RuntimeError("RDKit is required for fingerprint computation")

    mol = Chem.MolFromSmiles(smiles)  # type: ignore[attr-defined]
    if mol is None:
        raise ValueError(f"Invalid SMILES: {smiles}")

    gen = GetMorganGenerator(radius=radius, fpSize=n_bits)  # type: ignore[attr-defined]
    fp = gen.GetFingerprint(mol)
    return np.array(fp, dtype=np.float32)


def fit_pca_and_transform(
    fingerprints: list[np.ndarray],
    n_components: int = 50,
) -> tuple[np.ndarray, Any]:
    """Fit PCA(n_components) on a corpus of fingerprints and transform them.

    Args:
        fingerprints: List of 1-D arrays, each of shape (n_bits,).
        n_components: Number of PCA components (default 50).

    Returns:
        Tuple of (transformed array of shape (n_samples, n_components), pca_model).
    """
    from sklearn.decomposition import PCA

    if len(fingerprints) < n_components:
        raise ValueError(
            f"Need at least {n_components} fingerprints to fit PCA, got {len(fingerprints)}"
        )

    X = np.vstack(fingerprints)
    pca = PCA(n_components=n_components)
    transformed = pca.fit_transform(X)
    return transformed, pca


def save_pca_model(pca: Any, path: Path | None = None) -> None:
    """Serialize a fitted PCA model to disk."""
    _ensure_model_dir()
    path = path or PCA_MODEL_PATH
    with open(path, "wb") as f:
        pickle.dump(pca, f)


def load_pca_model(path: Path | None = None) -> Any | None:
    """Load a previously saved PCA model from disk.

    Returns None if no model exists.
    """
    path = path or PCA_MODEL_PATH
    if not path.exists():
        return None
    with open(path, "rb") as f:
        return pickle.load(f)


def transform_with_pca(fingerprints: list[np.ndarray], pca: Any) -> np.ndarray:
    """Transform fingerprints using a pre-fitted PCA model.

    Args:
        fingerprints: List of 1-D arrays, each of shape (n_bits,).
        pca: A fitted sklearn PCA instance.

    Returns:
        Array of shape (n_samples, n_components).
    """
    X = np.vstack(fingerprints)
    transformed: np.ndarray = pca.transform(X)
    return transformed


def compute_pca_for_batch(
    smiles_list: list[str],
    *,
    existing_pca: Any | None = None,
    save: bool = True,
) -> tuple[list[np.ndarray | None], Any]:
    """Compute Morgan fingerprints and PCA(50) for a batch of SMILES.

    If existing_pca is provided, it is used for transformation.
    Otherwise, a new PCA is fit on the batch and saved to disk.

    Returns:
        Tuple of (list of PCA vectors or None for invalid SMILES, pca_model).
    """
    fingerprints: list[np.ndarray] = []
    valid_indices: list[int] = []

    for idx, smiles in enumerate(smiles_list):
        try:
            fp = compute_morgan_fingerprint(smiles)
            fingerprints.append(fp)
            valid_indices.append(idx)
        except (ValueError, RuntimeError):
            pass

    if not fingerprints:
        return [None] * len(smiles_list), existing_pca

    if existing_pca is not None:
        transformed = transform_with_pca(fingerprints, existing_pca)
    else:
        transformed, existing_pca = fit_pca_and_transform(fingerprints)
        if save:
            save_pca_model(existing_pca)

    # Map back to original indices
    result: list[np.ndarray | None] = [None] * len(smiles_list)
    for vi, vec in zip(valid_indices, transformed, strict=True):
        result[vi] = vec

    return result, existing_pca
