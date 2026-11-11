.PHONY: dev start lint lint-fix format format-check check fix migrate check-schema check-logins smoke hooks docker docker-up docker-down docker-logs db-sync db-supabase db-verify seed-roll audit-config

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
# The database. There is exactly one - the Supabase project named by
# DATABASE_URL_OVERRIDE in backend/.env - so this is the same three steps
# (schema -> seeds -> verify) that the container boot runs, nothing more.
# ---------------------------------------------------------------------------
db-sync:
	$(MAKE) -C backend db-sync

db-supabase:
	$(MAKE) -C backend db-sync TARGET=supabase

db-verify:
	$(MAKE) -C backend db-verify

# The demo roll (admitted students, teachers, the register, leave requests).
# MANUAL ONLY: nothing in the boot, the entrypoint or CI calls it. It replaces
# the named school's rows, and the database it writes to is the real one, so the
# script insists on --yes.
#   make seed-roll ARGS="--school abc --sections a,b --yes"
seed-roll:
	$(MAKE) -C backend seed-roll ARGS="$(ARGS)"

audit-config:
	$(MAKE) -C backend audit-config
