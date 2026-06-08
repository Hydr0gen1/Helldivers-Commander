from __future__ import annotations

import logging
from datetime import datetime, timezone

import pytest

from app.cache import InProcTTLCache
from app.config import Settings
from app.ingest.worker import CACHE_CAMPAIGNS, IngestWorker
from app.models.domain import Planet, War


class FailingUpstream:
    async def resolve_war_id(self) -> int:
        raise RuntimeError("war id unavailable")

    async def get_war(self) -> object:
        raise RuntimeError("war unavailable")

    async def get_planets(self) -> list[object]:
        raise RuntimeError("planets unavailable")

    async def get_campaigns(self) -> list[dict[str, object]]:
        raise RuntimeError("campaigns unavailable")

    async def get_orders(self) -> list[object]:
        raise RuntimeError("orders unavailable")

    async def get_dispatches(self) -> list[object]:
        raise RuntimeError("dispatches unavailable")


class CampaignUpstream(FailingUpstream):
    async def get_campaigns(self) -> list[dict[str, object]]:
        return [{"planetIndex": 42, "type": 1}]


@pytest.mark.asyncio
async def test_start_logs_and_continues_when_initial_upstream_calls_fail(caplog: pytest.LogCaptureFixture) -> None:
    caplog.set_level(logging.INFO)
    worker = IngestWorker(FailingUpstream(), InProcTTLCache(), Settings(ingest_interval_seconds=30))  # type: ignore[arg-type]

    await worker.start()
    await worker.stop()

    messages = "\n".join(record.message for record in caplog.records)
    assert "war_id_resolution_failed" in messages
    assert "ingest_war_planets_failed" in messages
    assert "ingest_scheduler_started" in messages


@pytest.mark.asyncio
async def test_campaign_tick_populates_campaign_cache() -> None:
    cache = InProcTTLCache()
    worker = IngestWorker(CampaignUpstream(), cache, Settings(ingest_interval_seconds=30))  # type: ignore[arg-type]

    await worker.tick_campaigns()

    assert await cache.get(CACHE_CAMPAIGNS) == {"campaigns": [{"planetIndex": 42, "type": 1}]}


class WarIdCommunity:
    name = "community"

    async def resolve_war_id(self) -> int:
        return 987

    async def fetch_war(self) -> dict[str, object]:
        return {"time": "2026-06-06T00:00:00Z", "impactMultiplier": 1.0, "statistics": {}}

    def normalize_war(self, raw: object, *, resolved_war_id: int | None = None) -> object:
        return {"warId": resolved_war_id}


@pytest.mark.asyncio
async def test_upstream_threads_resolved_war_id_into_war_normalizer() -> None:
    from app.clients.upstream import UpstreamClient

    upstream = UpstreamClient(WarIdCommunity())  # type: ignore[arg-type]

    await upstream.resolve_war_id()
    war = await upstream.get_war()

    assert war == {"warId": 987}


class SnapshotUpstream(FailingUpstream):
    async def get_war(self) -> War:
        return War(war_id=1, time=datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc), impact_multiplier=1.5)

    async def get_planets(self) -> list[Planet]:
        return [Planet(index=7, name="Mort", health=500_000, max_health=1_000_000, liberation_pct=50.0, players=123)]


class RecordingPersistence:
    enabled = False

    def __init__(self) -> None:
        self.calls: list[dict[str, object]] = []

    async def write_planet_tick(self, *, war: War, planets: list[Planet], campaigns: list[dict[str, object]]) -> None:
        self.calls.append({"war": war, "planets": planets, "campaigns": campaigns})

    async def write_orders(self, orders: list[object]) -> None:
        pass

    async def write_dispatches(self, dispatches: list[object]) -> None:
        pass


@pytest.mark.asyncio
async def test_war_planets_tick_writes_snapshot_batch() -> None:
    cache = InProcTTLCache()
    persistence = RecordingPersistence()
    worker = IngestWorker(
        SnapshotUpstream(),
        cache,
        Settings(ingest_interval_seconds=30),
        persistence=persistence,  # type: ignore[arg-type]
    )

    await worker.tick_war_and_planets()

    assert len(persistence.calls) == 1
    call = persistence.calls[0]
    assert call["war"] == War(war_id=1, time=datetime(2026, 6, 6, 12, 0, tzinfo=timezone.utc), impact_multiplier=1.5)
    assert [planet.index for planet in call["planets"]] == [7]
