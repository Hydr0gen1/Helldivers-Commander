from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select

from app.api.deps import get_cache, get_db
from app.cache import Cache
from app.derive.liberation import (
    SnapshotPoint,
    confidence,
    decay_pct_per_hr,
    eta_hours,
    lib_rate,
    trend,
)
from app.ingest.worker import CACHE_CAMPAIGNS, CACHE_PLANETS, cached_or_empty
from app.models.db import Database, PlanetSnapshot
from app.models.domain import CampaignsResponse, Derived, HistoryPoint, HistoryResponse, Planet, PlanetsResponse

router = APIRouter(prefix="/api/v1", tags=["planets"])


@router.get("/planets", response_model=PlanetsResponse)
async def get_planets(cache: Cache = Depends(get_cache)) -> PlanetsResponse:
    return await cached_or_empty(cache, CACHE_PLANETS, PlanetsResponse(planets=[]))


@router.get("/planets/{index}", response_model=Planet)
async def get_planet(index: int, cache: Cache = Depends(get_cache), db: Database = Depends(get_db)) -> Planet:
    response: PlanetsResponse = await cached_or_empty(cache, CACHE_PLANETS, PlanetsResponse(planets=[]))
    for planet in response.planets:
        if planet.index == index:
            history = await _history_points(db, index)
            derived = _derive_planet(planet, history)
            return planet.model_copy(update={"derived": derived})
    raise HTTPException(status_code=404, detail={"error": {"code": "PLANET_NOT_FOUND", "message": f"Planet {index} is not cached"}})


@router.get("/planets/{index}/history", response_model=HistoryResponse)
async def get_planet_history(index: int, db: Database = Depends(get_db)) -> HistoryResponse:
    points = await _history_points(db, index, hours=24)
    return HistoryResponse(
        history=[HistoryPoint(ts=point.ts, liberation_pct=point.liberation_pct, players=point.players) for point in points]
    )


@router.get("/campaigns", response_model=CampaignsResponse)
async def get_campaigns(cache: Cache = Depends(get_cache)) -> dict[str, object]:
    return await cached_or_empty(cache, CACHE_CAMPAIGNS, {"campaigns": []})


async def _history_points(db: Database, planet_index: int, *, hours: int = 24) -> list[SnapshotPoint]:
    if not db.enabled or db.sessionmaker is None:
        return []
    since = datetime.now(timezone.utc) - timedelta(hours=hours)
    async with db.sessionmaker() as session:
        result = await session.execute(
            select(PlanetSnapshot.ts, PlanetSnapshot.liberation_pct, PlanetSnapshot.players)
            .where(PlanetSnapshot.planet_index == planet_index, PlanetSnapshot.ts >= since)
            .order_by(PlanetSnapshot.ts.asc())
        )
    return [
        SnapshotPoint(ts=row.ts, liberation_pct=float(row.liberation_pct or 0.0), players=int(row.players or 0))
        for row in result
    ]


def _derive_planet(planet: Planet, history: list[SnapshotPoint]) -> Derived | None:
    if len(history) < 2:
        return None
    rate = lib_rate(history)
    decay = decay_pct_per_hr(planet.regen_per_second, planet.max_health)
    return Derived(
        lib_rate_pct_per_hr=rate,
        decay_pct_per_hr=decay,
        eta_hours=eta_hours(planet.liberation_pct, rate),
        confidence=confidence(history),
        trend=trend(history, rate),
    )
