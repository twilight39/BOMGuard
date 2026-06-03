"""Chat thread and message endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from bomguard.db import get_db
from bomguard.models.database import ChatMessage, ChatThread

router = APIRouter(prefix="/api/chat", tags=["Chat"])


@router.get("/threads")
async def list_threads(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = 20,
) -> list[dict[str, Any]]:
    """List current user's chat threads."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    threads = (
        db.query(ChatThread)
        .filter(ChatThread.user_id == user_id)
        .order_by(ChatThread.updated_at.desc())
        .limit(limit)
        .all()
    )

    return [
        {
            "id": t.id,
            "title": t.title,
            "created_at": t.created_at.isoformat() if t.created_at else None,
            "updated_at": t.updated_at.isoformat() if t.updated_at else None,
        }
        for t in threads
    ]


@router.post("/threads")
async def create_thread(
    request: Request,
    db: Session = Depends(get_db),
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a new chat thread."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    title = (body or {}).get("title")
    thread = ChatThread(user_id=user_id, title=title)
    db.add(thread)
    db.commit()
    db.refresh(thread)

    return {
        "id": thread.id,
        "title": thread.title,
        "created_at": thread.created_at.isoformat() if thread.created_at else None,
        "updated_at": thread.updated_at.isoformat() if thread.updated_at else None,
    }


@router.get("/threads/{thread_id}/messages")
async def get_messages(
    thread_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> list[dict[str, Any]]:
    """Get all messages in a thread."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    thread = db.query(ChatThread).filter(ChatThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if thread.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    messages = (
        db.query(ChatMessage)
        .filter(ChatMessage.thread_id == thread_id)
        .order_by(ChatMessage.created_at.asc())
        .all()
    )

    return [
        {
            "id": m.id,
            "role": m.role,
            "content": m.content,
            "sources": m.sources,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        }
        for m in messages
    ]


@router.post("/threads/{thread_id}/sync")
async def sync_messages(
    thread_id: int,
    request: Request,
    db: Session = Depends(get_db),
    body: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Bulk-import messages from an anonymous session."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    thread = db.query(ChatThread).filter(ChatThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if thread.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    messages = (body or {}).get("messages", [])
    for msg in messages:
        db.add(
            ChatMessage(
                thread_id=thread_id,
                role=msg.get("role", "user"),
                content=msg.get("content", ""),
                sources=msg.get("sources"),
            )
        )

    db.commit()
    return {"synced": len(messages)}


@router.delete("/threads/{thread_id}")
async def delete_thread(
    thread_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Delete a chat thread and all its messages."""
    user_id = request.session.get("user_id")
    if not user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")

    thread = db.query(ChatThread).filter(ChatThread.id == thread_id).first()
    if not thread:
        raise HTTPException(status_code=404, detail="Thread not found")
    if thread.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    db.delete(thread)
    db.commit()
    return {"status": "deleted"}
