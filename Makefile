.PHONY: dev start lint lint-fix format format-check check fix migrate check-schema check-logins hooks docker docker-up docker-down docker-logs db-sync db-supabase db-verify db-wipe seed seed-roll

# Backend targets delegated to backend/
dev:
	$(MAKE) -C backend dev

start:
	$(MAKE) -C backend start

lint:
	$(MAKE) -C backend lint

lint-fix:
	$(MAKE) -C backend lint-fix

format:
	$(MAKE) -C backend format

format-check:
	$(MAKE) -C backend format-check

check:
	$(MAKE) -C backend check

fix:
	$(MAKE) -C backend fix

migrate:
	$(MAKE) -C backend migrate

check-schema:
	$(MAKE) -C backend check-schema
check-logins:
	$(MAKE) -C backend check-logins

# Docker: the backend image + backend/docker-compose.yml (see backend/Makefile).
docker:
	$(MAKE) -C backend docker

docker-up:
	$(MAKE) -C backend docker-up

docker-down:
	$(MAKE) -C backend docker-down

docker-logs:
	$(MAKE) -C backend docker-logs

# Git hooks
hooks:
	uv run --directory backend pre-commit install --hook-type pre-commit --hook-type pre-push

# ---------------------------------------------------------------------------
# The database. One database (the Supabase project in backend/.env), so this is
# the same schema -> seeds -> verify the container boot runs.
# ---------------------------------------------------------------------------
db-sync:
	$(MAKE) -C backend db-sync

db-supabase:
	$(MAKE) -C backend db-sync TARGET=supabase

db-verify:
	$(MAKE) -C backend db-verify

# Empty every table, keep the schema (DESTRUCTIVE - the flags are not optional).
#   make db-wipe ARGS="--yes --i-mean-production"
db-wipe:
	$(MAKE) -C backend db-wipe ARGS="$(ARGS)"

# The seeds alone: scripts/seed/01_roles_seed.py -> 04_academics_seed.py.
seed:
	$(MAKE) -C backend seed

# Demo data (manual only). Writes to the real database, so --yes is required.
#   make seed-roll ARGS="--school abc --yes"
seed-roll:
	$(MAKE) -C backend seed-roll ARGS="$(ARGS)"
