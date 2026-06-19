# Plan: E2E Integration & Polish

## Goal
Validate the full Docker Compose stack end-to-end and fix integration gaps.

## Scope
- `docker-compose.yml`
- `docker-compose.test.yml`
- Full-stack manual QA script
- Performance / security hardening

## Tasks
1. [ ] **Stack smoke test**: `docker compose up --build -d`; verify all health endpoints return 200.
2. [ ] **Upload → scan flow**: Upload `samples/smartphone_pcb_bom.csv` and confirm scan completes with expected restricted substances.
3. [ ] **Auth flow**: WorkOS login → callback → session cookie → logout; verify protected admin routes.
4. [ ] **Chat flow**: Send RAG question via WebSocket; verify streaming tokens and sources.
5. [ ] **Celery flow**: Trigger regulation refresh from admin; verify tasks complete and DB updates.
6. [ ] **MLflow flow**: Train a model manually; verify metrics appear in MLflow UI.
7. [ ] **Data seeding**: Ensure `seed.py` runs cleanly on fresh DB and populates all 5 regulations + sample BOMs.
8. [ ] **Performance**: Add DB connection pooling review; ensure N+1 queries are eliminated in `/api/boms/{id}/parts`.
9. [ ] **Security**: Verify `ADMIN_API_KEY` check on enrichment; confirm Traefik rate limiting headers.
10. [ ] **Documentation**: Update `README.md` quickstart if any env vars or ports changed.

## Dependencies
- All feature branches merged into `main`

## Outcome
Production stack is stable, performant, and documented for demo use.
