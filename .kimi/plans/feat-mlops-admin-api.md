# Plan: Admin MLOps API

## Goal
Implement admin endpoints for model performance, drift detection, and retraining triggers.

## Scope
- `backend/bomguard/api/admin.py`
- `backend/bomguard/models/database.py` (`ml_model_performance`)
- Drift monitoring stubs

## Tasks
1. [ ] **Performance endpoint**: `GET /api/admin/ml/regulations/{id}/performance` returns latest metrics (ROC-AUC, AP, Brier, training date, promotion status) from `ml_model_performance`.
2. [ ] **Drift endpoint**: `GET /api/admin/ml/regulations/{id}/drift` compares recent `regulatory_changes` distribution against training baseline using Evidently AI; returns drift score + detected features.
3. [ ] **Retrain endpoint**: `POST /api/admin/ml/regulations/{id}/retrain` enqueues a Celery task that invokes the training pipeline; returns job ID.
4. [ ] **Stats endpoint**: `GET /api/admin/ml/stats` aggregates counts across regulations (trained models, pending changes, avg drift).
5. [ ] **Enrichment status**: Wire `GET /api/admin/enrich/status` to actual Celery task inspection (`celery_app.control.inspect`).
6. [ ] **Admin key check**: Ensure `X-Admin-API-Key` header validation on sensitive endpoints.
7. [ ] **Tests**: `tests/test_api/test_admin.py` mocking MLflow and Evidently.

## Dependencies
- `feat/ml-training-registry` (retrain must call real training code)
- Evidently AI package installed

## Outcome
Admin dashboard can view model health, detect drift, and trigger retraining.
