"""Regulatory data endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/regulations", tags=["Regulations"])


@router.get("/")
async def list_regulations() -> list[dict]:
    """List all active regulations."""
    return []


@router.get("/{regulation_id}")
async def get_regulation(regulation_id: str) -> dict:
    """Get regulation details and ML status."""
    return {"id": regulation_id}


@router.get("/feed")
async def regulatory_feed() -> list[dict]:
    """Recent regulatory changes."""
    return []
