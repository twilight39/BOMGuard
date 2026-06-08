"""OpenRouter API client with streaming and retry support."""

import logging
from collections.abc import AsyncIterator
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class OpenRouterClient:
    """Async client for OpenRouter's OpenAI-compatible chat API."""

    BASE_URL = "https://openrouter.ai/api/v1"

    def __init__(
        self,
        api_key: str,
        http_referer: str = "http://localhost:5173",
        x_title: str = "BOMGuard",
    ) -> None:
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": http_referer,
            "X-Title": x_title,
        }

    async def chat(
        self,
        messages: list[dict[str, str]],
        model: str = "~google/gemini-flash-latest",
        temperature: float = 0.3,
        max_retries: int = 3,
    ) -> str:
        """Send a non-streaming chat request."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": False,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            for attempt in range(max_retries):
                response = await client.post(
                    f"{self.BASE_URL}/chat/completions",
                    headers=self.headers,
                    json=payload,
                )
                if response.status_code == 429:
                    import asyncio

                    wait = 2**attempt
                    await asyncio.sleep(wait)
                    continue
                if response.status_code >= 400:
                    logger.error(
                        "OpenRouter chat error: %s %s — %s",
                        response.status_code,
                        response.reason_phrase,
                        response.text,
                    )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                return str(data["choices"][0]["message"]["content"])

        raise RuntimeError("OpenRouter chat failed after retries")

    async def embed(
        self,
        text: str,
        model: str = "google/gemini-embedding-001",
        dimensions: int = 768,
        max_retries: int = 3,
    ) -> list[float]:
        """Generate embeddings via OpenRouter's OpenAI-compatible endpoint."""
        payload: dict[str, Any] = {
            "model": model,
            "input": text,
            "dimensions": dimensions,
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            for attempt in range(max_retries):
                response = await client.post(
                    f"{self.BASE_URL}/embeddings",
                    headers=self.headers,
                    json=payload,
                )
                if response.status_code == 429:
                    import asyncio

                    wait = 2**attempt
                    await asyncio.sleep(wait)
                    continue
                if response.status_code >= 400:
                    logger.error(
                        "OpenRouter embed error: %s %s — %s",
                        response.status_code,
                        response.reason_phrase,
                        response.text,
                    )
                response.raise_for_status()
                data: dict[str, Any] = response.json()
                embedding: list[float] = data["data"][0]["embedding"]
                return embedding

        raise RuntimeError("OpenRouter embed failed after retries")

    async def chat_stream(
        self,
        messages: list[dict[str, str]],
        model: str = "~google/gemini-flash-latest",
        temperature: float = 0.3,
    ) -> AsyncIterator[str]:
        """Send a streaming chat request and yield text deltas."""
        payload: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }

        async with (
            httpx.AsyncClient(timeout=60.0) as client,
            client.stream(
                "POST",
                f"{self.BASE_URL}/chat/completions",
                headers=self.headers,
                json=payload,
            ) as response,
        ):
            try:
                status_code = int(response.status_code)
            except (TypeError, ValueError):
                status_code = 0
            if status_code >= 400:
                body = await response.aread()
                logger.error(
                    "OpenRouter stream error: %s %s — %s",
                    status_code,
                    response.reason_phrase,
                    body.decode() if body else "",
                )
            response.raise_for_status()
            async for line in response.aiter_lines():
                line = line.strip()
                if not line or not line.startswith("data: "):
                    continue
                data = line[len("data: ") :]
                if data == "[DONE]":
                    break
                try:
                    import json

                    chunk = json.loads(data)
                    delta = chunk["choices"][0]["delta"]
                    if "content" in delta and delta["content"]:
                        yield delta["content"]
                except (json.JSONDecodeError, KeyError, IndexError):
                    continue
