from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_cache
from app.cache import Cache
from app.ingest.worker import CACHE_DISPATCHES, cached_or_empty
from app.models.domain import DispatchesResponse

router = APIRouter(prefix="/api/v1", tags=["dispatches"])


@router.get("/dispatches", response_model=DispatchesResponse)
async def get_dispatches(since: datetime | None = Query(default=None), cache: Cache = Depends(get_cache)) -> DispatchesResponse:
    response: DispatchesResponse = await cached_or_empty(cache, CACHE_DISPATCHES, DispatchesResponse(dispatches=[]))
    if since is None:
        return response
    return DispatchesResponse(dispatches=[dispatch for dispatch in response.dispatches if dispatch.published >= since])
