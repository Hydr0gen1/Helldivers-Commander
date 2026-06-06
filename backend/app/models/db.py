from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any

from sqlalchemy import ARRAY, BigInteger, DateTime, Float, Integer, Text, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

logger = logging.getLogger(__name__)


class Base(DeclarativeBase):
    pass


class PlanetStatic(Base):
    __tablename__ = "planets_static"

    index: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(Text)
    sector: Mapped[str | None] = mapped_column(Text)
    biome: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    position_x: Mapped[float | None] = mapped_column(Float)
    position_y: Mapped[float | None] = mapped_column(Float)
    waypoints: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    max_health: Mapped[int | None] = mapped_column(BigInteger)
    initial_owner: Mapped[int | None] = mapped_column(Integer)


class PlanetSnapshot(Base):
    __tablename__ = "planet_snapshots"

    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    planet_index: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    health: Mapped[int | None] = mapped_column(BigInteger)
    max_health: Mapped[int | None] = mapped_column(BigInteger)
    owner: Mapped[int | None] = mapped_column(Integer)
    players: Mapped[int | None] = mapped_column(BigInteger)
    regen_per_second: Mapped[float | None] = mapped_column(Float)
    liberation_pct: Mapped[float | None] = mapped_column(Float)
    campaign_type: Mapped[int | None] = mapped_column(Integer)
    impact_multiplier: Mapped[float | None] = mapped_column(Float)


class OrderSnapshot(Base):
    __tablename__ = "orders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), primary_key=True)
    title: Mapped[str | None] = mapped_column(Text)
    briefing: Mapped[str | None] = mapped_column(Text)
    expiration: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    tasks: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)
    progress: Mapped[list[int] | None] = mapped_column(ARRAY(Integer))
    rewards: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONB)


class DispatchRecord(Base):
    __tablename__ = "dispatches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    published: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    type: Mapped[int | None] = mapped_column(Integer)
    message: Mapped[str | None] = mapped_column(Text)


class Database:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self.engine: AsyncEngine | None = None
        self.sessionmaker: async_sessionmaker[AsyncSession] | None = None

    @property
    def enabled(self) -> bool:
        return self.sessionmaker is not None

    async def start(self) -> None:
        if not self.database_url:
            logger.info("db_disabled reason=DATABASE_URL_unset")
            return
        try:
            self.engine = create_async_engine(self.database_url, pool_pre_ping=True)
            self.sessionmaker = async_sessionmaker(self.engine, expire_on_commit=False)
            async with self.engine.connect() as connection:
                await connection.execute(text("SELECT 1"))
            logger.info("db_connected url_configured=true")
        except Exception as exc:  # startup boundary: persistence must not break M1 cache-only mode
            logger.warning("db_unavailable persistence=disabled error=%r", exc)
            if self.engine is not None:
                await self.engine.dispose()
            self.engine = None
            self.sessionmaker = None

    async def stop(self) -> None:
        if self.engine is not None:
            await self.engine.dispose()

    @asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self.sessionmaker is None:
            raise RuntimeError("database is not enabled")
        async with self.sessionmaker() as session:
            yield session
