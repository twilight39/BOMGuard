"""RAG pipeline for regulatory Q&A using Gemini embeddings + OpenRouter chat."""

import asyncio
from typing import Any

import google.generativeai as genai
from pgvector.sqlalchemy import Vector
from sqlalchemy import func
from sqlalchemy.orm import Session

from bomguard.config import Settings
from bomguard.models.database import RegulatorySummary
from bomguard.services.openrouter_client import OpenRouterClient

RAG_SYSTEM_INSTRUCTIONS = """You are BOMGuard, a regulatory compliance assistant for the electronics manufacturing industry.

Regulations currently tracked:
- EU REACH SVHC Candidate List (ECHA)
- US State PFAS Restrictions
- EU RoHS Directive 2011/65/EU
- US TSCA Section 6(h) PBT
- China RoHS 2 (SJ/T 11363)

To add a new regulation, a developer must:
1. Create a scraper module in backend/bomguard/ingestion/scrapers/
2. Register it in backend/bomguard/ingestion/registry.py
3. Run the scraper via the admin pipeline or Celery task

Rules:
- Get straight to the point. Do NOT start with phrases like "Based on the provided context" or "According to the information".
- Use markdown formatting freely (**bold**, *italics*, bullet points) to make the answer readable.
- If the context does not contain enough information, say so clearly.
- Cite specific regulations when possible."""

RAG_SYSTEM_PROMPT = """You are BOMGuard, a regulatory compliance assistant for the electronics manufacturing industry. Answer the user's question based ONLY on the regulatory context provided below.

System context:
The following regulations are currently tracked in BOMGuard:
- EU REACH SVHC Candidate List (ECHA)
- US State PFAS Restrictions
- EU RoHS Directive 2011/65/EU
- US TSCA Section 6(h) PBT
- China RoHS 2 (SJ/T 11363)

To add a new regulation, a developer must:
1. Create a scraper module in backend/bomguard/ingestion/scrapers/
2. Register it in backend/bomguard/ingestion/registry.py
3. Run the scraper via the admin pipeline or Celery task

Rules:
- Get straight to the point. Do NOT start with phrases like "Based on the provided context" or "According to the information".
- Use markdown formatting freely (**bold**, *italics*, bullet points) to make the answer readable.
- If the context does not contain enough information, say so clearly.
- Cite specific regulations when possible.

Context:
{context}

Question: {question}

Answer:"""

settings = Settings()


class RegulatoryLLMService:
    """LLM service for regulatory summarization and RAG Q&A."""

    def __init__(self) -> None:
        self.openrouter = OpenRouterClient(
            api_key=settings.openrouter_api_key or "",
            http_referer="https://github.com/effyyang/bomguard",
            x_title="BOMGuard",
        )
        self.gemini_api_key = settings.gemini_api_key
        if self.gemini_api_key:
            genai.configure(api_key=self.gemini_api_key)  # type: ignore[reportAttributeAccessIssue]

    async def _embed(self, text: str) -> list[float]:
        """Generate a 768-dim embedding for text.

        Uses Gemini directly when a Gemini key is available,
        otherwise falls back to OpenRouter's embedding endpoint.
        """
        if self.gemini_api_key:
            result = await asyncio.to_thread(
                genai.embed_content,  # type: ignore[reportAttributeAccessIssue]
                model="models/text-embedding-004",
                content=text,
                task_type="retrieval_query",
            )
            embedding: list[float] = result["embedding"]
            return embedding
        return await self.openrouter.embed(text)

    def _search_similar_sync(
        self, db: Session, query_embedding: list[float], k: int = 5
    ) -> list[RegulatorySummary]:
        """Find top-k most similar regulatory summaries using pgvector."""
        return (
            db.query(RegulatorySummary)
            .order_by(
                func.cosine_distance(
                    RegulatorySummary.embedding,
                    func.cast(query_embedding, Vector(768)),
                )
            )
            .limit(k)
            .all()
        )

    async def _search_similar(
        self, db: Session, query_embedding: list[float], k: int = 5
    ) -> list[RegulatorySummary]:
        """Async wrapper for similarity search."""
        return await asyncio.to_thread(self._search_similar_sync, db, query_embedding, k)

    def _build_context(self, summaries: list[RegulatorySummary]) -> str:
        """Build a context string from retrieved summaries."""
        parts: list[str] = []
        for i, s in enumerate(summaries, 1):
            parts.append(f"[{i}] {s.summary_text}")
        return "\n\n".join(parts)

    def _build_messages(
        self,
        question: str,
        context: str,
        history: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        """Build the messages array for OpenRouter."""
        messages: list[dict[str, str]] = [
            {"role": "system", "content": RAG_SYSTEM_INSTRUCTIONS},
        ]
        if history:
            messages.extend(history)
        messages.append(
            {"role": "user", "content": f"Context:\n{context}\n\nQuestion: {question}"}
        )
        return messages

    async def ask(
        self, db: Session, question: str, model: str = "google/gemini-2.5-flash"
    ) -> dict[str, Any]:
        """RAG-based Q&A over regulatory summaries."""
        query_embedding = await self._embed(question)
        summaries = await self._search_similar(db, query_embedding, k=5)
        context = self._build_context(summaries)
        messages = self._build_messages(question, context)
        answer = await self.openrouter.chat(messages=messages, model=model)
        return {
            "answer": answer,
            "sources": [
                {
                    "id": s.id,
                    "substance_id": s.substance_id,
                    "regulation_id": s.regulation_id,
                    "summary_text": s.summary_text,
                }
                for s in summaries
            ],
        }

    async def ask_stream(
        self,
        db: Session,
        question: str,
        history: list[dict[str, str]] | None = None,
        model: str = "google/gemini-2.5-flash",
    ) -> tuple[list[dict[str, str]], list[RegulatorySummary]]:
        """Prepare a streaming RAG response. Returns messages array and summaries."""
        query_embedding = await self._embed(question)
        summaries = await self._search_similar(db, query_embedding, k=5)
        context = self._build_context(summaries)
        messages = self._build_messages(question, context, history)
        return messages, summaries
