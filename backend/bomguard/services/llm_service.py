"""RAG pipeline for regulatory Q&A using Gemini embeddings + OpenRouter chat."""

import asyncio
from typing import Any

import google.generativeai as genai
from sqlalchemy import func
from sqlalchemy.orm import Session

from bomguard.config import Settings
from bomguard.models.database import RegulatorySummary
from bomguard.services.openrouter_client import OpenRouterClient

RAG_SYSTEM_PROMPT = """You are BOMGuard, a regulatory compliance assistant for the electronics manufacturing industry. Answer the user's question based ONLY on the regulatory context provided below. If the context does not contain enough information, say so clearly. Cite specific regulations when possible.

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

    def _embed_sync(self, text: str) -> list[float]:
        """Generate a 768-dim Gemini embedding for text (synchronous)."""
        if not self.gemini_api_key:
            raise RuntimeError("Gemini API key is required for embeddings")
        result = genai.embed_content(  # type: ignore[reportAttributeAccessIssue]
            model="models/text-embedding-004",
            content=text,
            task_type="retrieval_query",
        )
        embedding: list[float] = result["embedding"]
        return embedding

    async def _embed(self, text: str) -> list[float]:
        """Async wrapper for embedding generation."""
        return await asyncio.to_thread(self._embed_sync, text)

    def _search_similar_sync(
        self, db: Session, query_embedding: list[float], k: int = 5
    ) -> list[RegulatorySummary]:
        """Find top-k most similar regulatory summaries using pgvector."""
        return (
            db.query(RegulatorySummary)
            .order_by(
                func.cosine_distance(
                    RegulatorySummary.embedding, query_embedding
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

    async def ask(
        self, db: Session, question: str, model: str = "anthropic/claude-3.5-sonnet"
    ) -> dict[str, Any]:
        """RAG-based Q&A over regulatory summaries."""
        query_embedding = await self._embed(question)
        summaries = await self._search_similar(db, query_embedding, k=5)
        context = self._build_context(summaries)
        prompt = RAG_SYSTEM_PROMPT.format(context=context, question=question)
        answer = await self.openrouter.chat(
            messages=[{"role": "user", "content": prompt}],
            model=model,
        )
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
        model: str = "anthropic/claude-3.5-sonnet",
    ) -> tuple[str, list[RegulatorySummary]]:
        """Prepare a streaming RAG response. Returns context string and summaries."""
        query_embedding = await self._embed(question)
        summaries = await self._search_similar(db, query_embedding, k=5)
        context = self._build_context(summaries)
        prompt = RAG_SYSTEM_PROMPT.format(context=context, question=question)
        return prompt, summaries
