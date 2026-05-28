"""BOM upload, list, and delete endpoints."""

from fastapi import APIRouter, UploadFile

router = APIRouter(prefix="/api/boms", tags=["BOMs"])


@router.post("/upload")
async def upload_bom(file: UploadFile) -> dict:
    """Upload a BOM file (CSV or XLSX)."""
    return {"filename": file.filename, "status": "pending"}


@router.get("/")
async def list_boms() -> list[dict]:
    """List all uploaded BOMs."""
    return []


@router.get("/{bom_id}")
async def get_bom(bom_id: int) -> dict:
    """Get BOM metadata and status."""
    return {"id": bom_id, "status": "pending"}


@router.delete("/{bom_id}")
async def delete_bom(bom_id: int) -> dict:
    """Delete a BOM."""
    return {"id": bom_id, "deleted": True}
