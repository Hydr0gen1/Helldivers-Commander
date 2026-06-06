from __future__ import annotations

import logging
from collections.abc import AsyncIterator, Sequence
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, Integer, JSON, String, Text, UniqueConstraint, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.models.domain import Dispatch, Order, Planet, War

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class PlanetStatic(Base):
    __tablename__ = "planets_static"

    index: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    sector: Mapped[str] = mapped_column(String(120), nullable=False, default="UNKNOWN")
    biome: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    position_x: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    position_y: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    waypoints: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    disabled: Mapped[bool] = mapped_column(nullable=False, default=False)


class PlanetSnapshot(Base):
    __tablename__ = "planet_snapshots"
    __table_args__ = (
        Index("ix_planet_snapshots_planet_ts", "planet_index", "ts"),
    )

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    planet_index: Mapped[int] = mapped_column(ForeignKey("planets_static.index", ondelete="CASCADE"), primary_key=True)
    health: Mapped[int] = mapped_column(BigInteger, nullable=False)
    max_health: Mapped[int] = mapped_column(BigInteger, nullable=False)
    owner: Mapped[int] = mapped_column(Integer, nullable=False)
    players: Mapped[int] = mapped_column(Integer, nullable=False)
    regen_per_second: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    liberation_pct: Mapped[float] = mapped_column(Float, nullable=False)
    campaign_type: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impact_multiplier: Mapped[float] = mapped_column(Float, nullable=False, default=1.0)


class OrderRecord(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(Text, nullable=False, default="")
    briefing: Mapped[str] = mapped_column(Text, nullable=False, default="")
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    type: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    flags: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expiration: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    progress: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)
    tasks: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    rewards: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False, default=list)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class DispatchRecord(Base):
    __tablename__ = "dispatches"
    __table_args__ = (UniqueConstraint("id", name="uq_dispatches_id"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    published: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    type: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    message: Mapped[str | None] = mapped_column(Text, nullable=True)


def utc_boundary(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def create_engine_and_session(database_url: str) -> tuple[AsyncEngine, async_sessionmaker[AsyncSession]] | None:
    if not database_url:
        logger.info("database_url_unset persistence=disabled")
        return None
    engine = create_async_engine(database_url, pool_pre_ping=True)
    return engine, async_sessionmaker(engine, expire_on_commit=False)


async def session_scope(sessionmaker: async_sessionmaker[AsyncSession]) -> AsyncIterator[AsyncSession]:
    async with sessionmaker() as session:
        async with session.begin():
            yield session


class DatabasePersistence:
    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession] | None) -> None:
        self._sessionmaker = sessionmaker
        self._bootstrapped_planets: set[int] = set()

    @property
    def enabled(self) -> bool:
        return self._sessionmaker is not None

    async def write_planet_tick(
        self,
        *,
        war: War,
        planets: Sequence[Planet],
        campaigns: Sequence[dict[str, Any]] | None = None,
    ) -> None:
        if self._sessionmaker is None:
            logger.info("snapshot_persistence_skipped reason=database_url_unset planets=%s", len(planets))
            return
        ts = utc_boundary(war.time)
        campaign_types = campaign_type_by_planet(campaigns or [])
        async with self._sessionmaker() as session:
            async with session.begin():
                await upsert_planets_static(session, planets)
                await insert_planet_snapshots(
                    session,
                    ts=ts,
                    planets=planets,
                    impact_multiplier=war.impact_multiplier,
                    campaign_types=campaign_types,
                )
        logger.info("snapshot_persistence_ok ts=%s planets=%s", ts.isoformat(), len(planets))

    async def backfill_planet_history(self, planet_index: int, rows: Sequence[dict[str, Any]]) -> int:
        if self._sessionmaker is None:
            logger.info("history_bootstrap_skipped reason=database_url_unset planet_index=%s", planet_index)
            return 0
        if planet_index in self._bootstrapped_planets:
            return 0
        async with self._sessionmaker() as session:
            async with session.begin():
                result = await insert_history_snapshots(session, planet_index=planet_index, rows=rows)
        self._bootstrapped_planets.add(planet_index)
        return result

    async def write_orders(self, orders: Sequence[Order]) -> None:
        if self._sessionmaker is None:
            return
        async with self._sessionmaker() as session:
            async with session.begin():
                await upsert_orders(session, orders)

    async def write_dispatches(self, dispatches: Sequence[Dispatch]) -> None:
        if self._sessionmaker is None:
            return
        async with self._sessionmaker() as session:
            async with session.begin():
                await upsert_dispatches(session, dispatches)


def campaign_type_by_planet(campaigns: Sequence[dict[str, Any]]) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for campaign in campaigns:
        index = campaign.get("planetIndex", campaign.get("planet_index"))
        campaign_type = campaign.get("type")
        if index is not None and campaign_type is not None:
            mapping[int(index)] = int(campaign_type)
    return mapping


async def upsert_planets_static(session: AsyncSession, planets: Sequence[Planet]) -> None:
    if not planets:
        return
    rows = [
        {
            "index": planet.index,
            "name": planet.name,
            "sector": planet.sector,
            "biome": planet.biome,
            "position_x": planet.position.x,
            "position_y": planet.position.y,
            "waypoints": planet.waypoints,
            "disabled": planet.disabled,
        }
        for planet in planets
    ]
    stmt = pg_insert(PlanetStatic).values(rows)
    update_cols = {key: getattr(stmt.excluded, key) for key in rows[0] if key != "index"}
    await session.execute(stmt.on_conflict_do_update(index_elements=["index"], set_=update_cols))


async def insert_planet_snapshots(
    session: AsyncSession,
    *,
    ts: datetime,
    planets: Sequence[Planet],
    impact_multiplier: float,
    campaign_types: dict[int, int] | None = None,
) -> None:
    if not planets:
        return
    campaign_types = campaign_types or {}
    rows = [
        {
            "ts": utc_boundary(ts),
            "planet_index": planet.index,
            "health": planet.health,
            "max_health": planet.max_health,
            "owner": planet.owner,
            "players": planet.players,
            "regen_per_second": planet.regen_per_second,
            "liberation_pct": planet.liberation_pct,
            "campaign_type": campaign_types.get(planet.index),
            "impact_multiplier": impact_multiplier,
        }
        for planet in planets
    ]
    await session.execute(pg_insert(PlanetSnapshot).values(rows).on_conflict_do_nothing(index_elements=["ts", "planet_index"]))


async def insert_history_snapshots(session: AsyncSession, *, planet_index: int, rows: Sequence[dict[str, Any]]) -> int:
    values = []
    for row in rows:
        ts = row.get("ts")
        if not isinstance(ts, datetime):
            continue
        values.append(
            {
                "ts": utc_boundary(ts),
                "planet_index": planet_index,
                "health": int(row.get("health", 0) or 0),
                "max_health": int(row.get("max_health", row.get("maxHealth", 1_000_000)) or 1_000_000),
                "owner": int(row.get("owner", 1) or 1),
                "players": int(row.get("players", row.get("playerCount", 0)) or 0),
                "regen_per_second": float(row.get("regen_per_second", row.get("regenPerSecond", 0.0)) or 0.0),
                "liberation_pct": float(row.get("liberation_pct", row.get("liberationPct", 0.0)) or 0.0),
                "campaign_type": row.get("campaign_type", row.get("campaignType")),
                "impact_multiplier": float(row.get("impact_multiplier", row.get("impactMultiplier", 1.0)) or 1.0),
            }
        )
    if not values:
        return 0
    await session.execute(pg_insert(PlanetSnapshot).values(values).on_conflict_do_nothing(index_elements=["ts", "planet_index"]))
    return len(values)


async def upsert_orders(session: AsyncSession, orders: Sequence[Order]) -> None:
    if not orders:
        return
    now = datetime.now(timezone.utc)
    rows = [
        {
            "id": order.id,
            "title": order.title,
            "briefing": order.briefing,
            "description": order.description,
            "type": order.type,
            "flags": order.flags,
            "expiration": utc_boundary(order.expiration),
            "progress": order.progress,
            "tasks": [task.model_dump(mode="json") for task in order.tasks],
            "rewards": [reward.model_dump(mode="json") for reward in order.rewards],
            "updated_at": now,
        }
        for order in orders
    ]
    stmt = pg_insert(OrderRecord).values(rows)
    await session.execute(stmt.on_conflict_do_update(index_elements=["id"], set_={key: getattr(stmt.excluded, key) for key in rows[0] if key != "id"}))


async def upsert_dispatches(session: AsyncSession, dispatches: Sequence[Dispatch]) -> None:
    if not dispatches:
        return
    rows = [
        {"id": item.id, "published": utc_boundary(item.published), "type": item.type, "message": item.message}
        for item in dispatches
    ]
    stmt = pg_insert(DispatchRecord).values(rows)
    await session.execute(stmt.on_conflict_do_update(index_elements=["id"], set_={key: getattr(stmt.excluded, key) for key in rows[0] if key != "id"}))


async def snapshot_history(session: AsyncSession, planet_index: int, limit: int = 288) -> list[PlanetSnapshot]:
    result = await session.execute(
        select(PlanetSnapshot)
        .where(PlanetSnapshot.planet_index == planet_index)
        .order_by(PlanetSnapshot.ts.desc())
        .limit(limit)
    )
    return list(reversed(result.scalars().all()))
