.PHONY: dev start lint lint-fix format format-check check fix test migrate check-schema check-logins docker docker-up docker-down docker-logs db-sync db-supabase db-verify db-wipe seed seed-roll

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

# The gates: behaviour, plus the tree and configuration rules that `scripts/` no
# longer carries (tests/test_structure.py, tests/test_config.py). Pair it with
# `uv run python -m compileall -q app scripts`, which catches a broken import.
test:
	uv run python -m pytest tests -q

# Database migrations
migrate:
	uv run alembic upgrade head

# Does the database still match the code? Exit 1 when the two have drifted.
check-schema:
	uv run python scripts/check_schema.py

# Can the seeded logins still sign in? Exit 1 on drift. Read-only: the seed never
# re-keys an existing account, so `backend/.env` and the stored hash can disagree.
check-logins:
	uv run python scripts/check_logins.py

# ---------------------------------------------------------------------------
# Docker: the backend image and `docker-compose.yml` (FastAPI only - the
# database is the Supabase project named by `backend/.env`).
#   make docker     build, then run in the foreground
#   make docker-up  build, then run detached
# ---------------------------------------------------------------------------
docker:
	docker compose build
	docker compose up

docker-up:
	docker compose build
	docker compose up -d

docker-down:
	docker compose down

docker-logs:
	docker compose logs -f backend

# ---------------------------------------------------------------------------
# The database: one command, one database. Schema, seeds and the drift check -
# exactly the three steps the container boot runs, so a hand-run cannot drift
# from a boot.
#   make db-sync                   backend/.env's database (the Supabase project)
#   make db-sync TARGET=supabase   the same one via SUPABASE_DB_URL
# ---------------------------------------------------------------------------
db-sync:
	uv run python scripts/db_sync.py --target $(if $(TARGET),$(TARGET),env)

db-supabase:
	uv run python scripts/db_sync.py --target supabase

# Is this database still right? Models vs schema, then the seeded logins.
# Exit 1 when either disagrees.
db-verify:
	uv run python scripts/check_schema.py
	uv run python scripts/check_logins.py

# Empty every table, keep the schema: the next boot (bootstrap) re-seeds the
# catalogs, and the demo roll stays off until someone runs `make seed-roll`.
#   make db-wipe ARGS="--yes --i-mean-production --backup rows.json"
db-wipe:
	uv run python scripts/db_sync.py --wipe $(ARGS)

# The seeds, in filename order: 01_roles_seed, 02_permissions_seed,
# 03_school_seed, 04_academics_seed. Boot runs the same file, so a hand-run
# cannot drift from a boot.
seed:
	uv run python scripts/seed/run_seeds.py

# Demo data (manual only, real database): one school's students, teachers,
# register and leave requests. Refuses to run without --yes.
#   make seed-roll ARGS="--school abc --yes"
seed-roll:
	uv run python scripts/seed/demo_data_seed/auto_seeder_by_admission_form_and_teacher_form.py $(ARGS)
