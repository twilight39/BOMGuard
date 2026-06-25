"""LLM Q&A endpoints (REST + WebSocket)."""

from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.orm import Session

from bomguard.db import SessionLocal, get_db
from bomguard.metrics import llm_queries_total
from bomguard.models.database import ChatMessage, ChatThread, ScanResult, Substance
from bomguard.services.llm_service import RegulatoryLLMService

router = APIRouter(prefix="/api/ask", tags=["Ask"])


def get_llm_service() -> RegulatoryLLMService:
    """Dependency factory for the LLM service."""
    return RegulatoryLLMService()


def _load_ml_alerts(db: Session, bom_id: Any) -> list[dict[str, Any]]:
    """Load ML-predicted high/medium risk substances for a BOM."""
    if bom_id is None:
        return []
    try:
        bom_id_int = int(bom_id)
    except (TypeError, ValueError):
        return []
    rows = (
        db.query(ScanResult, Substance)
        .join(Substance, ScanResult.cas_number == Substance.cas_number)
        .filter(ScanResult.bom_id == bom_id_int)
        .filter(ScanResult.hit_type == "ml_risk_prediction")
        .filter(ScanResult.ml_risk_tier.in_(["high", "medium"]))
        .all()
    )
    return [
        {
            "cas_number": sr.cas_number,
            "substance_name": substance.name,
            "regulation_id": sr.regulation_id,
            "risk_score": sr.ml_risk_score,
            "risk_tier": sr.ml_risk_tier,
        }
        for sr, substance in rows
        if sr.cas_number is not None
    ]


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
    llm_queries_total.labels(type="rest").inc()
    ml_alerts = _load_ml_alerts(db, request.get("bom_id"))
    return await llm.ask(db, question, ml_alerts=ml_alerts)


@router.websocket("/ws")
async def ask_websocket(websocket: WebSocket) -> None:
    """Streaming WebSocket chat with thread persistence."""
    await websocket.accept()
    llm = RegulatoryLLMService()

    # Read user_id from session cookie via websocket scope
    user_id: str | None = websocket.scope.get("session", {}).get("user_id")

    try:
        while True:
            message = await websocket.receive_json()
            question = message.get("question", "")
            thread_id = message.get("thread_id")

            if not question:
                await websocket.send_json({"type": "error", "message": "No question provided."})
                continue

            llm_queries_total.labels(type="websocket").inc()

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
                    existing_thread = (
                        db.query(ChatThread).filter(ChatThread.id == thread_id).first()
                    )
                    if not existing_thread or existing_thread.user_id != user_id:
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
                ml_alerts = _load_ml_alerts(db, message.get("bom_id"))
                messages, summaries = await llm.ask_stream(
                    db, question, history=history, ml_alerts=ml_alerts
                )
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
    except Exception:
        await websocket.send_json(
            {"type": "error", "message": "An error occurred. Please try again."}
        )
        await websocket.close()
