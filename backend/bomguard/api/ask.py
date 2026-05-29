"""LLM Q&A endpoints (REST + WebSocket)."""

from typing import Any

from fastapi import APIRouter, WebSocket

router = APIRouter(prefix="/api/ask", tags=["Ask"])


@router.post("/")
async def ask_question(request: dict[str, Any]) -> dict[str, Any]:
    """Sync Q&A endpoint."""
    _ = request
    return {"answer": "Not implemented yet.", "sources": []}


@router.websocket("/ws")
async def ask_websocket(websocket: WebSocket) -> None:
    """Streaming WebSocket chat."""
    await websocket.accept()
    while True:
        _question = await websocket.receive_text()
        await websocket.send_json({"answer": "Not implemented yet."})
