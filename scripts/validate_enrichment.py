#!/usr/bin/env python3
"""Quick manual validation script for the enrichment pipeline.

Run from repo root: cd backend && uv run python ../scripts/validate_enrichment.py
"""

import asyncio
import sys


def section(title: str) -> None:
    print(f"\n=== {title} ===")


def check_pubchem() -> None:
    from bomguard.services.pubchem_client import PubChemClient

    async def main() -> None:
        client = PubChemClient()
        smiles = await client.get_smiles("64-17-5")
        props = await client.get_properties("64-17-5")
        print("SMILES:", smiles)
        print("MolWt:", props.get("MolecularWeight"))
        print("LogP:", props.get("XLogP"))
        missing = await client.get_smiles("999-99-9")
        print("Missing CAS:", missing)

    asyncio.run(main())


def check_fingerprints() -> None:
    from bomguard.enrichment.fingerprints import (
        compute_morgan_fingerprint,
        compute_pca_for_batch,
        load_pca_model,
    )

    fp = compute_morgan_fingerprint("CCO")
    print("Fingerprint shape:", fp.shape)

    smiles = ["C" * i for i in range(1, 55)]
    vecs, model = compute_pca_for_batch(smiles, save=True)
    print("PCA model persisted:", load_pca_model() is not None)
    print("First vector shape:", vecs[0].shape if vecs[0] is not None else None)


def check_descriptors() -> None:
    from bomguard.enrichment.pipeline import _compute_rdkit_descriptors

    desc = _compute_rdkit_descriptors("CCO")
    for k, v in desc.items():
        print(f"  {k}: {v}")


def check_celery() -> None:
    from bomguard.celery_app import celery_app

    for name in sorted(celery_app.tasks):
        if "enrich" in name:
            print(f"  {name}")


def main() -> int:
    section("1. PubChem live lookup")
    check_pubchem()

    section("2. Morgan fingerprint + PCA")
    check_fingerprints()

    section("3. RDKit descriptors")
    check_descriptors()

    section("4. Celery task registration")
    check_celery()

    section("All checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
