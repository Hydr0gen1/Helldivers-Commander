from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from apscheduler.schedulers.asyncio import AsyncIOScheduler

from app.cache import Cache
from app.clients.upstream import UpstreamClient
from app.config import Settings
from app.models.domain import DispatchesResponse, OrdersResponse, PlanetsResponse

logger = logging.getLogger(__name__)

CACHE_WAR = "war"
CACHE_PLANETS = "planets"
CACHE_ORDERS = "orders"
CACHE_DISPATCHES = "dispatches"
CACHE_CAMPAIGNS = "campaigns"
CACHE_LAST_INGEST = "last_ingest"


class IngestWorker:
    def __init__(self, upstream: UpstreamClient, cache: Cache, settings: Settings) -> None:
        self._upstream = upstream
        self._cache = cache
        self._settings = settings
        self._scheduler = AsyncIOScheduler(timezone="UTC")

    async def start(self) -> None:
        await self._resolve_war_id()
        await self.tick_all()
        interval = max(30, self._settings.ingest_interval_seconds)
        self._scheduler.add_job(self.tick_war_and_planets, "interval", seconds=interval, id="war_planets", max_instances=1)
        self._scheduler.add_job(self.tick_campaigns, "interval", seconds=interval, id="campaigns", max_instances=1)
        self._scheduler.add_job(self.tick_orders, "interval", minutes=5, id="orders", max_instances=1)
        self._scheduler.add_job(self.tick_dispatches, "interval", seconds=60, id="dispatches", max_instances=1)
        self._scheduler.start()
        logger.info("ingest_scheduler_started interval_seconds=%s", interval)

    async def stop(self) -> None:
        if self._scheduler.running:
            self._scheduler.shutdown(wait=False)

    async def tick_all(self) -> None:
        await self.tick_war_and_planets()
        await self.tick_campaigns()
        await self.tick_orders()
        await self.tick_dispatches()

    async def tick_war_and_planets(self) -> None:
        try:
            war = await self._upstream.get_war()
            planets = await self._upstream.get_planets()
            await self._cache.set(CACHE_WAR, war, ttl_seconds=90)
            await self._cache.set(CACHE_PLANETS, PlanetsResponse(planets=planets), ttl_seconds=90)
            await self._mark_ingest()
            logger.info("ingest_war_planets_ok planets=%s", len(planets))
        except Exception as exc:  # scheduler boundary: log and keep next tick alive
            logger.warning("ingest_war_planets_failed error=%r", exc)

    async def tick_campaigns(self) -> None:
        try:
            campaigns = await self._upstream.get_campaigns()
            await self._cache.set(CACHE_CAMPAIGNS, {"campaigns": campaigns}, ttl_seconds=90)
            await self._mark_ingest()
            logger.info("ingest_campaigns_ok count=%s", len(campaigns))
        except Exception as exc:  # scheduler boundary: log and keep next tick alive
            logger.warning("ingest_campaigns_failed error=%r", exc)

    async def tick_orders(self) -> None:
        try:
            orders = await self._upstream.get_orders()
            await self._cache.set(CACHE_ORDERS, OrdersResponse(orders=orders), ttl_seconds=330)
            await self._mark_ingest()
            logger.info("ingest_orders_ok count=%s", len(orders))
        except Exception as exc:  # scheduler boundary: log and keep next tick alive
            logger.warning("ingest_orders_failed error=%r", exc)

    async def tick_dispatches(self) -> None:
        try:
            dispatches = await self._upstream.get_dispatches()
            await self._cache.set(CACHE_DISPATCHES, DispatchesResponse(dispatches=dispatches), ttl_seconds=90)
            await self._mark_ingest()
            logger.info("ingest_dispatches_ok count=%s", len(dispatches))
        except Exception as exc:  # scheduler boundary: log and keep next tick alive
            logger.warning("ingest_dispatches_failed error=%r", exc)

    async def _resolve_war_id(self) -> None:
        try:
            war_id = await self._upstream.resolve_war_id()
            logger.info("war_id_resolved war_id=%s", war_id)
        except Exception as exc:  # startup may continue so cached/dev fallback routes still respond gracefully
            logger.warning("war_id_resolution_failed error=%r", exc)

    async def _mark_ingest(self) -> None:
        await self._cache.set(CACHE_LAST_INGEST, datetime.now(timezone.utc), ttl_seconds=None)


async def cached_or_empty(cache: Cache, key: str, default: Any) -> Any:
    value = await cache.get(key)
    return default if value is None else value
