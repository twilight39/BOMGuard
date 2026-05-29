FROM python:3.12-slim

WORKDIR /app

# Install system dependencies for RDKit and psycopg2
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    g++ \
    libfontconfig1 \
    libxrender1 \
    && rm -rf /var/lib/apt/lists/*

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /bin/uv

# Copy dependency files
COPY pyproject.toml ./
COPY README.md ./

# Install dependencies
RUN uv sync --no-install-project

# Copy application code
COPY bomguard/ ./bomguard/
COPY tests/ ./tests/
COPY alembic.ini ./
COPY migrations/ ./migrations/

# Install project
RUN uv sync

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "bomguard.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
