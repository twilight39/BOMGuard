"""Compliance scanning endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from bomguard.db import get_db
from bomguard.models.schemas import ScanResultSchema

router = APIRouter(prefix="/api/scan", tags=["Scan"])


@router.post("/{bom_id}")
async def trigger_scan(bom_id: int, db: Session = Depends(get_db)) -> dict:
    """Trigger a compliance scan for a BOM."""
    return {"bom_id": bom_id, "status": "queued"}


@router.get("/{bom_id}/status")
async def scan_status(bom_id: int, db: Session = Depends(get_db)) -> dict:
    """Get scan progress (0-100%)."""
    return {"bom_id": bom_id, "progress": 0}


@router.get("/{bom_id}/result", response_model=list[ScanResultSchema])
async def scan_result(bom_id: int, db: Session = Depends(get_db)) -> list[ScanResultSchema]:
    """Get full scan results."""
    return []
