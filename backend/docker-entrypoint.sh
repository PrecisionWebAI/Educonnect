#!/bin/sh
# ============================================================================
# Educonnect backend - container entrypoint
#
#   1. wait for the database (host:port from DATABASE_URL_OVERRIDE)
#   2. exec the CMD (uvicorn)
#
# The schema, the migrations and the seeds are **not** done here: the app does
# them on startup (`app/core/bootstrap.py`), so each step has one implementation
# and prints its status once. Running them here as well would seed twice and
# double the boot time.
#
# Demo data is manual only: scripts/seed/demo_data_seed/ via `make seed-roll`.
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
# 2. Hand over to the container CMD (uvicorn) as PID 1 so signals reach it.
# ---------------------------------------------------------------------------
if [ "$#" -eq 0 ]; then
    echo "[entrypoint] ERROR: no CMD to exec - the image needs one (uvicorn app.main:app ...)" >&2
    exit 1
fi
echo "[entrypoint] Starting: $*"
exec "$@"
