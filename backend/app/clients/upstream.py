from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Awaitable, Callable, Protocol, TypeVar

import httpx
from pydantic import ValidationError

from app.clients.sources.community import CommunitySource
from app.config import Settings
from app.models.domain import Dispatch, Order, Planet, War

logger = logging.getLogger(__name__)
T = TypeVar("T")


class SourceFailure(RuntimeError):
    pass


class AllSourcesDown(SourceFailure):
    pass


class SourceAdapter(Protocol):
    name: str

    async def resolve_war_id(self) -> int: ...
    async def fetch_war(self) -> Any: ...
    async def fetch_planets(self) -> Any: ...
    async def fetch_planet(self, index: int) -> Any: ...
    async def fetch_assignments(self) -> Any: ...
    async def fetch_dispatches(self) -> Any: ...
    async def fetch_campaigns(self) -> Any: ...
    def normalize_war(self, raw: Any, *, resolved_war_id: int | None = None) -> War: ...
    def normalize_planets(self, raw: Any) -> list[Planet]: ...
    def normalize_planet(self, raw: Any) -> Planet: ...
    def normalize_assignments(self, raw: Any) -> list[Order]: ...
    def normalize_dispatches(self, raw: Any) -> list[Dispatch]: ...
    def normalize_campaigns(self, raw: Any) -> list[dict[str, Any]]: ...


@dataclass
class CircuitBreaker:
    failure_threshold: int
    cooldown_seconds: int
    consecutive_failures: int = 0
    opened_at: datetime | None = None
    last_state: str = "down"

    def health(self, now: datetime) -> str:
        if self.opened_at is not None:
            if now - self.opened_at < timedelta(seconds=self.cooldown_seconds):
                return "open"
            return "down"
        return self.last_state

    def allow_call(self, now: datetime) -> bool:
        return self.opened_at is None or now - self.opened_at >= timedelta(seconds=self.cooldown_seconds)

    def record_success(self) -> None:
        self.consecutive_failures = 0
        self.opened_at = None
        self.last_state = "up"

    def record_failure(self, now: datetime) -> None:
        self.consecutive_failures += 1
        self.last_state = "down"
        if self.consecutive_failures >= self.failure_threshold:
            self.opened_at = now
            self.last_state = "open"


class UpstreamClient:
    def __init__(
        self,
        community: CommunitySource,
        diveharder: SourceAdapter | None = None,
        raw: SourceAdapter | None = None,
        settings: Settings | None = None,
    ) -> None:
        self._sources: list[SourceAdapter] = [source for source in (community, diveharder, raw) if source is not None]
        threshold = settings.upstream_breaker_failure_threshold if settings else 3
        cooldown = settings.upstream_breaker_cooldown_seconds if settings else 60
        self._breakers = {source.name: CircuitBreaker(threshold, cooldown) for source in self._sources}
        self.war_id: int | None = None

    @property
    def source_status(self) -> dict[str, str]:
        now = datetime.now(timezone.utc)
        return {source.name: self._breakers[source.name].health(now) for source in self._sources}

    async def resolve_war_id(self) -> int:
        result = await self._with_fallback("war_id", lambda source: source.resolve_war_id())
        self.war_id = result
        for source in self._sources:
            if hasattr(source, "_war_id"):
                setattr(source, "_war_id", result)
        return result

    async def get_war(self) -> War:
        return await self._with_fallback(
            "war",
            lambda source: self._fetch_and_normalize(source, source.fetch_war, lambda raw: source.normalize_war(raw, resolved_war_id=self.war_id)),
        )

    async def get_planets(self) -> list[Planet]:
        return await self._with_fallback(
            "planets",
            lambda source: self._fetch_and_normalize(source, source.fetch_planets, source.normalize_planets),
        )

    async def get_planet(self, index: int) -> Planet | None:
        try:
            return await self._with_fallback(
                "planet",
                lambda source: self._fetch_and_normalize(source, lambda: source.fetch_planet(index), source.normalize_planet),
            )
        except AllSourcesDown:
            return None

    async def get_orders(self) -> list[Order]:
        return await self._with_fallback(
            "orders",
            lambda source: self._fetch_and_normalize(source, source.fetch_assignments, source.normalize_assignments),
        )

    async def get_dispatches(self) -> list[Dispatch]:
        return await self._with_fallback(
            "dispatches",
            lambda source: self._fetch_and_normalize(source, source.fetch_dispatches, source.normalize_dispatches),
        )

    async def get_campaigns(self) -> list[dict[str, object]]:
        return await self._with_fallback(
            "campaigns",
            lambda source: self._fetch_and_normalize(source, source.fetch_campaigns, source.normalize_campaigns),
        )

    async def _fetch_and_normalize(self, source: SourceAdapter, fetch: Callable[[], Awaitable[Any]], normalize: Callable[[Any], T]) -> T:
        raw = await fetch()
        return normalize(raw)

    async def _with_fallback(self, data_type: str, call_for_source: Callable[[SourceAdapter], Awaitable[T]]) -> T:
        failures: list[str] = []
        for source in self._sources:
            breaker = self._breakers[source.name]
            now = datetime.now(timezone.utc)
            if not breaker.allow_call(now):
                failures.append(f"{source.name}:open")
                logger.warning("source_breaker_open source=%s data_type=%s", source.name, data_type)
                continue
            try:
                result = await call_for_source(source)
                breaker.record_success()
                return result
            except (httpx.HTTPError, ValidationError, TypeError, ValueError) as exc:
                breaker.record_failure(datetime.now(timezone.utc))
                failures.append(f"{source.name}:{exc!r}")
                logger.warning("source_call_failed source=%s data_type=%s error=%r", source.name, data_type, exc)
        raise AllSourcesDown(f"all upstream sources down for {data_type}: {'; '.join(failures)}")
