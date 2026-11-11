#!/bin/sh
# ============================================================================
# Educonnect backend — container entrypoint
#
# Runs the database bootstrap BEFORE the API starts, then hands over to the
# container CMD (uvicorn):
#
#   1. wait until the configured database accepts connections
#   2. create the database + schema, apply Alembic migrations
#   3. run the seeds in order — each step labelled in the logs
#
# There is no database container: the database is the Supabase project named by
# `DATABASE_URL_OVERRIDE` in `backend/.env`, the same one `make dev` uses. A DSN
# that already exists needs no creation, so `ensure_database` / `ensure_schema`
# skip their DDL for a managed provider and only migrations run.
#
# `scripts/seed.py` registers the schools and their one admin each (the **system
# admin** first, then the schools). The app-level seeders come next through
# `app/core/bootstrap.py` - the role catalog, the class catalog (shared by every
# school) and the RBAC grants.
#
# No students, teachers, staff, fees, salaries, homework or sample rows are
# seeded: those come from the product flows (admission, hiring). The demo roll is
# a **manual** script (`scripts/auto_seeder_by_admission_form_and_teacher_form.py`,
# `make seed-roll`) and is never called from here.
#
# Every step is idempotent (each seed checks its own tables first and skips), so
# this is safe on every start. A failing step is logged and skipped, never
# fatal — same as app/core/bootstrap.py — so a bad seed can never stop the API
# from starting.
#
# Env:
#   DATABASE_URL_OVERRIDE  the DSN whose host:port is waited for (preferred)
#   DB_HOST / DB_PORT      fallback for a database you run yourself
#   DB_WAIT_SECONDS        how long to wait for the DB       (default: 60)
# ============================================================================

set -e

DB_WAIT_SECONDS="${DB_WAIT_SECONDS:-60}"

# ---------------------------------------------------------------------------
# 1. Wait for the database. The host/port come from the DSN when there is one -
#    a managed database is not a compose service, so `DB_HOST` cannot describe
#    it. A plain `docker run` without compose is covered by the same loop.
# ---------------------------------------------------------------------------
WAIT_TARGET=$(python <<'PY'
import os
from urllib.parse import urlsplit

dsn = os.environ.get("DATABASE_URL_OVERRIDE", "")
if dsn:
    url = urlsplit(dsn)
    print(f"{url.hostname} {url.port or 5432}")
else:
    print(f"{os.environ.get('DB_HOST', 'localhost')} {os.environ.get('DB_PORT', 5432)}")
PY
)
# shellcheck disable=SC2086  # two words, split on purpose
set -- $WAIT_TARGET
DB_HOST="$1"
DB_PORT="$2"

echo "[entrypoint] Waiting for the database at ${DB_HOST}:${DB_PORT} ..."
waited=0
until python -c "
import socket, sys
sock = socket.socket()
sock.settimeout(2)
sys.exit(0 if sock.connect_ex(('${DB_HOST}', ${DB_PORT})) == 0 else 1)
"; do
    waited=$((waited + 2))
    if [ "${waited}" -ge "${DB_WAIT_SECONDS}" ]; then
        echo "[entrypoint] ${DB_HOST}:${DB_PORT} still unreachable after ${DB_WAIT_SECONDS}s - starting anyway"
        break
    fi
    echo "[entrypoint] Database not ready yet - retrying in 2s"
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
