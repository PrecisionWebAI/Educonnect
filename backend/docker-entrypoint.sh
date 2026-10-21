#!/bin/sh
# ============================================================================
# Educonnect backend — container entrypoint
#
# Runs the database bootstrap BEFORE the API starts, then hands over to the
# container CMD (uvicorn):
#
#   1. wait until PostgreSQL accepts connections
#   2. create the database + schema, apply Alembic migrations
#   3. run the seed scripts — one line each, so the order is explicit here and
#      each file's output is labelled in the logs
#
# Only two seeds exist: scripts/seed.py (the demo school + its one admin) and
# scripts/seed_academics.py (the class structure). No students, teachers, staff,
# fees, salaries, homework or sample rows are seeded.
#
# Every step is idempotent (each seed checks its own tables first and skips), so
# this is safe on every start. A failing step is logged and skipped, never
# fatal — same as app/core/bootstrap.py — so a bad seed can never stop the API
# from starting.
#
# Env:
#   DB_HOST          host of the PostgreSQL service    (compose: db)
#   DB_PORT          port inside the compose network   (compose: 5432)
#   DB_WAIT_SECONDS  how long to wait for the DB       (default: 60)
# ============================================================================

set -e

DB_HOST="${DB_HOST:-db}"
DB_PORT="${DB_PORT:-5432}"
DB_WAIT_SECONDS="${DB_WAIT_SECONDS:-60}"

# ---------------------------------------------------------------------------
# 1. Wait for PostgreSQL. Compose already gates on the db healthcheck; this
#    also covers a plain `docker run`, where nothing waits for the database.
# ---------------------------------------------------------------------------
echo "[entrypoint] Waiting for PostgreSQL at ${DB_HOST}:${DB_PORT} ..."
waited=0
until python -c "
import socket, sys
sock = socket.socket()
sock.settimeout(2)
sys.exit(0 if sock.connect_ex(('${DB_HOST}', ${DB_PORT})) == 0 else 1)
"; do
    waited=$((waited + 2))
    if [ "${waited}" -ge "${DB_WAIT_SECONDS}" ]; then
        echo "[entrypoint] PostgreSQL still unreachable after ${DB_WAIT_SECONDS}s - starting anyway"
        break
    fi
    echo "[entrypoint] PostgreSQL not ready yet - retrying in 2s"
    sleep 2
done

# ---------------------------------------------------------------------------
# 2. Database, schema and migrations — reuse the tested helpers from
#    app/core/bootstrap.py instead of duplicating that logic here.
# ---------------------------------------------------------------------------
echo "[entrypoint] Preparing database (create DB/schema, apply migrations) ..."
if ! python -c "
from app.core.bootstrap import ensure_database, ensure_schema, run_migrations
ensure_database()
ensure_schema()
run_migrations()
"; then
    echo "[entrypoint] WARNING: database preparation failed - starting anyway (the API retries on startup)"
fi

# ---------------------------------------------------------------------------
# 3. Seed scripts — one process per file, so each one's output is labelled.
#    No student / teacher / staff seeding (see the header above).
# ---------------------------------------------------------------------------
run_seed() {
    echo "[entrypoint] seed: scripts/$1.py"
    if ! python "scripts/$1.py"; then
        echo "[entrypoint] WARNING: scripts/$1.py failed - continuing"
    fi
}

# The role catalog must exist before any account is given a role, and the RBAC
# grants point at role ids - so it comes first.
echo "[entrypoint] seed: role catalog"
if ! python -c "from app.core.bootstrap import seed_roles; seed_roles()"; then
    echo "[entrypoint] WARNING: role seed failed - continuing"
fi

run_seed seed              # the demo school + its one admin (admin@<school code>)
run_seed seed_academics    # the class structure: 15 classes, sections A-J

echo "[entrypoint] seed: RBAC permissions"
if ! python -c "from app.core.bootstrap import seed_permissions; seed_permissions()"; then
    echo "[entrypoint] WARNING: permission seed failed - continuing"
fi

# ---------------------------------------------------------------------------
# Hand over to the container CMD (uvicorn) as PID 1 so signals reach it.
# ---------------------------------------------------------------------------
echo "[entrypoint] Starting: $*"
exec "$@"
