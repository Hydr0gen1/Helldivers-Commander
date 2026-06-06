from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends

from app.api.deps import get_cache
from app.cache import Cache
from app.ingest.worker import CACHE_WAR, cached_or_empty
from app.models.domain import War

router = APIRouter(prefix="/api/v1", tags=["war"])


@router.get("/war", response_model=War)
async def get_war(cache: Cache = Depends(get_cache)) -> War:
    return await cached_or_empty(cache, CACHE_WAR, War(war_id=0, time=datetime.now(timezone.utc)))
