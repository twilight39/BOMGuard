# Plan: Frontend Page Components

## Goal
Replace placeholder directories with working page-level components.

## Scope
- `frontend/src/components/scan-result/`
- `frontend/src/components/regulatory-feed/`
- `frontend/src/components/ai-assistant/` (dedicated page view beyond chat modal)
- `frontend/src/components/ml-dashboard/`
- `frontend/src/components/upload/` (enhancements)
- `frontend/src/pages/` (add new TanStack routes)

## Tasks
1. [ ] **Scan Result Page**: Full-screen scan breakdown with AG Grid part list, per-regulation risk badges, and CAS detail drawer.
2. [ ] **Regulatory Feed Page**: Timeline view of `regulatory_changes` with filtering by regulation and date range.
3. [ ] **AI Assistant Page**: Standalone chat page (not modal) with thread history sidebar, markdown rendering, and source citations.
4. [ ] **ML Dashboard Page**: Admin-only view showing per-regulation model cards (ROC-AUC, drift status), SHAP example viewer, and retrain button.
5. [ ] **Upload Enhancements**: Drag-and-drop zone, progress bar, preview first 10 rows, fuzzy header mapping confirmation.
6. [ ] **Routing**: Add file-based routes in `src/routes/` for new pages; run `npm run generate-routes`.
7. [ ] **Navigation**: Update `AppShell.tsx` sidebar/menu with new links and role-based visibility (admin vs public).
8. [ ] **API types**: Extend `services/api.ts` with new endpoints (admin, shap, etc.).

## Dependencies
- Backend endpoints should exist or be stubbed with 501 responses so the frontend can be developed in parallel.

## Outcome
All placeholder directories contain real components; app navigation includes dedicated pages for scan results, regulatory feed, AI assistant, and ML dashboard.
