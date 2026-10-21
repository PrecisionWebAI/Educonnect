#!/bin/sh
# ============================================================================
# Educonnect backend — container entrypoint
#
# Runs the database bootstrap BEFORE the API starts, then hands over to the
# container CMD (uvicorn):
#
#   1. wait until PostgreSQL accepts connections
#   2. create the database + schema, apply Alembic migrations
#   3. run the seeds in order — each step labelled in the logs
#
# `scripts/seed.py` is the **only** script seed: it registers the schools and their
# one admin each. The rest are app-level seeders called through
# `app/core/bootstrap.py` - the role catalog, the class catalog (15 classes +
# 150 sections, shared by every school) and the RBAC grants. No students,
# teachers, staff, fees, salaries, homework or sample rows are seeded.
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

run_seed seed              # the schools + one admin each (scripts/seed.py)

# The class catalog is an app-level seeder, like the roles and permissions.
echo "[entrypoint] seed: class catalog"
if ! python -c "from app.core.bootstrap import seed_academics; seed_academics()"; then
    echo "[entrypoint] WARNING: class structure seed failed - continuing"
fi

echo "[entrypoint] seed: RBAC permissions"
if ! python -c "from app.core.bootstrap import seed_permissions; seed_permissions()"; then
    echo "[entrypoint] WARNING: permission seed failed - continuing"
fi

# ---------------------------------------------------------------------------
# Hand over to the container CMD (uvicorn) as PID 1 so signals reach it.
# ---------------------------------------------------------------------------
echo "[entrypoint] Starting: $*"
exec "$@"
