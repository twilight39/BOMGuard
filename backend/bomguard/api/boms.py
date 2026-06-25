"""BOM upload, list, and delete endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, UploadFile
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from bomguard.db import get_db
from bomguard.enrichment.tasks import enrich_substance
from bomguard.metrics import bom_uploads_total
from bomguard.models.database import Bom, BomPart, ScanResult, Substance
from bomguard.models.schemas import (
    BomDetailSchema,
    BomSchema,
    BomUploadResponse,
)
from bomguard.seed import SAMPLE_MAP, load_sample_bom
from bomguard.services.bom_parser import parse_bom
from bomguard.services.bom_substances import sync_bom_substances

router = APIRouter(prefix="/api/boms", tags=["BOMs"])


@router.post("/upload", response_model=BomUploadResponse)
async def upload_bom(
    file: UploadFile,
    request: Request,
    db: Session = Depends(get_db),
) -> BomUploadResponse:
    """Upload a BOM file (CSV or XLSX)."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="Filename is required.")

    user_id = request.session.get("user_id")

    contents = await file.read()
    try:
        parts = parse_bom(contents, file.filename)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Ensure CAS numbers referenced by the BOM are tracked as substances.
    # These become negative training examples for all regulations.
    new_substances = sync_bom_substances(db, parts)
    for substance in new_substances:
        enrich_substance.delay(substance.id)

    name = file.filename.rsplit(".", 1)[0]
    file_format = file.filename.rsplit(".", 1)[-1].lower() if "." in file.filename else None

    bom = Bom(
        name=name,
        source_type="upload",
        file_format=file_format,
        total_parts=len(parts),
        compliance_status="pending",
        user_id=user_id,
    )
    db.add(bom)
    db.flush()  # Get bom.id

    for parsed in parts:
        bom_part = BomPart(
            bom_id=bom.id,
            line_number=parsed.line_number,
            part_number=parsed.part_number,
            description=parsed.description,
            manufacturer=parsed.manufacturer,
            supplier=parsed.supplier,
            quantity=parsed.quantity,
            unit=parsed.unit or "pcs",
            cas_numbers=parsed.cas_numbers,
        )
        db.add(bom_part)

    db.commit()

    bom_uploads_total.labels(source="upload").inc()
    return BomUploadResponse(id=bom.id, filename=file.filename, status="pending")


@router.post("/samples/{sample_id}", response_model=BomSchema)
async def load_sample(
    sample_id: str,
    request: Request,
    db: Session = Depends(get_db),
) -> BomSchema:
    """Load a pre-built sample BOM into the current user's account."""
    if sample_id not in SAMPLE_MAP:
        raise HTTPException(status_code=404, detail=f"Unknown sample: {sample_id}")

    user_id = request.session.get("user_id")
    try:
        bom = load_sample_bom(db, sample_id, user_id=user_id)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc

    # Enrich any new substances created from the sample BOM's CAS numbers.
    for part in bom.parts:
        if not part.cas_numbers:
            continue
        for cas in part.cas_numbers.split("|"):
            cas = cas.strip()
            if not cas:
                continue
            substance = db.query(Substance).filter_by(cas_number=cas).first()
            if substance:
                enrich_substance.delay(substance.id)

    bom_uploads_total.labels(source="sample").inc()
    return BomSchema.model_validate(bom)


@router.get("/samples", response_model=list[dict[str, str]])
async def list_samples() -> list[dict[str, str]]:
    """List available sample BOMs."""
    return [
        {"id": sid, "name": name, "filename": filename}
        for sid, (filename, name) in SAMPLE_MAP.items()
    ]


@router.get("/", response_model=list[BomSchema])
async def list_boms(
    request: Request,
    db: Session = Depends(get_db),
) -> list[BomSchema]:
    """List current user's BOMs ordered by creation date descending."""
    user_id = request.session.get("user_id")
    query = db.query(Bom)
    query = (
        query.filter(Bom.user_id == user_id)
        if user_id
        else query.filter(Bom.user_id.is_(None))
    )
    boms = query.order_by(Bom.created_at.desc()).all()

    # Attach hit counts
    if boms:
        bom_ids = [b.id for b in boms]
        hit_counts = {
            row.bom_id: row.cnt
            for row in db.query(ScanResult.bom_id, func.count().label("cnt"))
            .filter(ScanResult.bom_id.in_(bom_ids))
            .group_by(ScanResult.bom_id)
            .all()
        }
        return [
            BomSchema.model_validate(b).model_copy(update={"hit_count": hit_counts.get(b.id, 0)})
            for b in boms
        ]

    return []


@router.get("/{bom_id}", response_model=BomDetailSchema)
async def get_bom(
    bom_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> BomDetailSchema:
    """Get BOM metadata and parts."""
    user_id = request.session.get("user_id")
    bom = (
        db.query(Bom)
        .options(joinedload(Bom.parts))
        .filter(Bom.id == bom_id)
        .first()
    )
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found.")
    if bom.user_id is not None and bom.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to view this BOM.")
    return BomDetailSchema.model_validate(bom)


@router.delete("/{bom_id}")
async def delete_bom(
    bom_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Delete a BOM and its parts."""
    user_id = request.session.get("user_id")
    bom = db.query(Bom).filter(Bom.id == bom_id).first()
    if not bom:
        raise HTTPException(status_code=404, detail="BOM not found.")
    if bom.user_id is not None and bom.user_id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to delete this BOM.")
    db.delete(bom)
    db.commit()
    return {"id": bom_id, "deleted": True}
