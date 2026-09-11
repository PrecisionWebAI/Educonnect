.PHONY: dev start lint lint-fix format format-check check fix migrate docker docker-up docker-down docker-logs

# Run development server with hot-reload
dev:
	uv run fastapi dev app/main.py

# Run production server
start:
	uv run fastapi run app/main.py --host 0.0.0.0 --port 8000

# Linting
lint:
	uv run ruff check .

lint-fix:
	uv run ruff check --fix .

# Formatting
format:
	uv run ruff format .

format-check:
	uv run ruff format --check .

# Combined Quality Checks
check:
	uv run ruff check .
	uv run ruff format --check .

# Combined Auto-Fix
fix:
	uv run ruff check --fix .
	uv run ruff format .

# Database migrations
migrate:
	uv run alembic upgrade head

# Docker (full backend stack: FastAPI + PostgreSQL — compose file lives at the repo root)
docker:
	cd .. && docker compose up --build

docker-up:
	cd .. && docker compose up --build -d

docker-down:
	cd .. && docker compose down

docker-logs:
	cd .. && docker compose logs -f backend
