.PHONY: help install dev test lint format clean compose-up compose-down

help:
	@echo "BOMGuard — available commands:"
	@echo "  make install       — install backend and frontend dependencies"
	@echo "  make dev           — start dev servers (backend + frontend)"
	@echo "  make test          — run all tests"
	@echo "  make lint          — run linters (ruff, mypy, eslint)"
	@echo "  make format        — auto-format code"
	@echo "  make clean         — remove build artifacts"
	@echo "  make compose-up    — start full Docker Compose stack"
	@echo "  make compose-down  — stop Docker Compose stack"

install:
	cd backend && uv sync
	cd frontend && npm install

dev:
	@echo "Start backend: cd backend && uv run uvicorn bomguard.main:create_app --factory --reload"
	@echo "Start frontend: cd frontend && npm run dev"

test:
	cd backend && uv run pytest tests/ -v
	cd frontend && npm run type-check

lint:
	cd backend && uv run ruff check bomguard/ tests/ && uv run ruff format --check bomguard/ tests/ && uv run mypy bomguard/
	cd frontend && npm run lint && npm run format:check

format:
	cd backend && uv run ruff format bomguard/ tests/ && uv run ruff check --fix bomguard/ tests/
	cd frontend && npm run format

clean:
	rm -rf backend/.venv frontend/node_modules frontend/dist
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name .pytest_cache -exec rm -rf {} + 2>/dev/null || true

compose-up:
	docker compose up --build -d

compose-down:
	docker compose down -v
