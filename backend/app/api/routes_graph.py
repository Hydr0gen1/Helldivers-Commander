from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_cache
from app.cache import Cache
from app.derive.graph import find_gambits
from app.ingest.worker import CACHE_PLANETS, cached_or_empty
from app.models.domain import CamelModel, Gambit, PlanetsResponse


class GambitsResponse(CamelModel):
    gambits: list[Gambit]


router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


@router.get("/gambits", response_model=GambitsResponse)
async def get_gambits(cache: Cache = Depends(get_cache)) -> GambitsResponse:
    planets: PlanetsResponse = await cached_or_empty(cache, CACHE_PLANETS, PlanetsResponse(planets=[]))
    return GambitsResponse(gambits=find_gambits(planets.planets))
