.PHONY: dev start lint lint-fix format format-check check fix migrate check-schema smoke docker docker-up docker-down docker-logs

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

# Does the database still match the code? Exit 1 when the two have drifted.
check-schema:
	uv run python scripts/check_schema.py

# Read-only smoke test of the Admission / Staff Hiring / Classroom routes.
smoke:
	uv run python scripts/smoke_areas.py
