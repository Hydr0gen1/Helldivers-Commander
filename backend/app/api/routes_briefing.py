from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_briefing_generator, get_cache
from app.briefing.llm import BriefingGenerator
from app.cache import Cache
from app.ingest.worker import CACHE_DISPATCHES, cached_or_empty
from app.models.domain import BriefingResponse, DispatchesResponse

router = APIRouter(prefix="/api/v1", tags=["briefing"])


@router.get("/briefing", response_model=BriefingResponse)
async def get_briefing(
    cache: Cache = Depends(get_cache), generator: BriefingGenerator = Depends(get_briefing_generator)
) -> BriefingResponse:
    dispatches: DispatchesResponse = await cached_or_empty(cache, CACHE_DISPATCHES, DispatchesResponse(dispatches=[]))
    return await generator.generate(dispatches.dispatches)
