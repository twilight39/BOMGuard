"""Compliance scanning endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy import func
from sqlalchemy.orm import Session

from bomguard.db import get_db
from bomguard.metrics import scans_total
from bomguard.models.database import Bom, BomPart, ScanResult
from bomguard.models.schemas import ScanResultDetailSchema
from bomguard.services.compliance_scanner import ComplianceScanner

router = APIRouter(prefix="/api/scan", tags=["Scan"])


@router.get("/recent")
async def recent_scans(
    request: Request,
    db: Session = Depends(get_db),
    limit: int = 10,
) -> list[dict[str, Any]]:
    """Recent BOMs with scan results, ordered by most recent scan."""
    user_id = request.session.get("user_id")

    # Subquery: max scan result timestamp per BOM
    latest_scan = (
        db.query(ScanResult.bom_id, func.max(ScanResult.created_at).label("scanned_at"))
        .group_by(ScanResult.bom_id)
        .subquery()
    )

    # Hit count per BOM
    hit_counts = (
        db.query(ScanResult.bom_id, func.count(ScanResult.id).label("hit_count"))
        .group_by(ScanResult.bom_id)
        .subquery()
    )

    query = (
        db.query(Bom, latest_scan.c.scanned_at, hit_counts.c.hit_count)
        .join(latest_scan, Bom.id == latest_scan.c.bom_id)
        .outerjoin(hit_counts, Bom.id == hit_counts.c.bom_id)
        .order_by(latest_scan.c.scanned_at.desc())
        .limit(limit)
    )

    # Filter by user if authenticated (include public BOMs too)
    if user_id:
        query = query.filter((Bom.user_id == user_id) | (Bom.user_id.is_(None)))
    else:
        query = query.filter(Bom.user_id.is_(None))

    results = query.all()

    return [
        {
            "bom_id": bom.id,
            "bom_name": bom.name,
            "compliance_status": bom.compliance_status,
            "hits_found": hit_count or 0,
            "scanned_at": scanned_at.isoformat() if scanned_at else None,
        }
        for bom, scanned_at, hit_count in results
    ]


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
    try:
        hits = scanner.scan_bom(bom_id)
        scans_total.labels(status="completed").inc()
    except Exception:
        scans_total.labels(status="failed").inc()
        raise

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
