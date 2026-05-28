# BOMGuard — System Architecture

## Overview

BOMGuard is a regulation-agnostic BOM compliance scanner with ML-based risk prediction and LLM-powered regulatory intelligence. This document describes the system architecture, component interactions, and deployment topology.

---

## Component Architecture

```
                              ┌──────────────┐
                              │   React SPA  │
                              │  (TypeScript)│
                              └──────┬───────┘
                                     │ HTTPS
                              ┌──────▼───────┐
                              │   Traefik    │  Reverse Proxy + SSL
                              └──────┬───────┘
                                     │
                    ┌────────────────┼────────────────┐
                    │                │                │
              ┌─────▼──────┐  ┌──────▼───────┐  ┌────▼──────────┐
              │  FastAPI   │  │  WebSocket   │  │   Static      │
              │   (API)    │  │  Server      │  │   Files       │
              └─────┬──────┘  └──────────────┘  └───────────────┘
                    │
     ┌──────────────┼──────────────┬──────────────┐
     │              │              │              │
┌────▼──────┐ ┌────▼──────┐ ┌─────▼──────┐ ┌────▼──────┐
│PostgreSQL │ │  Redis    │ │  Celery    │ │  MLflow   │
│  +pgvector│ │           │ │  Workers   │ │           │
└────┬──────┘ └───────────┘ └─────┬──────┘ └────┬──────┘
     │                            │             │
     └──────────────┬─────────────┘             │
                    │                           │
             ┌──────▼────────┐         ┌────────▼────────┐
             │ Apache Airflow│         │ Prometheus +    │
             │   Scheduler   │         │    Grafana      │
             └───────────────┘         └─────────────────┘
```

---

## Service Definitions

| Service | Port | Role | Memory |
|---------|------|------|--------|
| FastAPI API | 8000 | REST API + WebSocket | ~256MB |
| React Frontend | 3000 | Static SPA (nginx) | ~32MB |
| PostgreSQL 16 + pgvector | 5432 | Primary database, vector store | ~512MB |
| Redis 7 | 6379 | Cache, Celery broker | ~128MB |
| Celery Worker | — | Background task processor | ~256MB |
| Celery Beat | — | Periodic task scheduler | ~64MB |
| MLflow | 5000 | Experiment tracking, model registry | ~256MB |
| Airflow Webserver | 8080 | Pipeline orchestration UI | ~256MB |
| Airflow Scheduler | — | DAG execution | ~256MB |
| Prometheus | 9090 | Metrics collection | ~128MB |
| Grafana | 3001 | Metrics visualization | ~256MB |
| Traefik | 80/443 | Reverse proxy, SSL termination | ~64MB |
| **Total** | | | **~2.4GB** |

The stack fits comfortably within a 4GB Hetzner VPS with ~1.6GB headroom for spikes. MLflow and Airflow can be stopped during low-activity periods — the core compliance scanner operates independently.

---

## Data Flow

### 1. Regulatory Data Ingestion

```
[ECHA Website] ──▶ [Scraper] ──▶ SHA-256 compare ──▶ [substances]
                                         │                    │
                                    Change detected?            │
                                         │                    │
                                    Yes ──┼──▶ [regulatory_changes]
                                         │           │
                                         │           ▼
                                         │     [Blast Radius]
                                         │           │
                                         │           ▼
                                         │     [WebSocket Alert]
                                         │           │
                                         │           ▼
                                         │     [LLM Summary]
                                         │     [Embedding Store]
```

The scraper runs every 6 hours via Celery beat. Content is hashed and compared against the stored hash — only changed content triggers downstream processing. This prevents unnecessary blast radius computations and LLM calls.

### 2. BOM Compliance Scan

```
[BOM Upload / Sample Clone]
         │
         ▼
[BOM Parser] ──▶ [bom_parts] (CAS numbers extracted)
         │
         ▼
[Feature Engineering] ──▶ cached [substance_properties]
         │                          (RDKit fingerprints, EPA data)
         │
         ▼
[Multi-Regulation Scanner]
         │
    ┌────┼────┬────────┬──────────┐
    │    │    │        │          │
    ▼    ▼    ▼        ▼          ▼
[REACH][PFAS][RoHS] [TSCA] [China RoHS]
  ML    ML   Rule   Rule     Rule
         │
         ▼
[Scan Results] ──▶ [scan_results] ──▶ [Frontend Dashboard]
```

For each regulation, the scanner checks whether an ML model is available. If so, it runs the XGBoost predictor with regulation-specific similarity features. If not, it falls back to deterministic CAS matching against the restricted substance list. Both paths produce uniform `ScanResult` records.

### 3. ML Training Pipeline

```
[Airflow DAG: risk_model_pipeline @weekly]
         │
    ┌────┴────┬────────────────┐
    │         │                │
    ▼         ▼                ▼
[Refresh  [Feature      [Train per regulation]
 Substance  Enrichment]       │
 Data]                        ├─▶ REACH SVHC model
    │                         ├─▶ PFAS model
    │                         │
    │                         ▼
    │                    [Temporal Holdout]
    │                    (auto-switch to random
    │                     stratified if <6mo data)
    │                         │
    │                         ▼
    │                    [Evaluate: ROC-AUC, AP,
    │                     Precision@100, Brier]
    │                         │
    │                    Pass? ──┬──▶ [Promote via MLflow]
    │                    Fail? ──┼──▶ [Retain Previous]
    │                            │
    │                            ▼
    │                       [SHAP Ref Plots]
    │                       [Evidently Drift]
    │                       [Invalidate Cache]
    │
    └─────────────────────────▶
```

The pipeline auto-selects its train/test split strategy: temporal holdout (80/20 by date) when at least 6 months of regulatory history exists, random stratified otherwise. This makes the pipeline robust during early deployment when historical data is sparse.

### 4. LLM / RAG Pipeline

```
[Regulatory Change Detected]
         │
         ▼
[Gemini 2.5 Flash: summarize]
         │
         ├──────────────────┐
         ▼                  ▼
   [Summary Text]    [Text Embedding]
   (regulatory_       (Gemini Embed API,
    summaries.          768-dim)
    summary_text)            │
         │                  ▼
         │            [pgvector store]
         │            (cosine similarity index)
         │                  │
         └──────────────────┘
                            │
              [User submits question]
                            │
                            ▼
                   [Embed query]
                            │
                            ▼
                   [pgvector: top-5 similarity]
                            │
                            ▼
                   [RAG prompt: context + query]
                            │
                            ▼
                   [Gemini: generate answer]
                            │
                            ▼
                   [Return answer + cited sources]
```

Regulatory summaries are generated once per substance-regulation pair and cached. The embedding + pgvector approach keeps vector search in the same PostgreSQL instance — no separate vector database service is required.

---

## Database Design

### Entity Relationships

```
substances (1) ────(*) substance_regulation_status ────(1) regulations
     │                                                        │
     ├──(1) substance_properties                              ├── ml_enabled flag
     │                                                        ├── model version
     ├──(*) regulatory_changes                                └── authority, scope
     │
     └──(*) regulatory_summaries (with pgvector embedding)

boms (1) ────(*) bom_parts ────(*) scan_results ────(1) regulations
```

### Key Design Decisions

**Single PostgreSQL instance with pgvector** over separate vector database (ChromaDB, Pinecone). This eliminates a network hop, reduces operational surface area, and keeps transaction boundaries simple. If vector query performance becomes a bottleneck at >100K substances, ChromaDB can be introduced as an indexed replica without code changes.

**PCA-reduced fingerprints stored as `FLOAT[]`** rather than full 1024-dim bit vectors. The 50 principal components capture ~95% of molecular variance per our evaluation. Storing them in a PostgreSQL array column allows direct querying without deserialization overhead.

---

## ML Architecture

### Regulation-Agnostic Design

The ML pipeline separates **universal features** (computed once per substance) from **regulation-specific features** (computed per model). This enables training separate models for each regulation without duplicating the expensive cheminformatics work.

**Universal features** (cached in `substance_properties`):
- Morgan fingerprint PCA components (50-dim)
- Molecular descriptors (8 scalar values)
- EPA toxicity properties (4 scalar values)

**Regulation-specific features** (computed at training/inference time):
- Tanimoto similarity to known restricted substances under that regulation
- Regulatory pre-signals (consultation list, intention list)

### Model Lifecycle

```
[Training Data] ──▶ [Optuna HPO] ──▶ [XGBoost] ──▶ [Calibrate]
                                                        │
                                                        ▼
                                              [Temporal Evaluation]
                                              (or random stratified)
                                                        │
                                              Pass? ────┼──▶ [MLflow: Production]
                                              Fail? ────┼──▶ [MLflow: Rejected]
                                                        │
                                                        ▼
                                               [RegulationModelRegistry]
                                               (loads production models
                                                into memory on first use)
```

### Inference Path

```
[BOM Part with CAS]
         │
         ▼
[Load cached substance features] ◀── [substance_properties]
         │
         ▼
[For each ML-enabled regulation]:
    - Compute regulation-specific similarity features
    - Concatenate with universal features
    - Run XGBoost predict_proba
    - Return risk_score + risk_tier
         │
         ▼
[Display: ML-predicted risks vs direct matches]
```

Inference latency: <100ms per substance per regulation on CPU. The model registry caches loaded models in memory to avoid repeated MLflow deserialization.

---

## Deployment Topology

```
                        Internet
                           │
                    ┌──────▼──────┐
                    │   Porkbun   │  DNS
                    │   Domain    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   Hetzner   │  CX21 (4GB RAM)
                    │     VPS     │  Ubuntu 22.04
                    │             │
                    │  Docker     │
                    │  Compose    │
                    │             │
                    │  ┌────────┐ │
                    │  │Traefik │ │  ← Port 80, 443
                    │  │  SSL   │ │
                    │  └────┬───┘ │
                    │       │     │
                    │  ┌────┴───┐ │
                    │  │11 svcs │ │  ← All containerized
                    │  └────────┘ │
                    └─────────────┘
                           │
                    ┌──────▼──────┐
                    │  GHCR       │  Container Registry
                    │  (GitHub)   │  Images pushed via Blacksmith CI
                    └─────────────┘
```

### SSL / Domain

Traefik handles automatic Let's Encrypt certificate provisioning and renewal. The Porkbun domain points to the Hetzner VPS IP. Traefik routes `api.` subdomain to FastAPI and root domain to the React frontend.

### CI/CD Flow

```
[Git Push to main]
         │
         ▼
[Blacksmith Runner]  (2x faster than GitHub-hosted)
         │
    ┌────┼────┬────────────┐
    │    │    │            │
    ▼    ▼    ▼            ▼
 [ruff] [mypy] [pytest] [docker build]
 lint   type   backend   + push to GHCR
        check  frontend
               ml
    │
    ▼
[SSH to Hetzner]
[docker compose pull && up -d]
```

---

## Scaling Path

Current deployment targets a single-server setup for cost efficiency (~$7/month). The architecture supports horizontal scaling without structural changes:

| Bottleneck | Current | Scale-Out |
|-----------|---------|-----------|
| API throughput | Single FastAPI instance | Add replicas behind Traefik load balancer |
| ML inference | In-process, CPU-bound | ONNX export + inference service with GPU |
| Database | Single PostgreSQL | RDS/Cloud SQL with read replica |
| Scraping | Single Celery worker | Distributed scraping with Scrapy cluster |
| Vector search | pgvector (CPU) | Pinecone/Weaviate for >100K vectors |

Kubernetes manifests in `k8s/` document the scale-out topology. These are not required for the portfolio demo but serve as interview discussion material.

---

## Failure Modes

| Component | Failure | Mitigation |
|-----------|---------|------------|
| ECHA scraper | Site redesign / rate limit | Exponential backoff; fallback to last cached data; manual import path |
| EPA CompTox API | Key expiry / downtime | Cached substance_properties serve stale data; queue retry |
| Gemini API | Rate limit / outage | LLM chat returns "service unavailable"; RAG falls back to keyword search |
| ML model | Drift / accuracy drop | Evidently detection gates prevent promotion; previous model retained |
| Database | Connection loss | Retry with exponential backoff; Celery tasks queued in Redis survive restart |
| Hetzner VPS | Outage | Porkbun DNS TTL 300s; backup restore from GitHub + docker compose up |
