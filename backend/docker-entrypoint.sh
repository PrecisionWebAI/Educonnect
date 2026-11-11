#!/bin/sh
# ============================================================================
# Educonnect backend - container entrypoint
#
#   1. wait for the database (host:port from DATABASE_URL_OVERRIDE)
#   2. create DB/schema where we own it, then alembic upgrade head
#   3. run the numbered seeds: scripts/seed/run_seeds.py (01_roles_seed, ...)
#   4. exec the CMD (uvicorn)
#
# Idempotent, and a failing step is logged but never fatal. Demo data is manual
# only: scripts/seed/demo_data_seed/ via `make seed-roll`.
#
# Env: DATABASE_URL_OVERRIDE (host to wait for), DB_HOST/DB_PORT (fallback),
#      DB_WAIT_SECONDS (default 60).
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
# Split "<host> <port>" with parameter expansion, never `set --`: positional
# parameters are the container CMD, and overwriting them makes the final
# `exec "$@"` try to run the hostname ("exec: <host>: not found", exit 127,
# which restart:unless-stopped then loops forever).
DB_HOST="${WAIT_TARGET% *}"
DB_PORT="${WAIT_TARGET##* }"
DB_HOST="${DB_HOST:-localhost}"
DB_PORT="${DB_PORT:-5432}"

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
# 3. Seeds - the numbered scripts in scripts/seed/ (01_roles_seed, ...), in order.
# ---------------------------------------------------------------------------
echo "[entrypoint] seeds: scripts/seed/NN_*_seed.py"
if ! python scripts/seed/run_seeds.py; then
    echo "[entrypoint] WARNING: seeds failed - continuing"
fi

# ---------------------------------------------------------------------------
# Hand over to the container CMD (uvicorn) as PID 1 so signals reach it.
# ---------------------------------------------------------------------------
if [ "$#" -eq 0 ]; then
    echo "[entrypoint] ERROR: no CMD to exec - the image needs one (uvicorn app.main:app ...)" >&2
    exit 1
fi
echo "[entrypoint] Starting: $*"
exec "$@"
