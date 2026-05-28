"""Gemini RAG pipeline for regulatory Q&A."""

import google.generativeai as genai


class RegulatoryLLMService:
    """LLM service for regulatory summarization and RAG Q&A."""

    def __init__(self, api_key: str) -> None:
        genai.configure(api_key=api_key)
        self.llm = genai.GenerativeModel("gemini-2.5-flash")
        self.embedding_model = "models/text-embedding-004"

    async def ask(self, question: str) -> dict:
        """RAG-based Q&A over regulatory summaries."""
        return {"answer": "Not implemented yet.", "sources": []}
