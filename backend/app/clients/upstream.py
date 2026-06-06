from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Awaitable, Callable, TypeVar

import httpx
from pydantic import ValidationError

from app.clients.sources.community import CommunitySource
from app.models.domain import Dispatch, Order, Planet, War

logger = logging.getLogger(__name__)
T = TypeVar("T")


class UpstreamClient:
    def __init__(self, community: CommunitySource) -> None:
        self._community = community
        self._sources: dict[str, str] = {community.name: "down"}
        self.war_id: int | None = None

    @property
    def source_status(self) -> dict[str, str]:
        return dict(self._sources)

    async def resolve_war_id(self) -> int:
        result = await self._call_source(self._community.name, self._community.resolve_war_id)
        self.war_id = result
        return result

    async def get_war(self) -> War:
        raw = await self._call_source(self._community.name, self._community.fetch_war)
        return self._community.normalize_war(raw)

    async def get_planets(self) -> list[Planet]:
        raw = await self._call_source(self._community.name, self._community.fetch_planets)
        return self._community.normalize_planets(raw)

    async def get_planet(self, index: int) -> Planet | None:
        raw = await self._call_source(self._community.name, lambda: self._community.fetch_planet(index))
        return self._community.normalize_planet(raw)

    async def get_orders(self) -> list[Order]:
        raw = await self._call_source(self._community.name, self._community.fetch_assignments)
        return self._community.normalize_assignments(raw)

    async def get_dispatches(self) -> list[Dispatch]:
        raw = await self._call_source(self._community.name, self._community.fetch_dispatches)
        return self._community.normalize_dispatches(raw)

    async def get_campaigns(self) -> list[dict[str, object]]:
        raw = await self._call_source(self._community.name, self._community.fetch_campaigns)
        return self._community.normalize_campaigns(raw)

    async def _call_source(self, source_name: str, call: Callable[[], Awaitable[T]]) -> T:
        try:
            result = await call()
            self._sources[source_name] = "up"
            return result
        except (httpx.HTTPError, ValidationError, TypeError, ValueError) as exc:
            self._sources[source_name] = "down"
            logger.warning("source_call_failed source=%s at=%s error=%r", source_name, datetime.now(timezone.utc).isoformat(), exc)
            raise
