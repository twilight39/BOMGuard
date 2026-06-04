"""Compliance scanning endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from bomguard.db import get_db
from bomguard.models.database import Bom, BomPart, ScanResult
from bomguard.models.schemas import ScanResultDetailSchema
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
    if bom.user_id is not None and bom.user_id != user_id:
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
    if bom.user_id is not None and bom.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    hit_count = db.query(ScanResult).filter(ScanResult.bom_id == bom_id).count()
    return {
        "bom_id": bom_id,
        "compliance_status": bom.compliance_status,
        "hits_found": hit_count,
    }


@router.get("/{bom_id}/result", response_model=list[ScanResultDetailSchema])
async def scan_result(
    bom_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> list[ScanResultDetailSchema]:
    """Get full scan results for a BOM."""
    user_id = request.session.get("user_id")
    bom = db.query(Bom).filter(Bom.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found")
    if bom.user_id is not None and bom.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized")

    rows = (
        db.query(ScanResult, BomPart)
        .outerjoin(BomPart, ScanResult.part_id == BomPart.id)
        .filter(ScanResult.bom_id == bom_id)
        .order_by(ScanResult.severity.desc(), ScanResult.cas_number)
        .all()
    )

    return [
        ScanResultDetailSchema(
            id=sr.id,
            bom_id=sr.bom_id,
            part_id=sr.part_id,
            regulation_id=sr.regulation_id,
            cas_number=sr.cas_number,
            hit_type=sr.hit_type,
            risk_score=sr.risk_score,
            severity=sr.severity,
            details=sr.details,
            part_number=bp.part_number if bp else None,
            part_description=bp.description if bp else None,
        )
        for sr, bp in rows
    ]
