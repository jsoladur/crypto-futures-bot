# Crypto Futures Bot — Agent Instructions

## Project Overview

Python-based cryptocurrency futures trading bot that automates trading on **MEXC**, **Bitget**, and **BloFin** exchanges. Integrates with **Telegram** for real-time monitoring and manual control. Architecture is modular with dependency injection, async programming, and clean separation of concerns.

## Key Technologies

- **Language:** Python 3.13+
- **Dependency Management:** [uv](https://github.com/astral-sh/uv)
- **Telegram Bot:** `aiogram`
- **Database:** `sqlalchemy`, `aiosqlite` (async SQLite), `alembic` (migrations)
- **Scheduling:** `apscheduler`
- **DI:** `dependency-injector` (Singleton pattern)
- **Configuration:** `pydantic-settings`
- **Exchange Integration:** `ccxt`
- **Analysis:** `ta` (technical analysis), `pandas`
- **Utilities:** `taskipy` (task runner), `ruff` (linter/formatter), `bandit` (security)

## Project Setup & Execution

- **Install dependencies:** `uv sync`
- **Run bot:** `task start` (runs `python -m crypto_futures_bot.main`)
- **Run tests:** `task test` (runs `pytest -x --log-cli-level=INFO`)
- **Coverage:** `task test:coverage` (adds `--cov=./src`)
- **Lint:** `task lint` (runs `pre-commit install && pre-commit run --all`)
- **Migrations:** `task make-migrations` (runs `alembic revision --autogenerate`)
- **Docker:** `docker-compose up --build` (mounts SQLite volume for persistence)

## Testing Quirks

- Uses `pytest-asyncio` in `auto` mode — no `@pytest.mark.asyncio` needed.
- `tests/conftest.py` creates a temporary SQLite DB per test session.
- Exchanges are mocked: default target is `BITGET`. Market data loaded from JSON resource files in `tests/helpers/resources/`.
- Background tasks are disabled by default in tests via `BACKGROUND_TASKS_ENABLED=false` env var.
- Always run `task test` after changes to verify nothing breaks.

## Architecture & Dependency Injection

- Source code lives in `src/crypto_futures_bot/` with a layered structure:
  - **`domain/`** — Core business logic, value objects, enums.
  - **`infrastructure/`** — Database access, external API adapters (MEXC, Bitget, BloFin), background services.
  - **`interfaces/`** — Entry points for interaction, primarily Telegram bot handlers. Dynamically loads commands from `interfaces/telegram/commands` and `interfaces/telegram/callbacks` using a module loader.
  - **`config/`** — Application configuration (`configuration_properties.py` Pydantic model) and DI container setup.
- Background tasks use `apscheduler` and a `pyee` event emitter for trading signals.

## Key Configuration (`.env`)

Create from `.env.example`. Key variables:

| Variable | Description |
|---|---|
| `ROOT_USER` / `ROOT_PASSWORD` | Admin credentials |
| `TELEGRAM_BOT_TOKEN` / `TELEGRAM_BOT_ENABLED` | Telegram bot config |
| `DATABASE_URL` | e.g. `sqlite+aiosqlite:///db.sqlite3` |
| `FUTURES_EXCHANGE` | `MEXC`, `BITGET` or `BLOFIN` |
| `MEXC_API_KEY` / `MEXC_API_SECRET` / `MEXC_WEB_AUTH_TOKEN` | MEXC credentials |
| `BITGET_API_KEY` / `BITGET_API_SECRET` / `BITGET_API_PASSPHRASE` | Bitget credentials |
| `BLOFIN_API_KEY` / `BLOFIN_API_SECRET` / `BLOFIN_API_PASSPHRASE` | BloFin credentials |
| `JOB_INTERVAL_SECONDS` | Scheduler interval |
| `NOTIFY_ENTRY_SIGNALS` | Enable signal notifications |
| `BACKGROUND_TASKS_ENABLED` | Enable/disable background tasks |

## Directory Structure Highlights

- `src/crypto_futures_bot/main.py` — Entry point. Initializes DI container, runs migrations, starts bot/scheduler.
- `src/crypto_futures_bot/config/configuration_properties.py` — Pydantic model for all config options.
- `tests/infrastructure/tasks/` — Integration tests for background tasks.
  - `signals_task_service_test.py` — Tests `SignalsTaskService`, shows how to mock exchange/technical analysis and verify `AsyncIOEventEmitter` events.

## Linting / Formatting

- `ruff` for linting and formatting (uses `absolufy-imports` plugin).
- `bandit` for security checks via `pre-commit`.
- Run `task lint` before committing.
