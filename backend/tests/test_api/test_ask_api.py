"""Tests for the LLM Q&A endpoints."""

from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from bomguard.config import Settings
from bomguard.main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app(Settings())
    return TestClient(app)


def test_ask_question_rest(client: TestClient) -> None:
    mock_result = {
        "answer": "Test answer",
        "sources": [
            {
                "id": 1,
                "substance_id": 1,
                "regulation_id": "eu_reach_svhc",
                "summary_text": "Summary text",
            }
        ],
    }

    with patch(
        "bomguard.api.ask.RegulatoryLLMService.ask", new_callable=AsyncMock
    ) as mock_ask:
        mock_ask.return_value = mock_result
        response = client.post("/api/ask/", json={"question": "What is REACH?"})
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Test answer"
        assert len(data["sources"]) == 1
        assert data["sources"][0]["regulation_id"] == "eu_reach_svhc"


def test_ask_question_empty(client: TestClient) -> None:
    response = client.post("/api/ask/", json={"question": ""})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "No question provided."
    assert data["sources"] == []


def test_ask_websocket(client: TestClient) -> None:
    async def mock_async_gen(*args, **kwargs):
        yield "Hello"

    with patch(
        "bomguard.api.ask.RegulatoryLLMService.ask_stream", new_callable=AsyncMock
    ) as mock_stream, patch(
        "bomguard.services.openrouter_client.OpenRouterClient.chat_stream",
        new=mock_async_gen,
    ):
        mock_stream.return_value = ("prompt", [])

        with client.websocket_connect("/api/ask/ws") as websocket:
            websocket.send_json({"question": "What is REACH?"})
            msg1 = websocket.receive_json()
            assert msg1["type"] == "token"
            assert msg1["content"] == "Hello"
            msg2 = websocket.receive_json()
            assert msg2["type"] == "sources"
            msg3 = websocket.receive_json()
            assert msg3["type"] == "done"
