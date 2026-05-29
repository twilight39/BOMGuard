"""Gemini RAG pipeline for regulatory Q&A."""

from typing import Any

import google.generativeai as genai


class RegulatoryLLMService:
    """LLM service for regulatory summarization and RAG Q&A."""

    def __init__(self, api_key: str) -> None:
        genai.configure(api_key=api_key)  # type: ignore[reportAttributeAccessIssue]
        self.llm = genai.GenerativeModel("gemini-2.5-flash")  # type: ignore[reportAttributeAccessIssue]
        self.embedding_model = "models/text-embedding-004"

    async def ask(self, question: str) -> dict[str, Any]:
        """RAG-based Q&A over regulatory summaries."""
        return {"answer": "Not implemented yet.", "sources": []}
