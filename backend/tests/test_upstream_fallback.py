from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

import httpx
import pytest

from app.clients.upstream import UpstreamClient
from app.config import Settings
from app.models.domain import Statistics, War


class FakeSource:
    def __init__(self, name: str, *, fail: bool = False) -> None:
        self.name = name
        self.fail = fail
        self.calls = 0

    async def resolve_war_id(self) -> int:
        return 801

    async def fetch_war(self) -> Any:
        self.calls += 1
        if self.fail:
            raise httpx.ConnectError("boom")
        return {"warId": 801, "time": "2026-06-06T00:00:00Z", "impactMultiplier": 1.5, "statistics": {}}

    def normalize_war(self, raw: Any, *, resolved_war_id: int | None = None) -> War:
        data = raw if isinstance(raw, dict) else {}
        return War(
            war_id=int(data.get("warId", resolved_war_id or 0)),
            time=datetime.fromisoformat(str(data["time"]).replace("Z", "+00:00")).astimezone(timezone.utc),
            impact_multiplier=float(data.get("impactMultiplier", 1.0)),
            statistics=Statistics(),
        )

    async def fetch_planets(self) -> Any:
        return []

    async def fetch_planet(self, index: int) -> Any:
        return {}

    async def fetch_assignments(self) -> Any:
        return []

    async def fetch_dispatches(self) -> Any:
        return []

    async def fetch_campaigns(self) -> Any:
        return []

    def normalize_planets(self, raw: Any) -> list[Any]:
        return []

    def normalize_planet(self, raw: Any) -> Any:
        return None

    def normalize_assignments(self, raw: Any) -> list[Any]:
        return []

    def normalize_dispatches(self, raw: Any) -> list[Any]:
        return []

    def normalize_campaigns(self, raw: Any) -> list[dict[str, Any]]:
        return []


@pytest.mark.asyncio
async def test_community_failure_falls_back_to_diveharder_domain_model() -> None:
    community = FakeSource("community", fail=True)
    diveharder = FakeSource("diveharder")
    raw = FakeSource("raw")
    client = UpstreamClient(community, diveharder, raw)  # type: ignore[arg-type]

    war = await client.get_war()

    assert war.war_id == 801
    assert war.impact_multiplier == 1.5
    assert community.calls == 1
    assert diveharder.calls == 1
    assert raw.calls == 0
    assert client.source_status == {"community": "down", "diveharder": "up", "raw": "down"}


@pytest.mark.asyncio
async def test_breaker_opens_after_consecutive_failures_and_recovers_after_cooldown() -> None:
    settings = Settings(upstream_breaker_failure_threshold=2, upstream_breaker_cooldown_seconds=1)
    community = FakeSource("community", fail=True)
    diveharder = FakeSource("diveharder")
    client = UpstreamClient(community, diveharder, settings=settings)  # type: ignore[arg-type]

    await client.get_war()
    await client.get_war()
    assert client.source_status["community"] == "open"

    await client.get_war()
    assert community.calls == 2

    breaker = client._breakers["community"]  # exercise the cooldown transition without slowing the suite
    assert breaker.opened_at is not None
    breaker.opened_at = breaker.opened_at.replace(year=breaker.opened_at.year - 1)
    community.fail = False

    war = await client.get_war()

    assert war.war_id == 801
    assert community.calls == 3
    assert client.source_status["community"] == "up"
