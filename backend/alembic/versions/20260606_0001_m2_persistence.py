"""M2 persistence schema with TimescaleDB snapshots.

Revision ID: 20260606_0001
Revises:
Create Date: 2026-06-06 00:00:00
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "20260606_0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.create_table(
        "planets_static",
        sa.Column("index", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("sector", sa.String(length=120), nullable=False),
        sa.Column("biome", sa.JSON(), nullable=True),
        sa.Column("position_x", sa.Float(), nullable=False),
        sa.Column("position_y", sa.Float(), nullable=False),
        sa.Column("waypoints", sa.JSON(), nullable=False),
        sa.Column("disabled", sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint("index"),
    )
    op.create_table(
        "planet_snapshots",
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("planet_index", sa.Integer(), nullable=False),
        sa.Column("health", sa.BigInteger(), nullable=False),
        sa.Column("max_health", sa.BigInteger(), nullable=False),
        sa.Column("owner", sa.Integer(), nullable=False),
        sa.Column("players", sa.Integer(), nullable=False),
        sa.Column("regen_per_second", sa.Float(), nullable=False),
        sa.Column("liberation_pct", sa.Float(), nullable=False),
        sa.Column("campaign_type", sa.Integer(), nullable=True),
        sa.Column("impact_multiplier", sa.Float(), nullable=False),
        sa.ForeignKeyConstraint(["planet_index"], ["planets_static.index"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ts", "planet_index"),
    )
    op.create_index("ix_planet_snapshots_planet_ts", "planet_snapshots", ["planet_index", "ts"])
    op.execute("SELECT create_hypertable('planet_snapshots', 'ts', if_not_exists => TRUE)")
    op.create_table(
        "orders",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("briefing", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("type", sa.Integer(), nullable=False),
        sa.Column("flags", sa.Integer(), nullable=False),
        sa.Column("expiration", sa.DateTime(timezone=True), nullable=False),
        sa.Column("progress", sa.JSON(), nullable=False),
        sa.Column("tasks", sa.JSON(), nullable=False),
        sa.Column("rewards", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "dispatches",
        sa.Column("id", sa.BigInteger(), nullable=False),
        sa.Column("published", sa.DateTime(timezone=True), nullable=False),
        sa.Column("type", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("id", name="uq_dispatches_id"),
    )


def downgrade() -> None:
    op.drop_table("dispatches")
    op.drop_table("orders")
    op.drop_index("ix_planet_snapshots_planet_ts", table_name="planet_snapshots")
    op.drop_table("planet_snapshots")
    op.drop_table("planets_static")
