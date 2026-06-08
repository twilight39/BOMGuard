"""Tests for the OpenRouter client."""

from collections.abc import AsyncIterator
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from bomguard.services.openrouter_client import OpenRouterClient


@pytest.fixture
def client() -> OpenRouterClient:
    return OpenRouterClient(api_key="test-key")


@pytest.mark.asyncio
async def test_chat_success(client: OpenRouterClient) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "choices": [{"message": {"content": "Hello from OpenRouter"}}]
    }
    mock_response.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(return_value=mock_response)

    with patch("httpx.AsyncClient", return_value=mock_client):
        result = await client.chat(messages=[{"role": "user", "content": "Hi"}])
        assert result == "Hello from OpenRouter"


@pytest.mark.asyncio
async def test_chat_retry_on_429(client: OpenRouterClient) -> None:
    mock_response_429 = MagicMock()
    mock_response_429.status_code = 429

    mock_response_200 = MagicMock()
    mock_response_200.status_code = 200
    mock_response_200.json.return_value = {
        "choices": [{"message": {"content": "Success after retry"}}]
    }
    mock_response_200.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.post = AsyncMock(side_effect=[mock_response_429, mock_response_200])

    with patch("httpx.AsyncClient", return_value=mock_client), patch(
        "asyncio.sleep", new=AsyncMock()
    ):
        result = await client.chat(messages=[{"role": "user", "content": "Hi"}])
        assert result == "Success after retry"


@pytest.mark.asyncio
async def test_chat_stream(client: OpenRouterClient) -> None:
    lines = [
        'data: {"choices": [{"delta": {"content": "Hello "}}]}',
        'data: {"choices": [{"delta": {"content": "world"}}]}',
        "data: [DONE]",
    ]

    mock_stream = MagicMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=None)
    mock_stream.raise_for_status = MagicMock()

    async def mock_aiter_lines() -> AsyncIterator[str]:
        for line in lines:
            yield line

    mock_stream.aiter_lines = mock_aiter_lines

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.stream = MagicMock(return_value=mock_stream)

    with patch("httpx.AsyncClient", return_value=mock_client):
        tokens = []
        async for token in client.chat_stream(messages=[{"role": "user", "content": "Hi"}]):
            tokens.append(token)
        assert tokens == ["Hello ", "world"]


@pytest.mark.asyncio
async def test_chat_stream_ignores_invalid_lines(client: OpenRouterClient) -> None:
    lines = [
        "",
        "data: not-json",
        'data: {"choices": [{"delta": {"content": "ok"}}]}',
        "data: [DONE]",
    ]

    mock_stream = MagicMock()
    mock_stream.__aenter__ = AsyncMock(return_value=mock_stream)
    mock_stream.__aexit__ = AsyncMock(return_value=None)
    mock_stream.raise_for_status = MagicMock()

    async def mock_aiter_lines() -> AsyncIterator[str]:
        for line in lines:
            yield line

    mock_stream.aiter_lines = mock_aiter_lines

    mock_client = MagicMock()
    mock_client.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client.__aexit__ = AsyncMock(return_value=None)
    mock_client.stream = MagicMock(return_value=mock_stream)

    with patch("httpx.AsyncClient", return_value=mock_client):
        tokens = []
        async for token in client.chat_stream(messages=[{"role": "user", "content": "Hi"}]):
            tokens.append(token)
        assert tokens == ["ok"]
