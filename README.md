# BOMGuard

Open-source Bill of Materials (BOM) compliance scanner for the electronics manufacturing industry.

## Features (in development)

- **Live regulatory data ingestion** — ECHA REACH SVHC and EPA CompTox
- **BOM compliance scanning** — multi-regulation simultaneous scanning
- **ML risk prediction** — XGBoost with SHAP interpretability
- **LLM-powered Q&A** — RAG pipeline with Gemini 2.5 Flash
- **MLOps pipeline** — Airflow, MLflow, Evidently AI

## Tech Stack

| Layer | Technology |
|-------|-----------|
| API | FastAPI + Python 3.12 |
| Frontend | React 19 + TypeScript + Tailwind CSS + shadcn/ui |
| Database | PostgreSQL 16 + pgvector |
| Cache / Queue | Redis 7 + Celery |
| ML | XGBoost + Optuna + SHAP |
| LLM | Gemini 2.5 Flash |
| Monitoring | Prometheus + Grafana |

## Quick Start

```bash
# Install dependencies
make install

# Start infrastructure
docker compose up db redis -d

# Run backend (terminal 1)
cd backend && uv run uvicorn bomguard.main:create_app --factory --reload

# Run frontend (terminal 2)
cd frontend && npm run dev
```

## Development

```bash
make lint      # Run all linters
make format    # Auto-format code
make test      # Run all tests
```

## License

MIT
