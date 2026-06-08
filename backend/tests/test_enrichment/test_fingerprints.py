"""Tests for Morgan fingerprint and PCA computation."""


import numpy as np
import pytest

from bomguard.enrichment.fingerprints import (
    PCA_MODEL_PATH,
    compute_morgan_fingerprint,
    compute_pca_for_batch,
    fit_pca_and_transform,
    load_pca_model,
    save_pca_model,
)


class TestComputeMorganFingerprint:
    def test_ethanol(self) -> None:
        fp = compute_morgan_fingerprint("CCO")
        assert isinstance(fp, np.ndarray)
        assert fp.shape == (2048,)
        assert fp.dtype == np.float32
        assert fp.sum() > 0  # should have some bits set

    def test_invalid_smiles_raises(self) -> None:
        with pytest.raises(ValueError, match="Invalid SMILES"):
            compute_morgan_fingerprint("not-a-smiles!!!")


class TestFitPcaAndTransform:
    def test_basic(self) -> None:
        fps = [np.random.rand(2048).astype(np.float32) for _ in range(60)]
        transformed, pca = fit_pca_and_transform(fps, n_components=50)
        assert transformed.shape == (60, 50)
        assert hasattr(pca, "components_")

    def test_too_few_samples_raises(self) -> None:
        fps = [np.random.rand(2048).astype(np.float32) for _ in range(5)]
        with pytest.raises(ValueError, match="Need at least 50 fingerprints"):
            fit_pca_and_transform(fps, n_components=50)


class TestPcaPersistence:
    def test_roundtrip(self) -> None:
        from sklearn.decomposition import PCA

        pca = PCA(n_components=50)
        X = np.random.rand(100, 2048).astype(np.float32)
        pca.fit(X)

        save_pca_model(pca, path=PCA_MODEL_PATH)
        loaded = load_pca_model(path=PCA_MODEL_PATH)

        assert loaded is not None
        assert loaded.n_components_ == 50

        # Transform should produce identical results
        sample = np.random.rand(1, 2048).astype(np.float32)
        assert np.allclose(pca.transform(sample), loaded.transform(sample), rtol=1e-4, atol=1e-5)

        # Cleanup
        if PCA_MODEL_PATH.exists():
            PCA_MODEL_PATH.unlink()


class TestComputePcaForBatch:
    def test_with_existing_pca(self) -> None:
        from sklearn.decomposition import PCA

        pca = PCA(n_components=50)
        X = np.random.rand(100, 2048).astype(np.float32)
        pca.fit(X)

        vecs, model = compute_pca_for_batch(
            ["CCO", "CCCO", "CCCCO"], existing_pca=pca, save=False
        )
        assert model is pca
        assert len(vecs) == 3
        assert all(v is not None for v in vecs)
        assert all(v.shape == (50,) for v in vecs if v is not None)

    def test_invalid_smiles_skipped(self) -> None:
        # Generate 52 valid SMILES (alkane chain lengths 1-52) + 2 invalid
        smiles = ["C" * i for i in range(1, 53)] + ["invalid!!!", "also-bad!!!"]
        vecs, model = compute_pca_for_batch(smiles, save=False)
        assert len(vecs) == 54
        assert vecs[0] is not None
        assert vecs[52] is None  # first invalid
        assert vecs[53] is None  # second invalid
