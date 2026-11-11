.PHONY: dev start lint lint-fix format format-check check fix migrate check-schema check-logins smoke hooks docker docker-up docker-down docker-logs db-sync db-supabase db-verify seed seed-roll audit-config

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

smoke:
	$(MAKE) -C backend smoke



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

# The seeds alone: scripts/seed/01_roles_seed.py -> 04_academics_seed.py.
seed:
	$(MAKE) -C backend seed

# Demo data (manual only). Writes to the real database, so --yes is required.
#   make seed-roll ARGS="--school abc --yes"
seed-roll:
	$(MAKE) -C backend seed-roll ARGS="$(ARGS)"

audit-config:
	$(MAKE) -C backend audit-config
