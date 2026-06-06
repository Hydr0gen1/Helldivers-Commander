# WarDesk — Helldivers 2 Galactic War Companion

WarDesk is a self-hosted companion app for the Helldivers 2 galactic war. Milestone M1 implements the live ingestion pipe: a single FastAPI backend worker polls the community API, stores normalized domain models in an in-process TTL cache, and serves a React/Vite galaxy map exclusively from WarDesk endpoints.

## What is included in M1

- FastAPI backend under `backend/app` with `/api/v1` routes for war state, planets, single planets, campaigns, current orders, dispatches, briefing, gambits, health, and SSE updates.
- Community upstream adapter for `https://api.helldivers2.dev`, including live war-ID resolution and the required `X-Super-*`/`User-Agent` headers.
- APScheduler ingest loop using one upstream request per data type per tick and an in-process TTL cache.
- Pydantic v2 domain models that serialize API responses with camelCase fields.
- Vite + React 18 + TypeScript + react-three-fiber frontend rendering planets and supply lines from `/api/v1/planets` only.

## Prerequisites

- Python 3.12
- Node.js 20+
- npm 10+

M1 does **not** require Postgres, TimescaleDB, Redis, Anthropic, or Steam API credentials.

## Backend setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
cp .env.example .env
uvicorn app.main:app --reload
```

The backend starts on <http://127.0.0.1:8000>. On startup it resolves the current war ID, performs the first ingest, then schedules refreshes.

Useful endpoints:

- `GET /healthz`
- `GET /api/v1/war`
- `GET /api/v1/planets`
- `GET /api/v1/planets/{index}`
- `GET /api/v1/orders/current`
- `GET /api/v1/dispatches`
- `GET /sse`

## Frontend setup

```bash
cd frontend
npm install
npm run dev
```

The frontend starts on <http://127.0.0.1:5173>. Vite proxies `/api`, `/healthz`, and `/sse` to the FastAPI backend. The frontend intentionally contains no upstream Helldivers API URL and never calls upstream services directly.

## Environment

Copy `backend/.env.example` to `backend/.env` and set at least:

```env
WARDESK_CONTACT=you@example.com
INGEST_INTERVAL_SECONDS=45
RATE_LIMIT_GUARD=true
```

`WARDESK_CONTACT` is sent in every upstream request as `X-Super-Contact` and in the `User-Agent` string.

## Project layout

```text
backend/app/main.py                 FastAPI app factory and lifespan
backend/app/cache.py                Cache interface and in-process TTL cache
backend/app/clients/base.py         Shared async httpx client with headers and backoff
backend/app/clients/sources/        Upstream source adapters
backend/app/ingest/worker.py        Scheduled ingest loop into cache
backend/app/models/domain.py        Canonical WarDesk API models
frontend/src/api/                   Typed WarDesk API client and model mirror
frontend/src/three/                 Galaxy map, planets, and supply lines
frontend/src/components/            Panels and war UI widgets
```

## Development checks

Backend:

```bash
cd backend
pytest
python -m compileall app tests
```

Frontend:

```bash
cd frontend
npm run build
```

## Milestone M2: local Postgres + TimescaleDB

M2 adds optional persistence and derivation. WarDesk still runs in M1 cache-only mode when `DATABASE_URL` is blank or the database cannot be reached; the backend logs that persistence is disabled and continues serving cached upstream data.

### Install Postgres and TimescaleDB locally

Ubuntu/Debian example:

```bash
sudo apt update
sudo apt install postgresql-16 postgresql-client-16
# Install TimescaleDB for your distro from https://docs.timescale.com/self-hosted/latest/install/
sudo timescaledb-tune --quiet --yes
sudo systemctl restart postgresql
```

macOS/Homebrew example:

```bash
brew install postgresql@16 timescaledb
brew services start postgresql@16
```

### Create the WarDesk role and database

```bash
sudo -u postgres psql <<'SQL'
CREATE ROLE wardesk WITH LOGIN PASSWORD 'wardesk';
CREATE DATABASE wardesk OWNER wardesk;
\c wardesk
CREATE EXTENSION IF NOT EXISTS timescaledb;
SQL
```

Set `DATABASE_URL` in `backend/.env`:

```env
DATABASE_URL=postgresql+asyncpg://wardesk:wardesk@localhost:5432/wardesk
```

Run migrations from the backend directory:

```bash
cd backend
alembic upgrade head
```

The M2 migration creates `planets_static`, `planet_snapshots` as a Timescale hypertable on `ts`, `orders`, and `dispatches`. After migrations and backend startup, each successful planets ingest tick writes a batch of `planet_snapshots` rows; `/api/v1/planets/{index}` reads recent snapshots to populate `derived`, and `/api/v1/planets/{index}/history` returns chart data for the frontend.
