"""Compliance scanning endpoints."""

from fastapi import APIRouter

router = APIRouter(prefix="/api/scan", tags=["Scan"])


@router.post("/{bom_id}")
async def trigger_scan(bom_id: int) -> dict:
    """Trigger a compliance scan for a BOM."""
    return {"bom_id": bom_id, "status": "queued"}


@router.get("/{bom_id}/status")
async def scan_status(bom_id: int) -> dict:
    """Get scan progress (0-100%)."""
    return {"bom_id": bom_id, "progress": 0}


@router.get("/{bom_id}/result")
async def scan_result(bom_id: int) -> dict:
    """Get full scan results."""
    return {"bom_id": bom_id, "results": []}
