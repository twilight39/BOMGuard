"""Compliance scanning endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from bomguard.db import get_db
from bomguard.models.database import Bom, ScanResult
from bomguard.models.schemas import ScanResultSchema
from bomguard.services.compliance_scanner import ComplianceScanner

router = APIRouter(prefix="/api/scan", tags=["Scan"])


@router.post("/{bom_id}")
async def trigger_scan(
    bom_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Trigger a compliance scan for a BOM."""
    user_id = request.session.get("user_id")
    bom = db.query(Bom).filter(Bom.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")
    if user_id and bom.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to scan this BOM")

    scanner = ComplianceScanner(db)
    hits = scanner.scan_bom(bom_id)

    return {
        "bom_id": bom_id,
        "status": "completed",
        "hits_found": len(hits),
        "compliance_status": bom.compliance_status,
    }


@router.get("/{bom_id}/status")
async def scan_status(
    bom_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Get scan status for a BOM."""
    user_id = request.session.get("user_id")
    bom = db.query(Bom).filter(Bom.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")
    if user_id and bom.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    hit_count = db.query(ScanResult).filter(ScanResult.bom_id == bom_id).count()
    return {
        "bom_id": bom_id,
        "compliance_status": bom.compliance_status,
        "hits_found": hit_count,
    }


@router.get("/{bom_id}/result", response_model=list[ScanResultSchema])
async def scan_result(
    bom_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> list[ScanResultSchema]:
    """Get full scan results for a BOM."""
    user_id = request.session.get("user_id")
    bom = db.query(Bom).filter(Bom.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")
    if user_id and bom.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    results = (
        db.query(ScanResult)
        .filter(ScanResult.bom_id == bom_id)
        .order_by(ScanResult.severity.desc(), ScanResult.cas_number)
        .all()
    )
    return [ScanResultSchema.model_validate(r) for r in results]
