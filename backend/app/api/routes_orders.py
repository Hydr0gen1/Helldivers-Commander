from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.api.deps import get_cache, get_db_sessionmaker
from app.cache import Cache
from app.derive.liberation import LiberationPoint, derive_liberation, liberation_pct
from app.derive.orders import estimate_order_probability, referenced_planet_indices
from app.ingest.worker import CACHE_ORDERS, CACHE_PLANETS, cached_or_empty
from app.models.db import snapshot_history
from app.models.domain import OrdersResponse, Planet, PlanetsResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["orders"])


@router.get("/orders/current", response_model=OrdersResponse)
async def get_current_orders(
    cache: Cache = Depends(get_cache),
    sessionmaker: async_sessionmaker[AsyncSession] | None = Depends(get_db_sessionmaker),
) -> OrdersResponse:
    response: OrdersResponse = await cached_or_empty(cache, CACHE_ORDERS, OrdersResponse(orders=[]))
    for order in response.orders:
        order.win_probability = None

    if sessionmaker is None or not response.orders:
        return response

    planets_response: PlanetsResponse = await cached_or_empty(cache, CACHE_PLANETS, PlanetsResponse(planets=[]))
    planets = {planet.index: planet for planet in planets_response.planets}
    now = datetime.now(timezone.utc)

    try:
        async with sessionmaker() as session:
            for order in response.orders:
                planet_eta_hours: dict[int, float | None] = {}
                for planet_index in referenced_planet_indices(order):
                    planet = planets.get(planet_index)
                    if planet is None:
                        planet_eta_hours[planet_index] = None
                        continue
                    planet_eta_hours[planet_index] = await _planet_eta_hours(session, planet)

                order.win_probability = estimate_order_probability(
                    order,
                    planets=planets,
                    planet_eta_hours=planet_eta_hours,
                    now=now,
                )
    except Exception as exc:
        logger.warning("order_probability_lookup_failed error=%r", exc)
        for order in response.orders:
            order.win_probability = None

    return response


async def _planet_eta_hours(session: AsyncSession, planet: Planet) -> float | None:
    history = await snapshot_history(session, planet.index)
    if not history:
        return None

    derived = derive_liberation(
        [LiberationPoint(ts=row.ts, liberation_pct=row.liberation_pct, players=row.players) for row in history],
        current_liberation_pct=liberation_pct(planet.health, planet.max_health),
        regen_per_second=planet.regen_per_second,
        max_health=planet.max_health,
    )
    return derived.eta_hours
