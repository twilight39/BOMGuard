# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app

# Install system dependencies (cached layer — rarely changes)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    g++ \
    libfontconfig1 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Pin uv version for reproducible builds
COPY --from=ghcr.io/astral-sh/uv:0.5.0 /uv /bin/uv

# Copy dependency metadata
COPY pyproject.toml ./
COPY README.md ./

# Install dependencies with BuildKit cache mount for uv cache.
# This layer is cached until pyproject.toml changes.
# Heavy packages (rdkit, scikit-learn, xgboost, numba) are built once and cached.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --no-install-project

# Copy application code
COPY bomguard/ ./bomguard/
COPY tests/ ./tests/
COPY alembic.ini ./
COPY migrations/ ./migrations/

# Install project (fast — only re-links the local package)
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

RUN mkdir -p /app/static/avatars

EXPOSE 8000

CMD ["uvicorn", "bomguard.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
