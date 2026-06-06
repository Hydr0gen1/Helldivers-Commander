from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator

from fastapi import APIRouter, Depends
from sse_starlette.sse import EventSourceResponse

from app.api.deps import get_cache
from app.cache import Cache
from app.ingest.worker import CACHE_PLANETS
from app.models.domain import PlanetsResponse

router = APIRouter(tags=["stream"])


@router.get("/sse")
async def sse(cache: Cache = Depends(get_cache)) -> EventSourceResponse:
    async def events() -> AsyncIterator[dict[str, str]]:
        while True:
            planets = await cache.get(CACHE_PLANETS)
            if isinstance(planets, PlanetsResponse):
                yield {"event": "planets", "data": json.dumps(planets.model_dump(mode="json", by_alias=True))}
            await asyncio.sleep(30)

    return EventSourceResponse(events())
