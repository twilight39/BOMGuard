"""LLM Q&A endpoints (REST + WebSocket)."""

import logging
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from bomguard.db import get_db, SessionLocal
from bomguard.models.database import ChatMessage, ChatThread
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
    """Streaming WebSocket chat with thread persistence."""
    await websocket.accept()
    llm = RegulatoryLLMService()

    # Read user_id from session cookie via websocket scope
    user_id: str | None = None
    try:
        user_id = websocket.scope.get("session", {}).get("user_id")
    except Exception:
        pass

    try:
        while True:
            message = await websocket.receive_json()
            question = message.get("question", "")
            thread_id = message.get("thread_id")

            if not question:
                await websocket.send_json({"type": "error", "message": "No question provided."})
                continue

            db = SessionLocal()
            try:
                # Create thread if needed (authenticated users only)
                if user_id and thread_id is None:
                    thread = ChatThread(
                        user_id=user_id,
                        title=question[:50],
                    )
                    db.add(thread)
                    db.commit()
                    db.refresh(thread)
                    thread_id = thread.id
                    await websocket.send_json({"type": "thread", "thread_id": thread_id})

                # Verify thread ownership
                if thread_id is not None and user_id:
                    thread = db.query(ChatThread).filter(ChatThread.id == thread_id).first()
                    if not thread or thread.user_id != user_id:
                        await websocket.send_json(
                            {"type": "error", "message": "Thread not found or not authorized."}
                        )
                        continue

                # Enforce 50-message max per thread
                if thread_id is not None:
                    msg_count = (
                        db.query(ChatMessage)
                        .filter(ChatMessage.thread_id == thread_id)
                        .count()
                    )
                    if msg_count >= 50:
                        await websocket.send_json(
                            {
                                "type": "error",
                                "message": "Thread limit exceeded (50 messages). Start a new chat.",
                            }
                        )
                        continue

                # Load previous messages for conversation history
                history: list[dict[str, str]] = []
                if thread_id is not None:
                    prev_messages = (
                        db.query(ChatMessage)
                        .filter(ChatMessage.thread_id == thread_id)
                        .order_by(ChatMessage.created_at.asc())
                        .all()
                    )
                    # Cap context at last 6 messages for LLM
                    for m in prev_messages[-6:]:
                        history.append({"role": m.role, "content": m.content})

                # Store user message
                if thread_id is not None:
                    db.add(
                        ChatMessage(
                            thread_id=thread_id,
                            role="user",
                            content=question,
                        )
                    )
                    db.commit()

                # Build prompt with history and stream
                messages, summaries = await llm.ask_stream(db, question, history=history)
                assistant_content = ""
                async for token in llm.openrouter.chat_stream(messages=messages):
                    await websocket.send_json({"type": "token", "content": token})
                    assistant_content += token

                sources = [
                    {
                        "id": s.id,
                        "substance_id": s.substance_id,
                        "regulation_id": s.regulation_id,
                        "summary_text": s.summary_text,
                    }
                    for s in summaries
                ]

                await websocket.send_json({"type": "sources", "sources": sources})
                await websocket.send_json({"type": "done"})

                # Store assistant message
                if thread_id is not None:
                    db.add(
                        ChatMessage(
                            thread_id=thread_id,
                            role="assistant",
                            content=assistant_content,
                            sources=sources,
                        )
                    )
                    db.commit()
            finally:
                db.close()
    except WebSocketDisconnect:
        pass
    except Exception as exc:
        logger.exception("WebSocket error")
        await websocket.send_json(
            {"type": "error", "message": "An error occurred. Please try again."}
        )
        await websocket.close()
