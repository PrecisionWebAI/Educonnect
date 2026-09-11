# Educonnect

Automation of Schools Workflow

## Project Structure

```
├── backend/          # FastAPI + SQLModel API (uv-managed)
│   ├── app/          # Application code (core config, domain routers/models)
│   ├── alembic/      # Database migrations
│   ├── scripts/      # Demo seed data
│   └── Dockerfile    # Backend image (used by docker-compose.yml)
└── frontend/         # Next.js + Tailwind CSS app
```

## Run the Backend with Docker (Local)

The single root `docker-compose.yml` runs the full backend stack — FastAPI API + PostgreSQL — in containers:

```bash
docker compose up --build          # start in foreground
docker compose up --build -d       # start in background
docker compose down                # stop (data persists in the volume)
```

- OpenAPI docs: <http://localhost:8000/docs>
- Health check: <http://localhost:8000/health>

Notes:

- On startup the API automatically creates the database/schema, applies Alembic
  migrations, and seeds demo data (see `app/core/bootstrap.py`).
- DB/auth values (`DB_USER`, `DB_PASSWORD`, `DB_NAME`, `SECRET_KEY`) are read
  from the git-ignored `backend/.env` (see `backend/.env-example` for a template).
- If your machine already runs PostgreSQL on port **5432**, copy `.env.example`
  to `.env` at the repo root and set `PG_HOST_PORT` (e.g. `PG_HOST_PORT=5433`)
  so the containerized DB doesn't clash. Override `API_PORT` the same way.
- Requires Docker Desktop (Docker >= 24 / Compose v2).

## Run Locally (without Docker)

Backend development server with auto-reload:

```bash
cd backend
uv run fastapi dev
```

Visit <http://localhost:8000> — the app connects to the PostgreSQL settings in
`backend/.env`.

### Deploy to FastAPI Cloud

Sign up and log in at <https://fastapicloud.com>, then deploy with:

```bash
cd backend
uv run fastapi deploy
```

## Quick Commands

You can run commands using `make` from the repo root:

| Command | Action |
|---|---|
| `make dev` | Start development server with auto-reload (`fastapi dev app/main.py`) |
| `make start` | Start server in production mode (`fastapi run app/main.py`) |
| `make check` | Run lint & formatting checks (`ruff check` & `ruff format --check`) |
| `make fix` | Auto-fix lint issues and format all code |
| `make lint` | Run Ruff lint check only |
| `make lint-fix` | Run Ruff lint auto-fix only |
| `make format` | Run Ruff code formatter only |
| `make format-check` | Check formatting without modifying files |
| `make migrate` | Run database migrations (`alembic upgrade head`) |
| `make hooks` | Install Git hooks for `pre-commit` and `pre-push` |
| `make docker` | Build & run the full backend stack (FastAPI + PostgreSQL) with Docker |
| `make docker-up` | Same as `make docker` but detached (background) |
| `make docker-down` | Stop the Docker stack |
| `make docker-logs` | Stream backend logs |

## Code Quality & Git Hooks

This project uses [Ruff](https://docs.astral.sh/ruff/) and [pre-commit](https://pre-commit.com/) to automatically check and format code on both **pre-commit** and **pre-push**.

### Install Git Hooks

```bash
make hooks
```

### Run All Pre-commit Hooks Manually

```bash
uv run --directory backend pre-commit run --all-files
```

## Learn More

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pre-commit Documentation](https://pre-commit.com/)
