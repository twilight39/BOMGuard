# Plan: BOM Upload & Parser (`feat/bom-upload`)

## Goal
Make the BOM upload endpoint actually parse and persist CSV/Excel files, and build the frontend pages for upload, list, and detail views.

## Current State

### Backend
- `POST /api/boms/upload` in `backend/bomguard/api/boms.py` accepts `UploadFile` but **ignores the content**. It returns a hardcoded fake response.
- `GET /api/boms` returns `[]`.
- `GET /api/boms/{bom_id}` returns a fake `BomSchema` with empty name.
- `BomSchema` in `backend/bomguard/models/schemas.py` exists but may be minimal.
- `Bom` model in `backend/bomguard/models/database.py` exists but check if it has a `parts` relationship.
- No CSV/Excel parsing logic exists.

### Frontend
- `frontend/src/pages/BomsPage.tsx` — likely a placeholder
- `frontend/src/routes/boms.index.tsx` — exists but may be minimal
- No upload component, no AG Grid table, no detail page
- API base URL is configured in `frontend/src/lib/api.ts` (or similar)

## Architecture Decisions (Already Made)
- FastAPI + SQLAlchemy 2.0 + Alembic on backend
- React 19 + TypeScript + Vite + TanStack Router + Tailwind v4 + shadcn/ui on frontend
- AG Grid for tables (decided in DECISIONS.md)
- Celery for async tasks

## Implementation Steps

### 1. Database Schema

Check the existing `Bom` and `BomPart` models in `backend/bomguard/models/database.py`.

If `BomPart` doesn't exist, add it:
```python
class BomPart(Base):
    __tablename__ = "bom_parts"
    id: Mapped[int] = mapped_column(primary_key=True)
    bom_id: Mapped[int] = mapped_column(ForeignKey("boms.id"))
    part_number: Mapped[str | None]
    manufacturer: Mapped[str | None]
    description: Mapped[str | None]
    cas_number: Mapped[str | None]  # if user provides it
    quantity: Mapped[int | None]
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
```

Generate Alembic migration:
```bash
cd backend && alembic revision --autogenerate -m "add bom_parts table"
```

### 2. Backend: CSV/Excel Parser

Create `backend/bomguard/services/bom_parser.py`:
- Use `pandas` for CSV/Excel reading
- Support `.csv`, `.xlsx`, `.xls`
- Auto-detect columns by fuzzy matching headers ("Part Number", "PartNumber", "PN", "Manufacturer", "Mfg", "CAS", "CAS Number", "Qty", "Quantity", etc.)
- Return `list[BomPartCreate]`
- Handle encoding issues (UTF-8, latin-1 fallback)
- Validate: reject empty files, files with > 10,000 rows (DoS protection)

### 3. Backend: Update Upload Endpoint

Refactor `POST /api/boms/upload` in `backend/bomguard/api/boms.py`:
1. Save uploaded file to a temp path
2. Parse with `bom_parser`
3. Create `Bom` row + `BomPart` rows in a transaction
4. Queue an async Celery scan task (or leave a TODO if scan branch isn't ready)
5. Return `BomSchema` with actual data

### 4. Backend: List & Detail Endpoints

Update `GET /api/boms`:
- Return paginated list of user's BOMs
- Include part count, scan status, created_at

Update `GET /api/boms/{bom_id}`:
- Return full BOM with parts list
- Include scan results if available

### 5. Frontend: Upload Page

Create or update `frontend/src/pages/BomsPage.tsx`:
- Drag-and-drop file upload zone (use shadcn/ui or native)
- Show upload progress / spinner
- Display parsing errors (invalid format, missing columns)
- On success, redirect to BOM detail page

### 6. Frontend: BOM List Page

Create `frontend/src/components/bom/BomList.tsx`:
- AG Grid table with columns: Name, Filename, Parts, Created, Status, Actions
- Actions: View, Delete, Re-scan
- Fetch from `GET /api/boms`

### 7. Frontend: BOM Detail Page

Create `frontend/src/pages/BomDetailPage.tsx` + route `frontend/src/routes/boms.$bomId.tsx`:
- Show BOM metadata (filename, uploaded date, part count)
- AG Grid table of parts (Part Number, Manufacturer, CAS, Quantity)
- Scan button if not yet scanned
- Scan results section (placeholder if scan branch isn't ready)

### 8. Tests

Backend:
- `test_bom_parser.py` — CSV parsing, column detection, Excel parsing, error cases
- `test_boms_api.py` — upload, list, detail, 404 cases

Frontend:
- Component tests for upload (if testing setup exists)

### 9. Lint / Type-Check / Test

```bash
cd backend && ruff check . && mypy . && basedpyright . && pytest tests/
cd frontend && npm run lint && npm run typecheck && npm run build
```

## Key Files to Create/Modify

| Action | File |
|--------|------|
| Create | `backend/bomguard/services/bom_parser.py` |
| Create | `backend/tests/test_boms/test_bom_parser.py` |
| Create | `backend/tests/test_boms/test_boms_api.py` |
| Create | `frontend/src/components/bom/BomList.tsx` |
| Create | `frontend/src/components/bom/BomUpload.tsx` |
| Create | `frontend/src/pages/BomDetailPage.tsx` |
| Create | `frontend/src/routes/boms.$bomId.tsx` |
| Modify | `backend/bomguard/models/database.py` (add BomPart if missing) |
| Modify | `backend/bomguard/models/schemas.py` (expand BomSchema) |
| Modify | `backend/bomguard/api/boms.py` (real upload/list/detail) |
| Modify | `frontend/src/pages/BomsPage.tsx` |
| Modify | `frontend/src/routes/boms.index.tsx` |

## Notes for Parallel Agent
- The auth branch (`feat/auth-workos`) may add a `user_id` column to the `Bom` model. If so, coordinate with that branch or leave a TODO comment.
- The scan branch (`feat/compliance-scan`) will consume BOM parts. Ensure the `BomPart` model has the fields the scanner needs (at minimum: `part_number`, `manufacturer`, `cas_number`, `description`).
- Keep the API response schema stable — the frontend will depend on it.
