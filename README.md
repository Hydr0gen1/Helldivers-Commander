# WarDesk — Helldivers 2 Galactic War Companion

WarDesk is a self-hosted companion app for the Helldivers 2 galactic war. Milestone M1 implements the live ingestion pipe: a single FastAPI backend worker polls the community API, stores normalized domain models in an in-process TTL cache, and serves a React/Vite galaxy map exclusively from WarDesk endpoints. Milestone M2 layers optional Postgres + TimescaleDB persistence, history bootstrap, and liberation derivation on top; if `DATABASE_URL` is unset, the M1 cache-only path still runs.

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

Postgres + TimescaleDB are optional for M2 persistence. Redis, Anthropic, and Steam API credentials remain optional.

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
- `GET /api/v1/planets/{index}/history`
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

### Optional local Postgres + TimescaleDB persistence

M2 assumes a native local Postgres instance; no Docker Compose or container is provided. Leave `DATABASE_URL` unset to skip persistence gracefully and keep the M1 cache-only app running. To enable snapshots and derived fields:

1. Install Postgres and TimescaleDB locally. On Debian/Ubuntu, install PostgreSQL from the distro or PostgreSQL apt repository, then install the TimescaleDB package matching your Postgres major version. On macOS, `brew install postgresql@16 timescaledb` is the simplest path.
2. Create the role and database:

   ```bash
   createuser --pwprompt wardesk
   createdb --owner=wardesk wardesk
   ```

3. Enable TimescaleDB for the database as a superuser:

   ```bash
   psql -d wardesk -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
   ```

4. Configure the backend connection string in `backend/.env`:

   ```env
   DATABASE_URL=postgresql+asyncpg://wardesk:wardesk@localhost:5432/wardesk
   TRAINING_MANUAL_BASE_URL=https://helldiverstrainingmanual.com
   ```

5. Apply migrations:

   ```bash
   cd backend
   alembic upgrade head
   ```

With the database configured, the ingest worker writes one `planet_snapshots` batch per successful planet refresh, backfills recent Training Manual history idempotently on first run, and `GET /api/v1/planets/{index}` includes DB-derived liberation trend, rate, decay, ETA, and confidence.

## Project layout

```text
backend/app/main.py                 FastAPI app factory and lifespan
backend/app/cache.py                Cache interface and in-process TTL cache
backend/app/clients/base.py         Shared async httpx client with headers and backoff
backend/app/clients/sources/        Upstream source adapters
backend/app/ingest/worker.py        Scheduled ingest loop into cache
backend/app/models/domain.py        Canonical WarDesk API models
backend/alembic/                     Alembic migrations for optional TimescaleDB persistence
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
