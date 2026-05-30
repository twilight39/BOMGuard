"""Regulatory summary generation using OpenRouter + Gemini embeddings."""

import google.generativeai as genai
from sqlalchemy.orm import Session

from bomguard.models.database import RegulatorySummary, Substance, SubstanceRegulationStatus
from bomguard.services.openrouter_client import OpenRouterClient

SUMMARY_PROMPT = """You are a regulatory compliance assistant. Write a concise plain-language summary (2-3 sentences) about the regulatory status of the following chemical substance.

Substance: {name}
CAS: {cas}
EC: {ec}
SMILES: {smiles}

Regulatory restrictions:
{restrictions}

Molecular properties:
{properties}

Summary:"""


def _build_restrictions_text(
    db: Session, substance_id: int
) -> str:
    """Build a text description of restrictions for a substance."""
    statuses = (
        db.query(SubstanceRegulationStatus)
        .filter(SubstanceRegulationStatus.substance_id == substance_id)
        .all()
    )
    if not statuses:
        return "No known restrictions."
    lines: list[str] = []
    for s in statuses:
        lines.append(f"- {s.regulation_id}: {s.status}")
    return "\n".join(lines)


def _build_properties_text(substance: Substance) -> str:
    """Build a text description of molecular properties."""
    props = substance.properties
    if not props:
        return "No properties available."
    fields: list[str] = []
    if props.molecular_weight is not None:
        fields.append(f"MW: {props.molecular_weight}")
    if props.logp is not None:
        fields.append(f"LogP: {props.logp}")
    if props.tpsa is not None:
        fields.append(f"TPSA: {props.tpsa}")
    if props.bcf is not None:
        fields.append(f"BCF: {props.bcf}")
    return ", ".join(fields) if fields else "No properties available."


class SummaryGenerator:
    """Generates regulatory summaries and embeddings for substances."""

    def __init__(
        self,
        openrouter_client: OpenRouterClient,
        gemini_api_key: str | None = None,
    ) -> None:
        self.openrouter = openrouter_client
        self.gemini_api_key = gemini_api_key
        if gemini_api_key:
            genai.configure(api_key=gemini_api_key)  # type: ignore[reportAttributeAccessIssue]

    def generate_summary(self, db: Session, substance: Substance) -> str:
        """Generate a plain-language summary for a substance."""
        restrictions = _build_restrictions_text(db, substance.id)
        properties = _build_properties_text(substance)
        prompt = SUMMARY_PROMPT.format(
            name=substance.name,
            cas=substance.cas_number or "N/A",
            ec=substance.ec_number or "N/A",
            smiles=substance.smiles or "N/A",
            restrictions=restrictions,
            properties=properties,
        )
        import asyncio

        return asyncio.run(self.openrouter.chat(messages=[{"role": "user", "content": prompt}]))

    def generate_embedding(self, text: str) -> list[float]:
        """Generate a 768-dim Gemini embedding for text."""
        if not self.gemini_api_key:
            raise RuntimeError("Gemini API key is required for embeddings")
        result = genai.embed_content(  # type: ignore[reportAttributeAccessIssue]
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_document",
        )
        embedding: list[float] = result["embedding"]
        return embedding

    def save_summary(
        self,
        db: Session,
        substance: Substance,
        summary_text: str,
        embedding: list[float],
        model_used: str = "anthropic/claude-3.5-sonnet",
    ) -> RegulatorySummary:
        """Save or update a regulatory summary in the database."""
        existing = (
            db.query(RegulatorySummary)
            .filter(
                RegulatorySummary.substance_id == substance.id,
            )
            .first()
        )
        if existing:
            existing.summary_text = summary_text
            existing.embedding = embedding
            existing.model_used = model_used
            db.commit()
            db.refresh(existing)
            return existing

        summary = RegulatorySummary(
            substance_id=substance.id,
            summary_text=summary_text,
            embedding=embedding,
            model_used=model_used,
        )
        db.add(summary)
        db.commit()
        db.refresh(summary)
        return summary

    def process_substance(
        self, db: Session, substance: Substance, skip_existing: bool = True
    ) -> RegulatorySummary | None:
        """Generate and save a summary for a single substance."""
        if skip_existing:
            existing = (
                db.query(RegulatorySummary)
                .filter(RegulatorySummary.substance_id == substance.id)
                .first()
            )
            if existing:
                return None

        summary_text = self.generate_summary(db, substance)
        embedding = self.generate_embedding(summary_text)
        return self.save_summary(db, substance, summary_text, embedding)

    def process_batch(
        self, db: Session, batch_size: int = 50, skip_existing: bool = True
    ) -> list[RegulatorySummary]:
        """Process a batch of substances without summaries."""
        query = db.query(Substance)
        if skip_existing:
            existing_ids = (
                db.query(RegulatorySummary.substance_id)
                .filter(RegulatorySummary.substance_id.isnot(None))
                .all()
            )
            existing_id_set = {row[0] for row in existing_ids}
            if existing_id_set:
                query = query.filter(~Substance.id.in_(existing_id_set))

        substances = query.limit(batch_size).all()
        results: list[RegulatorySummary] = []
        for substance in substances:
            try:
                summary = self.process_substance(db, substance, skip_existing=False)
                if summary:
                    results.append(summary)
            except Exception:
                continue
        return results
