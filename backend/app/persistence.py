from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import Select, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models.db import PlanetSnapshot
from app.models.domain import Planet, War

logger = logging.getLogger(__name__)


def campaign_type_by_planet(campaigns: list[dict[str, Any]]) -> dict[int, int | None]:
    mapping: dict[int, int | None] = {}
    for campaign in campaigns:
        raw_index = campaign.get("planetIndex", campaign.get("planet_index"))
        if raw_index is None:
            continue
        raw_type = campaign.get("type", campaign.get("campaignType", campaign.get("campaign_type")))
        mapping[int(raw_index)] = int(raw_type) if raw_type is not None else None
    return mapping


def snapshot_rows(war: War, planets: list[Planet], campaigns: list[dict[str, Any]]) -> list[dict[str, Any]]:
    campaign_types = campaign_type_by_planet(campaigns)
    # War.time has already been normalized from war-relative seconds to UTC at the ingest boundary.
    ts = war.time.astimezone(timezone.utc) if war.time.tzinfo is not None else war.time.replace(tzinfo=timezone.utc)
    return [
        {
            "ts": ts,
            "planet_index": planet.index,
            "health": planet.health,
            "max_health": planet.max_health,
            "owner": planet.owner,
            "players": planet.players,
            "regen_per_second": planet.regen_per_second,
            "liberation_pct": planet.liberation_pct,
            "campaign_type": campaign_types.get(planet.index),
            "impact_multiplier": war.impact_multiplier,
        }
        for planet in planets
    ]


async def persist_planet_snapshots(
    sessionmaker: async_sessionmaker[AsyncSession] | None,
    *,
    war: War,
    planets: list[Planet],
    campaigns: list[dict[str, Any]],
) -> int:
    if sessionmaker is None:
        return 0
    rows = snapshot_rows(war, planets, campaigns)
    if not rows:
        return 0
    async with sessionmaker() as session:
        statement = insert(PlanetSnapshot).values(rows).on_conflict_do_nothing(index_elements=["ts", "planet_index"])
        await session.execute(statement)
        await session.commit()
    logger.info("planet_snapshots_persisted rows=%s", len(rows))
    return len(rows)


async def has_snapshots(session: AsyncSession, planet_index: int) -> bool:
    statement: Select[tuple[int]] = select(PlanetSnapshot.planet_index).where(PlanetSnapshot.planet_index == planet_index).limit(1)
    result = await session.execute(statement)
    return result.scalar_one_or_none() is not None


async def insert_history_rows(session: AsyncSession, rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0
    statement = insert(PlanetSnapshot).values(rows).on_conflict_do_nothing(index_elements=["ts", "planet_index"])
    await session.execute(statement)
    await session.commit()
    return len(rows)
