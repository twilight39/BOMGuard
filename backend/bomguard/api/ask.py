"""LLM Q&A endpoints (REST + WebSocket)."""

from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from bomguard.db import get_db
from bomguard.services.llm_service import RegulatoryLLMService

router = APIRouter(prefix="/api/ask", tags=["Ask"])


def get_llm_service() -> RegulatoryLLMService:
    """Dependency factory for the LLM service."""
    return RegulatoryLLMService()


@router.post("/")
async def ask_question(
    request: dict[str, Any],
    db: Session = Depends(get_db),
    llm: RegulatoryLLMService = Depends(get_llm_service),
) -> dict[str, Any]:
    """Sync Q&A endpoint."""
    question = request.get("question", "")
    if not question:
        return {"answer": "No question provided.", "sources": []}
    return await llm.ask(db, question)


@router.websocket("/ws")
async def ask_websocket(websocket: WebSocket) -> None:
    """Streaming WebSocket chat."""
    await websocket.accept()
    llm = RegulatoryLLMService()
    try:
        while True:
            message = await websocket.receive_json()
            question = message.get("question", "")
            if not question:
                await websocket.send_json({"error": "No question provided."})
                continue

            # We need a DB session for the RAG pipeline
            from bomguard.db import SessionLocal

            db = SessionLocal()
            try:
                prompt, summaries = await llm.ask_stream(db, question)
                async for token in llm.openrouter.chat_stream(
                    messages=[{"role": "user", "content": prompt}]
                ):
                    await websocket.send_json({"type": "token", "content": token})

                await websocket.send_json({
                    "type": "sources",
                    "sources": [
                        {
                            "id": s.id,
                            "substance_id": s.substance_id,
                            "regulation_id": s.regulation_id,
                            "summary_text": s.summary_text,
                        }
                        for s in summaries
                    ],
                })
                await websocket.send_json({"type": "done"})
            finally:
                db.close()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        await websocket.send_json({"type": "error", "message": str(exc)})
        await websocket.close()
