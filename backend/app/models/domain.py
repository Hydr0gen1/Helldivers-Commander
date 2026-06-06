from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

FACTIONS: dict[int, str] = {
    1: "SUPER_EARTH",
    2: "TERMINIDS",
    3: "AUTOMATONS",
    4: "ILLUMINATE",
}


def to_camel(value: str) -> str:
    parts = value.split("_")
    return parts[0] + "".join(part.capitalize() for part in parts[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        extra="ignore",
    )


class Position(CamelModel):
    x: float = 0.0
    y: float = 0.0


class Statistics(CamelModel):
    missions_won: int = 0
    missions_lost: int = 0
    mission_time: int = 0
    terminid_kills: int = 0
    automaton_kills: int = 0
    illuminate_kills: int = 0
    bullets_fired: int = 0
    bullets_hit: int = 0
    time_played: int = 0
    deaths: int = 0
    revives: int = 0
    friendlies: int = 0
    mission_success_rate: int = 0
    accuracy: int = 0
    player_count: int = 0


class Derived(CamelModel):
    lib_rate_pct_per_hr: float | None = None
    decay_pct_per_hr: float = 0.0
    eta_hours: float | None = None
    confidence: float = 0.0
    trend: Literal["accelerating", "steady", "stalling", "losing"] = "steady"


class Planet(CamelModel):
    index: int
    name: str
    sector: str = "UNKNOWN"
    biome: dict[str, Any] | None = None
    position: Position = Field(default_factory=Position)
    waypoints: list[int] = Field(default_factory=list)
    max_health: int = 1_000_000
    health: int = 1_000_000
    liberation_pct: float = 0.0
    disabled: bool = False
    regen_per_second: float = 0.0
    owner: int = 1
    current_owner: str = "SUPER_EARTH"
    players: int = 0
    statistics: Statistics = Field(default_factory=Statistics)
    attacking: list[int] = Field(default_factory=list)
    event: dict[str, Any] | None = None
    derived: Derived | None = None


class Task(CamelModel):
    type: int = 0
    values: list[int] = Field(default_factory=list)
    value_types: list[int] = Field(default_factory=list)


class Reward(CamelModel):
    type: int = 0
    amount: int = 0
    id32: int = 0


class Order(CamelModel):
    id: int
    title: str = ""
    briefing: str = ""
    description: str = ""
    type: int = 0
    flags: int = 0
    expiration: datetime
    progress: list[int] = Field(default_factory=list)
    tasks: list[Task] = Field(default_factory=list)
    rewards: list[Reward] = Field(default_factory=list)
    win_probability: float | None = None


class Dispatch(CamelModel):
    id: int
    published: datetime
    type: int = 0
    message: str | None = None


class War(CamelModel):
    war_id: int
    time: datetime
    impact_multiplier: float = 1.0
    statistics: Statistics = Field(default_factory=Statistics)


class Gambit(CamelModel):
    kind: Literal["GAMBIT", "SIEGE", "CHOKEPOINT"]
    source_index: int
    target_index: int
    note: str


class PlanetsResponse(CamelModel):
    planets: list[Planet]


class OrdersResponse(CamelModel):
    orders: list[Order]


class DispatchesResponse(CamelModel):
    dispatches: list[Dispatch]


class CampaignsResponse(CamelModel):
    campaigns: list[dict[str, Any]]


class BriefingResponse(CamelModel):
    text: str
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class HealthResponse(CamelModel):
    sources: dict[str, str]
    last_ingest: datetime | None = None
