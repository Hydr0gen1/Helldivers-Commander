from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import get_cache
from app.cache import Cache
from app.ingest.worker import CACHE_ORDERS, cached_or_empty
from app.models.domain import OrdersResponse

router = APIRouter(prefix="/api/v1", tags=["orders"])


@router.get("/orders/current", response_model=OrdersResponse)
async def get_current_orders(cache: Cache = Depends(get_cache)) -> OrdersResponse:
    return await cached_or_empty(cache, CACHE_ORDERS, OrdersResponse(orders=[]))
