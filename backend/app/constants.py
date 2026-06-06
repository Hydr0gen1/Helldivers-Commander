from __future__ import annotations

from datetime import datetime, timezone

FACTIONS: dict[int, str] = {
    1: "SUPER_EARTH",
    2: "TERMINIDS",
    3: "AUTOMATONS",
    4: "ILLUMINATE",
}

# Community reverse-engineered defaults; Arrowhead may retune these after patches.
BASE_PLANET_HEALTH = 1_000_000
MAX_DECAY_PCT_PER_HR = 20.0
DEFAULT_CACHE_TTL_SECONDS = 60


def faction_name(faction_id: int | None) -> str:
    return FACTIONS.get(faction_id or 1, "UNKNOWN")


def utc_from_unix(seconds: int | float) -> datetime:
    return datetime.fromtimestamp(seconds, tz=timezone.utc)
