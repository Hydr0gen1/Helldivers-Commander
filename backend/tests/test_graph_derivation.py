from __future__ import annotations

import asyncio

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api import routes_graph
from app.cache import InProcTTLCache
from app.derive.graph import find_gambits
from app.ingest.worker import CACHE_CAMPAIGNS, CACHE_PLANETS
from app.models.domain import Planet, PlanetsResponse


def planet(index: int, *, owner: int = 1, health: int = 1_000, waypoints: list[int] | None = None, attacking: list[int] | None = None, event: dict[str, object] | None = None) -> Planet:
    names = {1: "SUPER_EARTH", 2: "TERMINIDS", 3: "AUTOMATONS", 4: "ILLUMINATE"}
    return Planet(
        index=index,
        name=f"Planet {index}",
        owner=owner,
        current_owner=names.get(owner, "UNKNOWN"),
        health=health,
        max_health=1_000,
        waypoints=waypoints or [],
        attacking=attacking or [],
        event=event,
    )


def kinds(planets: list[Planet], campaigns: list[dict[str, object]] | None = None) -> set[str]:
    return {gambit.kind for gambit in find_gambits(planets, campaigns)}


def test_fully_surrounded_enemy_planet_yields_siege() -> None:
    planets = [
        planet(1, waypoints=[2]),
        planet(2, owner=3, waypoints=[1, 3]),
        planet(3, waypoints=[2]),
    ]

    gambits = find_gambits(planets)

    assert [g.kind for g in gambits] == ["SIEGE"]
    assert gambits[0].target_index == 2


def test_surrounded_enemy_planet_with_active_campaign_is_not_siege() -> None:
    planets = [
        planet(1, waypoints=[2]),
        planet(2, owner=3, waypoints=[1, 3]),
        planet(3, waypoints=[2]),
    ]

    assert "SIEGE" not in kinds(planets, [{"planetIndex": 2}])
    assert "SIEGE" in kinds(planets)


def test_defense_with_weaker_source_yields_gambit() -> None:
    planets = [
        planet(10, owner=3, health=250, waypoints=[20], attacking=[20]),
        planet(20, owner=1, health=900, waypoints=[10], event={"health": 500}),
    ]

    gambits = find_gambits(planets, [{"planetIndex": 20, "health": 500}])

    assert [g.kind for g in gambits] == ["GAMBIT"]
    assert gambits[0].source_index == 10
    assert gambits[0].target_index == 20


def test_articulation_planet_on_active_front_yields_chokepoint() -> None:
    planets = [
        planet(1, owner=1, waypoints=[2]),
        planet(2, owner=1, waypoints=[1, 3, 4]),
        planet(3, owner=3, waypoints=[2], attacking=[2]),
        planet(4, owner=1, waypoints=[2]),
    ]

    gambits = find_gambits(planets)

    assert any(g.kind == "CHOKEPOINT" and g.target_index == 2 for g in gambits)


def test_normal_connected_front_does_not_emit_spurious_detections() -> None:
    planets = [
        planet(1, owner=1, waypoints=[2, 3]),
        planet(2, owner=1, waypoints=[1, 3]),
        planet(3, owner=3, waypoints=[1, 2], attacking=[1]),
    ]

    assert kinds(planets) == set()


def test_graph_gambits_endpoint_uses_cached_planets_and_campaigns() -> None:
    cache = InProcTTLCache()
    planets = [
        planet(10, owner=3, health=250, waypoints=[20], attacking=[20]),
        planet(20, owner=1, health=900, waypoints=[10], event={"health": 500}),
    ]
    asyncio.run(cache.set(CACHE_PLANETS, PlanetsResponse(planets=planets), ttl_seconds=90))
    asyncio.run(cache.set(CACHE_CAMPAIGNS, {"campaigns": [{"planetIndex": 20, "health": 500}]}, ttl_seconds=90))

    app = FastAPI()
    app.include_router(routes_graph.router)
    app.dependency_overrides[routes_graph.get_cache] = lambda: cache

    response = TestClient(app).get("/api/v1/graph/gambits")

    assert response.status_code == 200
    assert response.json()["gambits"][0]["kind"] == "GAMBIT"
