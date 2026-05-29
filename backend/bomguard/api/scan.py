"""Compliance scanning endpoints."""

from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from bomguard.db import get_db
from bomguard.models.schemas import ScanResultSchema

router = APIRouter(prefix="/api/scan", tags=["Scan"])


@router.post("/{bom_id}")
async def trigger_scan(bom_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Trigger a compliance scan for a BOM."""
    _ = db
    return {"bom_id": bom_id, "status": "queued"}


@router.get("/{bom_id}/status")
async def scan_status(bom_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Get scan progress (0-100%)."""
    _ = db
    return {"bom_id": bom_id, "progress": 0}


@router.get("/{bom_id}/result", response_model=list[ScanResultSchema])
async def scan_result(bom_id: int, db: Session = Depends(get_db)) -> list[ScanResultSchema]:
    """Get full scan results."""
    _ = db
    _ = bom_id
    return []
