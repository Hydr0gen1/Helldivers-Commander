# WarDesk — Helldivers 2 Galactic War Companion

WarDesk is a self-hosted companion app for the Helldivers 2 galactic war. A single FastAPI backend worker polls the community API, stores normalized domain models in an in-process TTL cache, optionally persists snapshots to Postgres + TimescaleDB, and serves a React/Vite galaxy map exclusively from WarDesk endpoints. If `DATABASE_URL` is unset, the cache-only path still runs and persistence is skipped gracefully.

Docker Compose is the primary supported way to run WarDesk. The default Compose stack starts TimescaleDB, applies Alembic migrations before the backend serves traffic, starts the FastAPI API, and serves the Vite frontend. The browser intentionally calls only WarDesk routes (`/api`, `/healthz`, `/sse`) and never calls upstream Helldivers services directly.

## What is included

- FastAPI backend under `backend/app` with `/api/v1` routes for war state, planets, single planets, campaigns, current orders, dispatches, briefing, gambits, health, and SSE updates.
- Community upstream adapter for `https://api.helldivers2.dev`, including live war-ID resolution and the required `X-Super-*`/`User-Agent` headers.
- APScheduler ingest loop using one upstream request per data type per tick and an in-process TTL cache.
- Optional Postgres + TimescaleDB snapshot persistence, Training Manual history bootstrap, and DB-derived liberation trend/rate/decay/ETA fields.
- Pydantic v2 domain models that serialize API responses with camelCase fields.
- Vite + React 18 + TypeScript + react-three-fiber frontend rendering planets and supply lines from WarDesk endpoints only.

## Prerequisites

- Docker Engine with Docker Compose v2

For native/local fallback development only, install Python 3.12, Node.js 20+, npm 10+, and an external Postgres + TimescaleDB instance if you want persistence.

## Getting started with Docker (default)

1. Copy the Compose environment template:

   ```bash
   cp .env.example .env
   ```

2. Edit `.env` as needed. The defaults are enough to boot the full local stack:

   ```env
   POSTGRES_USER=wardesk
   POSTGRES_PASSWORD=wardesk
   POSTGRES_DB=wardesk
   DATABASE_URL=postgresql+asyncpg://wardesk:wardesk@db:5432/wardesk
   WARDESK_CONTACT=you@example.com
   ```

   `DATABASE_URL` must use the Compose service name `db`, not `localhost`, because it is consumed from inside the backend container.

3. Start the full development stack:

   ```bash
   docker compose up --build
   ```

Compose starts these services on a shared network:

| Service | Image/build | Host port | Purpose |
| --- | --- | --- | --- |
| `db` | `timescale/timescaledb:latest-pg16` | `5432` | Postgres + TimescaleDB with a `pg_isready` healthcheck |
| `backend` | `backend/Dockerfile` dev target | `8000` | FastAPI API with `uvicorn --reload` |
| `frontend` | `frontend/Dockerfile` dev target | `5173` | Vite dev server with HMR |

The backend waits for the database healthcheck, runs `alembic upgrade head`, then starts `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`. Backend source is bind-mounted for hot reload. The frontend source is bind-mounted for Vite HMR and proxies `/api`, `/healthz`, and `/sse` to `http://backend:8000`.

Open:

- Frontend galaxy map: <http://127.0.0.1:5173>
- Backend health: <http://127.0.0.1:8000/healthz>
- API example: <http://127.0.0.1:8000/api/v1/planets>

### Persistence and restarts

TimescaleDB data is stored in the named Docker volume `wardesk_pgdata`, so snapshot history survives container restarts and `docker compose down && docker compose up`.

Useful commands:

```bash
# Stop containers but keep snapshot history
docker compose down

# Stop containers and delete snapshot history
docker compose down -v

# Follow backend logs
docker compose logs -f backend
```

### Optional environment passthroughs

The Compose file passes these optional credentials through to the backend if present in `.env`:

```env
ANTHROPIC_API_KEY=
STEAM_API_KEY=
```

Leave them blank to disable related optional integrations. `WARDESK_CONTACT` is sent in every upstream request as `X-Super-Contact` and in the `User-Agent` string.

### Production-ish frontend image

The frontend Dockerfile includes a production build target that compiles static assets and serves them through nginx. Run it with the `prod` profile:

```bash
docker compose --profile prod up --build frontend-prod backend db
```

The nginx container serves the built frontend on <http://127.0.0.1:8080> by default and proxies `/api`, `/healthz`, and `/sse` to the backend service so the browser still never calls upstream services directly.

## API endpoints

Useful endpoints:

- `GET /healthz`
- `GET /api/v1/war`
- `GET /api/v1/planets`
- `GET /api/v1/planets/{index}`
- `GET /api/v1/planets/{index}/history`
- `GET /api/v1/orders/current`
- `GET /api/v1/dispatches`
- `GET /sse`

## Native/local development fallback

Docker is the default and documented path. Use this fallback only when you intentionally want to run processes outside Compose.

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev]'
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Leave `DATABASE_URL` unset to skip persistence gracefully. To enable snapshots and derived fields outside Docker, run an external Postgres + TimescaleDB instance, create a `wardesk` database, configure a local connection string, and apply migrations:

```bash
export DATABASE_URL=postgresql+asyncpg://wardesk:wardesk@localhost:5432/wardesk
cd backend
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev -- --host 0.0.0.0
```

The native Vite dev server defaults to proxying `/api`, `/healthz`, and `/sse` to `http://127.0.0.1:8000`. Override `VITE_BACKEND_ORIGIN` if your backend is elsewhere.

## Project layout

```text
docker-compose.yml                  Docker-first dev/prod-ish orchestration
.env.example                         Compose environment template
backend/Dockerfile                   Python 3.12 slim backend image
backend/docker-entrypoint.sh         Idempotent migration-before-start entrypoint
backend/app/main.py                  FastAPI app factory and lifespan
backend/app/cache.py                 Cache interface and in-process TTL cache
backend/app/clients/sources/         Upstream source adapters
backend/app/ingest/worker.py         Scheduled ingest loop into cache and optional DB persistence
backend/app/models/domain.py         Canonical WarDesk API models
backend/alembic/                     Alembic migrations for optional TimescaleDB persistence
frontend/Dockerfile                  Vite dev image and nginx production image
frontend/nginx.conf                  Production-ish static server and API proxy
frontend/src/api/                    Typed WarDesk API client and model mirror
frontend/src/three/                  Galaxy map, planets, and supply lines
frontend/src/components/             Panels and war UI widgets
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
