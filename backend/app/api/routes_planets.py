from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import get_cache, get_db_sessionmaker
from app.cache import Cache
from app.derive.liberation import LiberationPoint, derive_liberation
from app.ingest.worker import CACHE_CAMPAIGNS, CACHE_PLANETS, cached_or_empty
from app.models.db import snapshot_history
from app.models.domain import (
    CampaignsResponse,
    Derived,
    Planet,
    PlanetHistoryPoint,
    PlanetHistoryResponse,
    PlanetsResponse,
)

router = APIRouter(prefix="/api/v1", tags=["planets"])


@router.get("/planets", response_model=PlanetsResponse)
async def get_planets(cache: Cache = Depends(get_cache)) -> PlanetsResponse:
    return await cached_or_empty(cache, CACHE_PLANETS, PlanetsResponse(planets=[]))


@router.get("/planets/{index}", response_model=Planet)
async def get_planet(
    index: int,
    cache: Cache = Depends(get_cache),
    sessionmaker: async_sessionmaker[AsyncSession] | None = Depends(get_db_sessionmaker),
) -> Planet:
    response: PlanetsResponse = await cached_or_empty(cache, CACHE_PLANETS, PlanetsResponse(planets=[]))
    for planet in response.planets:
        if planet.index == index:
            if sessionmaker is not None:
                async with sessionmaker() as session:
                    history = await snapshot_history(session, index)
                if history:
                    derived = derive_liberation(
                        [LiberationPoint(ts=row.ts, liberation_pct=row.liberation_pct, players=row.players) for row in history],
                        current_liberation_pct=history[-1].liberation_pct,
                        regen_per_second=history[-1].regen_per_second,
                        max_health=history[-1].max_health,
                    )
                    planet.derived = Derived(
                        lib_rate_pct_per_hr=derived.lib_rate_pct_per_hr,
                        decay_pct_per_hr=derived.decay_pct_per_hr,
                        eta_hours=derived.eta_hours,
                        confidence=derived.confidence,
                        trend=derived.trend,
                    )
            return planet
    raise HTTPException(status_code=404, detail={"error": {"code": "PLANET_NOT_FOUND", "message": f"Planet {index} is not cached"}})


@router.get("/planets/{index}/history", response_model=PlanetHistoryResponse)
async def get_planet_history(
    index: int,
    sessionmaker: async_sessionmaker[AsyncSession] | None = Depends(get_db_sessionmaker),
) -> PlanetHistoryResponse:
    if sessionmaker is None:
        return PlanetHistoryResponse(history=[])
    async with sessionmaker() as session:
        rows = await snapshot_history(session, index)
    return PlanetHistoryResponse(
        history=[PlanetHistoryPoint(ts=row.ts, liberation_pct=row.liberation_pct, players=row.players) for row in rows]
    )


@router.get("/campaigns", response_model=CampaignsResponse)
async def get_campaigns(cache: Cache = Depends(get_cache)) -> dict[str, object]:
    return await cached_or_empty(cache, CACHE_CAMPAIGNS, {"campaigns": []})
