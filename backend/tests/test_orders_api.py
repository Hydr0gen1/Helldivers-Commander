from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from fastapi import FastAPI
from fastapi.testclient import TestClient
import pytest

from app.api import routes_orders
from app.cache import InProcTTLCache
from app.ingest.worker import CACHE_ORDERS, CACHE_PLANETS
from app.models.domain import Order, OrdersResponse, Planet, PlanetsResponse, Task

NOW = datetime(2026, 6, 8, 12, tzinfo=timezone.utc)


class FailingSession:
    async def __aenter__(self) -> object:
        return object()

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        return None


class FailingSessionmaker:
    def __call__(self) -> FailingSession:
        return FailingSession()


def cached_orders_app(sessionmaker: object | None) -> TestClient:
    cache = InProcTTLCache()
    asyncio.run(
        cache.set(
            CACHE_ORDERS,
            OrdersResponse(
                orders=[
                    Order(
                        id=99,
                        title="Liberate Lesath",
                        expiration=NOW + timedelta(hours=48),
                        tasks=[Task(type=11, values=[1, 1, 194], valueTypes=[3, 11, 12])],
                    )
                ]
            ),
            ttl_seconds=90,
        )
    )
    asyncio.run(
        cache.set(
            CACHE_PLANETS,
            PlanetsResponse(planets=[Planet(index=194, name="Lesath", health=500_000, max_health=1_000_000)]),
            ttl_seconds=90,
        )
    )

    app = FastAPI()
    app.include_router(routes_orders.router)
    app.dependency_overrides[routes_orders.get_cache] = lambda: cache
    app.dependency_overrides[routes_orders.get_db_sessionmaker] = lambda: sessionmaker
    return TestClient(app)


def test_orders_current_leaves_win_probability_null_when_db_disabled() -> None:
    client = cached_orders_app(None)

    response = client.get("/api/v1/orders/current")

    assert response.status_code == 200
    assert response.json()["orders"][0]["winProbability"] is None


def test_orders_current_degrades_to_null_when_snapshot_query_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    client = cached_orders_app(FailingSessionmaker())

    async def fail_snapshot_history(session: object, planet_index: int, limit: int = 288) -> list[object]:
        raise OSError("database unavailable")

    monkeypatch.setattr(routes_orders, "snapshot_history", fail_snapshot_history)

    response = client.get("/api/v1/orders/current")

    assert response.status_code == 200
    assert response.json()["orders"][0]["winProbability"] is None
