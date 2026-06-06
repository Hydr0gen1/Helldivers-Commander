from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.clients.base import UpstreamHTTPClient
from app.config import Settings
from app.derive.liberation import liberation_pct


def _as_dict(raw: Any) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


def _as_list(raw: Any) -> list[Any]:
    return raw if isinstance(raw, list) else []


def _pick(data: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in data and data[name] is not None:
            return data[name]
    return default


class TrainingManualSource:
    name = "training_manual"

    def __init__(self, http: UpstreamHTTPClient, settings: Settings) -> None:
        self._http = http
        self._base = str(settings.training_manual_base_url).rstrip("/")

    async def fetch_planet_history(self, index: int) -> Any:
        return await self._http.get_json(f"{self._base}/api/v1/war/history/{index}?timeframe=day")

    def normalize_history(self, raw: Any) -> list[dict[str, Any]]:
        data = _as_dict(raw)
        items = _as_list(raw) or _as_list(data.get("history")) or _as_list(data.get("data"))
        rows: list[dict[str, Any]] = []
        for item in items:
            record = _as_dict(item)
            ts = _normalize_time(_pick(record, "ts", "time", "date", "retrievedAt", "updatedAt", default=None))
            if ts is None:
                continue
            max_health = int(_pick(record, "maxHealth", "max_health", default=1_000_000) or 1_000_000)
            health = int(_pick(record, "health", default=max_health) or max_health)
            liberation = _pick(record, "liberationPct", "liberation_pct", "liberation", "percentage", default=None)
            if liberation is None:
                liberation = liberation_pct(health, max_health)
            rows.append(
                {
                    "ts": ts,
                    "health": health,
                    "max_health": max_health,
                    "owner": int(_pick(record, "owner", "currentOwner", default=1) or 1),
                    "players": int(_pick(record, "players", "playerCount", default=0) or 0),
                    "regen_per_second": float(_pick(record, "regenPerSecond", "regen_per_second", default=0.0) or 0.0),
                    "liberation_pct": float(liberation),
                    "campaign_type": _pick(record, "campaignType", "campaign_type", "type", default=None),
                    "impact_multiplier": float(_pick(record, "impactMultiplier", "impact_multiplier", default=1.0) or 1.0),
                }
            )
        return rows


async def fetch_normalized_history(source: TrainingManualSource, index: int) -> list[dict[str, Any]]:
    return source.normalize_history(await source.fetch_planet_history(index))


def _normalize_time(value: Any) -> datetime | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc) if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
        except ValueError:
            if value.isdigit():
                return datetime.fromtimestamp(int(value), tz=timezone.utc)
            return None
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        return None
    if numeric <= 0:
        return None
    if numeric > 10_000_000_000:
        numeric /= 1000.0
    return datetime.fromtimestamp(numeric, tz=timezone.utc)
