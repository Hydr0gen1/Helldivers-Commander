from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_cache
from app.cache import Cache
from app.ingest.worker import CACHE_CAMPAIGNS, CACHE_PLANETS, cached_or_empty
from app.models.domain import CampaignsResponse, Planet, PlanetsResponse

router = APIRouter(prefix="/api/v1", tags=["planets"])


@router.get("/planets", response_model=PlanetsResponse)
async def get_planets(cache: Cache = Depends(get_cache)) -> PlanetsResponse:
    return await cached_or_empty(cache, CACHE_PLANETS, PlanetsResponse(planets=[]))


@router.get("/planets/{index}", response_model=Planet)
async def get_planet(index: int, cache: Cache = Depends(get_cache)) -> Planet:
    response: PlanetsResponse = await cached_or_empty(cache, CACHE_PLANETS, PlanetsResponse(planets=[]))
    for planet in response.planets:
        if planet.index == index:
            return planet
    raise HTTPException(status_code=404, detail={"error": {"code": "PLANET_NOT_FOUND", "message": f"Planet {index} is not cached"}})


@router.get("/campaigns", response_model=CampaignsResponse)
async def get_campaigns(cache: Cache = Depends(get_cache)) -> dict[str, object]:
    return await cached_or_empty(cache, CACHE_CAMPAIGNS, {"campaigns": []})
