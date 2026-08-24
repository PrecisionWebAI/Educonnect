# backend

A project created with FastAPI CLI.

## Quick Start

### Start the development server

```bash
uv run fastapi dev
```

Visit http://localhost:8000

### Deploy to FastAPI Cloud

Sign up and log in at https://fastapicloud.com, then deploy with:

```bash
uv run fastapi deploy
```

## Project Structure

- `main.py` - Your FastAPI application
- `pyproject.toml` - Project dependencies

## Available Commands

You can run commands using `make` directly:

| Command | Action |
|---|---|
| `make dev` | Start development server with auto-reload (`fastapi dev app/main.py`) |
| `make start` | Start server in production mode (`fastapi run app/main.py`) |
| `make check` | Run lint & formatting checks (`ruff check` & `ruff format --check`) |
| `make fix` | Auto-fix lint issues and format all files |
| `make lint` | Run Ruff lint check only |
| `make lint-fix` | Run Ruff lint auto-fix only |
| `make format` | Run Ruff code formatter |
| `make format-check`| Check formatting without modifying files |
| `make migrate` | Run database migrations (`alembic upgrade head`) |

## Code Quality & Git Hooks

This project uses [Ruff](https://docs.astral.sh/ruff/) and [pre-commit](https://pre-commit.com/) to automatically check and format code on both **pre-commit** and **pre-push**.

### Install Git Hooks
```bash
uv run --directory backend pre-commit install --hook-type pre-commit --hook-type pre-push
```

### Run All Pre-commit Hooks Manually
```bash
uv run --directory backend pre-commit run --all-files
```

## Learn More

- [FastAPI Documentation](https://fastapi.tiangolo.com)
- [Ruff Documentation](https://docs.astral.sh/ruff/)
- [Pre-commit Documentation](https://pre-commit.com/)
