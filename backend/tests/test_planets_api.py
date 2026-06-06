from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api import routes_planets
from app.cache import InProcTTLCache
from app.ingest.worker import CACHE_PLANETS
from app.models.domain import Planet, PlanetsResponse


class FailingSession:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


class FailingSessionmaker:
    def __call__(self) -> FailingSession:
        return FailingSession()


@pytest.fixture
def planets_app(monkeypatch: pytest.MonkeyPatch) -> tuple[TestClient, InProcTTLCache]:
    cache = InProcTTLCache()
    asyncio.run(
        cache.set(
            CACHE_PLANETS,
            PlanetsResponse(planets=[Planet(index=7, name="Mort", liberation_pct=42.0)]),
            ttl_seconds=90,
        )
    )

    app = FastAPI()
    app.include_router(routes_planets.router)
    app.dependency_overrides[routes_planets.get_cache] = lambda: cache
    app.dependency_overrides[routes_planets.get_db_sessionmaker] = lambda: FailingSessionmaker()
    return TestClient(app), cache


def test_planet_detail_degrades_when_snapshot_query_raises(
    planets_app: tuple[TestClient, InProcTTLCache], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _cache = planets_app

    async def fail_snapshot_history(session: object, planet_index: int, limit: int = 288) -> list[object]:
        raise OSError("database unavailable")

    monkeypatch.setattr(routes_planets, "snapshot_history", fail_snapshot_history)

    response = client.get("/api/v1/planets/7")

    assert response.status_code == 200
    body = response.json()
    assert body["index"] == 7
    assert body["name"] == "Mort"
    assert body["derived"] is None


def test_planet_history_degrades_when_snapshot_query_raises(
    planets_app: tuple[TestClient, InProcTTLCache], monkeypatch: pytest.MonkeyPatch
) -> None:
    client, _cache = planets_app

    async def fail_snapshot_history(session: object, planet_index: int, limit: int = 288) -> list[object]:
        raise OSError("database unavailable")

    monkeypatch.setattr(routes_planets, "snapshot_history", fail_snapshot_history)

    response = client.get("/api/v1/planets/7/history")

    assert response.status_code == 200
    assert response.json() == {"history": []}
