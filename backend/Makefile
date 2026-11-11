.PHONY: dev start lint lint-fix format format-check check fix migrate check-schema check-logins smoke docker docker-up docker-down docker-logs db-sync db-supabase db-verify seed seed-roll audit-config

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

# Can the seeded logins still sign in? Exit 1 on drift. Read-only: the seed never
# re-keys an existing account, so `backend/.env` and the stored hash can disagree.
check-logins:
	uv run python scripts/check_logins.py

# Read-only smoke test of the Admission / Staff Hiring / Classroom routes.
smoke:
	uv run python scripts/smoke_areas.py

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

# Is configuration still all-in-one-place, all-documented, no secret defaults?
audit-config:
	uv run python scripts/audit_config.py
