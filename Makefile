.PHONY: dev start lint lint-fix format format-check check fix migrate check-schema check-logins smoke hooks docker docker-up docker-down docker-logs db-local db-supabase db-verify db-diff db-copy audit-config

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
# Database, by target. Same three steps (schema -> seeds -> verify) everywhere.
#   make db-local      the docker postgres / backend/.env
#   make db-supabase   whatever SUPABASE_DB_URL points at
# ---------------------------------------------------------------------------
db-local:
	$(MAKE) -C backend db-sync TARGET=local

db-supabase:
	$(MAKE) -C backend db-sync TARGET=supabase

db-verify:
	$(MAKE) -C backend db-verify

# Row-level parity, and the one-shot fix when there is none: `db-diff` only
# reads, `db-copy` replaces Supabase's rows with local's (DRY=1 to preview).
db-diff:
	$(MAKE) -C backend db-diff

db-copy:
	$(MAKE) -C backend db-copy $(if $(DRY),DRY=1,)

audit-config:
	$(MAKE) -C backend audit-config
