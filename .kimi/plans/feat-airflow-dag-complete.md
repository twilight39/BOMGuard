# Plan: Airflow DAG Completion

## Goal
Replace skeleton no-op tasks with real callable logic in the weekly risk model pipeline.

## Scope
- `airflow/dags/risk_model_pipeline.py`

## Tasks
1. [ ] **Task 1 — `refresh_substances`**: Call ECHA scraper + static scrapers; insert new substances / hashes.
2. [ ] **Task 2 — `enrich_features`**: Trigger Celery batch enrichment for substances missing `substance_properties`.
3. [ ] **Task 3 — `train_reach_model`**: Call `ml.models.train.train_regulation_model('eu_reach_svhc')`.
4. [ ] **Task 4 — `train_pfas_model`**: Call `ml.models.train.train_regulation_model('us_state_pfas')`.
5. [ ] **Task 5 — `evaluate`**: Compare newly trained model against current production model on holdout; log metrics.
6. [ ] **Task 6 — `promote`**: If new model beats production by ≥1% ROC-AUC, update registry production tag.
7. [ ] **Task 7 — `invalidate_cache`**: Clear Redis cache keys for scan results tied to the regulation.
8. [ ] **Task 8 — `drift_check`**: Run Evidently drift report on `regulatory_changes`; alert if p-value < threshold.
9. [ ] **DAG structure**: `refresh` → `enrich` → `[train_reach, train_pfas]` → `evaluate` → `promote` → `invalidate`; `promote` → `drift_check`.
10. [ ] **Retries / alerts**: Add email/Slack on failure; retry 3× with exponential backoff.

## Dependencies
- `feat/ml-training-registry` (training callable must exist)
- `feat/mlops-admin-api` (drift logic reusable)

## Outcome
Weekly Airflow DAG fully automates data refresh, training, evaluation, promotion, and drift monitoring.
