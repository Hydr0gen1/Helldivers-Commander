"""m2 timescale schema

Revision ID: 0001_m2_timescale
Revises:
Create Date: 2026-06-06
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0001_m2_timescale"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS timescaledb")
    op.create_table(
        "planets_static",
        sa.Column("index", sa.Integer(), primary_key=True),
        sa.Column("name", sa.Text()),
        sa.Column("sector", sa.Text()),
        sa.Column("biome", postgresql.JSONB()),
        sa.Column("position_x", sa.Float()),
        sa.Column("position_y", sa.Float()),
        sa.Column("waypoints", postgresql.ARRAY(sa.Integer())),
        sa.Column("max_health", sa.BigInteger()),
        sa.Column("initial_owner", sa.Integer()),
    )
    op.create_table(
        "planet_snapshots",
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("planet_index", sa.Integer(), nullable=False),
        sa.Column("health", sa.BigInteger()),
        sa.Column("max_health", sa.BigInteger()),
        sa.Column("owner", sa.Integer()),
        sa.Column("players", sa.BigInteger()),
        sa.Column("regen_per_second", sa.Float()),
        sa.Column("liberation_pct", sa.Float()),
        sa.Column("campaign_type", sa.Integer()),
        sa.Column("impact_multiplier", sa.Float()),
        sa.PrimaryKeyConstraint("ts", "planet_index", name="pk_planet_snapshots"),
    )
    op.execute("SELECT create_hypertable('planet_snapshots','ts', if_not_exists => TRUE)")
    op.execute("CREATE INDEX IF NOT EXISTS ix_planet_snapshots_planet_index_ts ON planet_snapshots (planet_index, ts DESC)")
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("snapshot_ts", sa.DateTime(timezone=True), nullable=False),
        sa.Column("title", sa.Text()),
        sa.Column("briefing", sa.Text()),
        sa.Column("expiration", sa.DateTime(timezone=True)),
        sa.Column("tasks", postgresql.JSONB()),
        sa.Column("progress", postgresql.ARRAY(sa.Integer())),
        sa.Column("rewards", postgresql.JSONB()),
        sa.PrimaryKeyConstraint("id", "snapshot_ts", name="pk_orders"),
    )
    op.create_table(
        "dispatches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("published", sa.DateTime(timezone=True)),
        sa.Column("type", sa.Integer()),
        sa.Column("message", sa.Text()),
    )


def downgrade() -> None:
    op.drop_table("dispatches")
    op.drop_table("orders")
    op.execute("DROP INDEX IF EXISTS ix_planet_snapshots_planet_index_ts")
    op.drop_table("planet_snapshots")
    op.drop_table("planets_static")
