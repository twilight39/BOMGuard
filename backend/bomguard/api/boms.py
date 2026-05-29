"""BOM upload, list, and delete endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, UploadFile
from sqlalchemy.orm import Session

from bomguard.db import get_db
from bomguard.models.schemas import BomSchema, BomUploadResponse

router = APIRouter(prefix="/api/boms", tags=["BOMs"])


@router.post("/upload", response_model=BomUploadResponse)
async def upload_bom(file: UploadFile, db: Session = Depends(get_db)) -> BomUploadResponse:
    """Upload a BOM file (CSV or XLSX)."""
    _ = db
    return BomUploadResponse(id=1, filename=file.filename or "unknown", status="pending")


@router.get("/", response_model=list[BomSchema])
async def list_boms(db: Session = Depends(get_db)) -> list[BomSchema]:
    """List all uploaded BOMs."""
    _ = db
    return []


@router.get("/{bom_id}", response_model=BomSchema)
async def get_bom(bom_id: int, db: Session = Depends(get_db)) -> BomSchema:
    """Get BOM metadata and status."""
    _ = db
    return BomSchema(
        id=bom_id,
        name="",
        source_type="upload",
        total_parts=0,
        compliance_status="pending",
    )


@router.delete("/{bom_id}")
async def delete_bom(bom_id: int, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Delete a BOM."""
    _ = db
    return {"id": bom_id, "deleted": True}
