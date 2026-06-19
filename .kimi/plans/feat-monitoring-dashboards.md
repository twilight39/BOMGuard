# Plan: Grafana Dashboards

## Goal
Replace empty stub dashboard with useful operational and ML observability panels.

## Scope
- `monitoring/dashboards/bomguard.json`
- `monitoring/prometheus.yml` (add rules if needed)

## Tasks
1. [ ] **API health panel**: Request rate, p95 latency, error rate from `/api/metrics`.
2. [ ] **BOM activity panel**: Uploads per hour, scan queue depth, Celery worker task rate.
3. [ ] **Regulatory data panel**: Substance counts per regulation, last successful scrape timestamp.
4. [ ] **ML performance panel**: Per-regulation ROC-AUC over time (read from `ml_model_performance` via Postgres exporter or custom metric).
5. [ ] **LLM usage panel**: RAG query rate, embedding generation latency, OpenRouter token spend estimate.
6. [ ] **Infrastructure panel**: CPU / memory / disk for API, DB, Redis containers.
7. [ ] **Alerts**: Prometheus alerting rules for API down, scrape failures, ML model stale (>14 days).
8. [ ] **Provisioning**: Ensure `monitoring/dashboards/bomguard.json` is auto-loaded by Grafana via volume mount.

## Dependencies
- `feat/mlops-admin-api` (for ML metrics data source)

## Outcome
Grafana provides a single pane of glass for system health, regulatory data freshness, and model performance.
