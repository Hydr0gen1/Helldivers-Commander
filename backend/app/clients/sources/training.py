from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from app.clients.base import UpstreamHTTPClient
from app.models.domain import Planet, War
from app.persistence import campaign_type_by_planet

logger = logging.getLogger(__name__)

TRAINING_BASE_URL = "https://helldiverstrainingmanual.com/api/v1"


def _as_list(raw: Any) -> list[Any]:
    return raw if isinstance(raw, list) else []


def _as_dict(raw: Any) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


def _parse_ts(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            return None
    if isinstance(value, int | float):
        return datetime.fromtimestamp(float(value), tz=timezone.utc)
    return None


class TrainingManualSource:
    name = "training_manual"

    def __init__(self, http: UpstreamHTTPClient, base_url: str = TRAINING_BASE_URL) -> None:
        self._http = http
        self._base = base_url.rstrip("/")

    async def fetch_history(self, planet_index: int, timeframe: str = "day") -> Any:
        return await self._http.get_json(f"{self._base}/war/history/{planet_index}", params={"timeframe": timeframe})

    def normalize_history_rows(
        self,
        raw: Any,
        *,
        planet: Planet,
        war: War,
        campaigns: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        data = _as_dict(raw)
        items = _as_list(raw) or _as_list(data.get("history")) or _as_list(data.get("data"))
        campaign_type = campaign_type_by_planet(campaigns).get(planet.index)
        rows: list[dict[str, Any]] = []
        for item in items:
            point = _as_dict(item)
            ts = _parse_ts(point.get("ts", point.get("time", point.get("timestamp", point.get("date")))))
            liberation = point.get("liberationPct", point.get("liberation", point.get("liberation_pct")))
            if ts is None or liberation is None:
                continue
            rows.append(
                {
                    "ts": ts,
                    "planet_index": planet.index,
                    "health": point.get("health", planet.health),
                    "max_health": point.get("maxHealth", point.get("max_health", planet.max_health)),
                    "owner": point.get("owner", planet.owner),
                    "players": point.get("players", 0),
                    "regen_per_second": point.get("regenPerSecond", point.get("regen_per_second", planet.regen_per_second)),
                    "liberation_pct": float(liberation),
                    "campaign_type": campaign_type,
                    "impact_multiplier": war.impact_multiplier,
                }
            )
        return rows
