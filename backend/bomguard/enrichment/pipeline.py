"""Substance enrichment pipeline.

Fetches external data (PubChem SMILES, molecular properties, EPA data)
and computes derived descriptors for ML feature engineering.
"""

from typing import Any

from sqlalchemy.orm import Session

from bomguard.enrichment.fingerprints import compute_pca_for_batch
from bomguard.models.database import Substance, SubstanceProperties
from bomguard.services.pubchem_client import PubChemClient


def _compute_rdkit_descriptors(smiles: str) -> dict[str, Any]:
    """Compute molecular descriptors from SMILES using RDKit.

    Returns an empty dict if RDKit is not available or SMILES is invalid.
    """
    # Attempt RDKit import at module level to avoid mypy unreachable-code warnings
    rdkit_available: bool = True
    try:
        from rdkit import Chem  # type: ignore[import]
        from rdkit.Chem import Descriptors, rdMolDescriptors  # type: ignore[import]
    except Exception:
        rdkit_available = False

    if not rdkit_available:
        return {}

    mol = Chem.MolFromSmiles(smiles)  # type: ignore[attr-defined]
    if mol is None:
        return {}

    return {
        "molecular_weight": Descriptors.MolWt(mol),  # type: ignore[attr-defined]
        "logp": Descriptors.MolLogP(mol),  # type: ignore[attr-defined]
        "hbd": rdMolDescriptors.CalcNumHBD(mol),  # type: ignore[attr-defined]
        "hba": rdMolDescriptors.CalcNumHBA(mol),  # type: ignore[attr-defined]
        "tpsa": rdMolDescriptors.CalcTPSA(mol),  # type: ignore[attr-defined]
        "rotatable_bonds": rdMolDescriptors.CalcNumRotatableBonds(mol),  # type: ignore[attr-defined]
        "aromatic_rings": rdMolDescriptors.CalcNumAromaticRings(mol),  # type: ignore[attr-defined]
        "heavy_atoms": mol.GetNumHeavyAtoms(),  # type: ignore[attr-defined]
    }


class EnrichmentPipeline:
    """Enrich substances with external molecular data."""

    def __init__(self, db: Session, pubchem: PubChemClient | None = None) -> None:
        self.db = db
        self.pubchem = pubchem or PubChemClient()

    async def enrich_substance(self, substance: Substance) -> SubstanceProperties:
        """Fetch and compute all properties for a single substance.

        Creates or updates the SubstanceProperties row.
        """
        props = (
            self.db.query(SubstanceProperties)
            .filter_by(substance_id=substance.id)
            .first()
        )
        if not props:
            props = SubstanceProperties(substance_id=substance.id)
            self.db.add(props)

        smiles: str | None = None
        if substance.cas_number:
            smiles = await self.pubchem.get_smiles(substance.cas_number)
            pubchem_props = await self.pubchem.get_properties(substance.cas_number)

            if pubchem_props:
                props.molecular_weight = pubchem_props.get("MolecularWeight")
                props.logp = pubchem_props.get("XLogP")
                props.hbd = pubchem_props.get("HBondDonorCount")
                props.hba = pubchem_props.get("HBondAcceptorCount")
                props.tpsa = pubchem_props.get("TPSA")
                props.rotatable_bonds = pubchem_props.get("RotatableBondCount")

        if smiles:
            substance.smiles = smiles
            props.has_smiles = True
            rdkit_desc = _compute_rdkit_descriptors(smiles)
            for key, value in rdkit_desc.items():
                setattr(props, key, value)

        self.db.commit()
        return props

    async def enrich_all_missing(self, batch_size: int = 50) -> dict[str, Any]:
        """Enrich all substances that lack properties.

        Also computes Morgan fingerprints + PCA(50) for the batch.

        Returns a summary dict with counts.
        """
        from sqlalchemy import func


        # Substances without a properties row OR with has_smiles=False
        missing = (
            self.db.query(Substance)
            .outerjoin(SubstanceProperties)
            .filter(
                (SubstanceProperties.substance_id.is_(None))
                | (SubstanceProperties.has_smiles.is_(False))
            )
            .limit(batch_size)
            .all()
        )

        enriched = 0
        failed = 0
        for substance in missing:
            try:
                await self.enrich_substance(substance)
                enriched += 1
            except Exception:
                failed += 1

        # Compute Morgan fingerprints + PCA for enriched batch
        self._compute_fingerprints_for_batch(missing)

        total = self.db.query(func.count(Substance.id)).scalar() or 0
        with_props = (
            self.db.query(func.count(SubstanceProperties.substance_id))
            .filter(SubstanceProperties.has_smiles.is_(True))
            .scalar()
            or 0
        )

        return {
            "batch_size": batch_size,
            "processed": len(missing),
            "enriched": enriched,
            "failed": failed,
            "total_substances": total,
            "with_smiles": with_props,
            "coverage_pct": round((with_props / total) * 100, 1) if total else 0.0,
        }

    def _compute_fingerprints_for_batch(self, substances: list[Substance]) -> None:
        """Compute Morgan fingerprints and PCA(50) for a batch of substances.

        Only processes substances that have valid SMILES.
        Skips PCA fitting if the batch is too small (< 10 substances).
        """
        from bomguard.enrichment.fingerprints import load_pca_model

        smiles_list: list[str] = []
        substance_map: list[Substance] = []

        for sub in substances:
            if sub.smiles:
                smiles_list.append(sub.smiles)
                substance_map.append(sub)

        if len(smiles_list) < 10:
            # Not enough samples to fit PCA; skip for now.
            # They will be re-processed in a future larger batch.
            return

        pca = load_pca_model()
        pca_vectors, pca_model = compute_pca_for_batch(smiles_list, existing_pca=pca)

        for sub, vec in zip(substance_map, pca_vectors, strict=True):
            if vec is not None:
                props = (
                    self.db.query(SubstanceProperties)
                    .filter_by(substance_id=sub.id)
                    .first()
                )
                if props:
                    props.morgan_fp_pca_50 = vec.tolist()

        self.db.commit()
