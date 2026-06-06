from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_cache, get_upstream
from app.cache import Cache
from app.clients.upstream import UpstreamClient
from app.ingest.worker import CACHE_LAST_INGEST
from app.models.domain import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/healthz", response_model=HealthResponse)
async def healthz(cache: Cache = Depends(get_cache), upstream: UpstreamClient = Depends(get_upstream)) -> HealthResponse:
    last = await cache.get(CACHE_LAST_INGEST)
    return HealthResponse(sources=upstream.source_status, last_ingest=last if last is not None else None)
