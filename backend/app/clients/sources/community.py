from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import httpx
from pydantic import ValidationError

from app.clients.base import UpstreamHTTPClient
from app.config import Settings
from app.constants import BASE_PLANET_HEALTH, faction_name, utc_from_unix
from app.models.domain import Dispatch, Order, Planet, Position, Reward, Statistics, Task, War

logger = logging.getLogger(__name__)


def _as_dict(raw: Any) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


def _as_list(raw: Any) -> list[Any]:
    return raw if isinstance(raw, list) else []


def _pick(data: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in data and data[name] is not None:
            return data[name]
    return default


def _normalize_faction(value: Any) -> tuple[int, str]:
    if isinstance(value, int):
        return value, faction_name(value)
    if isinstance(value, str):
        cleaned = value.strip().upper().replace("-", "_").replace(" ", "_")
        aliases = {
            "HUMAN": 1,
            "HUMANS": 1,
            "SUPER_EARTH": 1,
            "TERMINID": 2,
            "TERMINIDS": 2,
            "AUTOMATON": 3,
            "AUTOMATONS": 3,
            "ILLUMINATE": 4,
        }
        if cleaned.isdigit():
            faction_id = int(cleaned)
            return faction_id, faction_name(faction_id)
        faction_id = aliases.get(cleaned, 1)
        return faction_id, faction_name(faction_id)
    return 1, faction_name(1)


class CommunitySource:
    name = "community"

    def __init__(self, http: UpstreamHTTPClient, settings: Settings) -> None:
        self._http = http
        self._base = str(settings.community_base_url).rstrip("/")
        self._war_start_unix: int | None = None

    async def resolve_war_id(self) -> int:
        raw = await self._http.get_json(f"{self._base}/raw/api/WarSeason/current/WarID")
        return int(_as_dict(raw).get("id", 0))

    async def fetch_war(self) -> Any:
        return await self._http.get_json(f"{self._base}/api/v1/war")

    async def fetch_planets(self) -> Any:
        return await self._http.get_json(f"{self._base}/api/v1/planets")

    async def fetch_planet(self, index: int) -> Any:
        return await self._http.get_json(f"{self._base}/api/v1/planets/{index}")

    async def fetch_assignments(self) -> Any:
        return await self._http.get_json(f"{self._base}/api/v1/assignments")

    async def fetch_dispatches(self) -> Any:
        return await self._http.get_json(f"{self._base}/api/v1/dispatches")

    async def fetch_campaigns(self) -> Any:
        return await self._http.get_json(f"{self._base}/api/v1/campaigns")

    def normalize_war(self, raw: Any) -> War:
        data = _as_dict(raw)
        try:
            return War(
                war_id=int(_pick(data, "warId", "war_id", default=0)),
                time=self._normalize_time(_pick(data, "time", default=0), data),
                impact_multiplier=float(_pick(data, "impactMultiplier", "impact_multiplier", default=1.0)),
                statistics=self._normalize_statistics(_pick(data, "statistics", "stats", default={})),
            )
        except (TypeError, ValueError, ValidationError) as exc:
            logger.warning("normalize_war_failed error=%r", exc)
            raise

    def normalize_planets(self, raw: Any) -> list[Planet]:
        items = _as_list(raw) or _as_list(_as_dict(raw).get("planets"))
        planets: list[Planet] = []
        for item in items:
            try:
                planets.append(self.normalize_planet(item))
            except (TypeError, ValueError, ValidationError) as exc:
                logger.warning("normalize_planet_skipped error=%r raw_type=%s", exc, type(item).__name__)
        return planets

    def normalize_planet(self, raw: Any) -> Planet:
        data = _as_dict(raw)
        stats = self._normalize_statistics(_pick(data, "statistics", "stats", default={}))
        max_health = int(_pick(data, "maxHealth", "max_health", default=BASE_PLANET_HEALTH) or BASE_PLANET_HEALTH)
        health = int(_pick(data, "health", default=max_health) or max_health)
        liberation = _pick(data, "liberationPct", "liberation", "liberationPercentage", default=None)
        if liberation is None:
            liberation = max(0.0, min(100.0, (1.0 - health / max(max_health, 1)) * 100.0))
        owner_value = _pick(data, "owner", "currentOwner", "initialOwner", default=1)
        owner, current_owner = _normalize_faction(owner_value)
        position_data = _as_dict(_pick(data, "position", default={}))
        return Planet(
            index=int(_pick(data, "index", default=0)),
            name=str(_pick(data, "name", default=f"Planet {data.get('index', 0)}")),
            sector=str(_pick(data, "sector", default="UNKNOWN")),
            biome=_pick(data, "biome", default=None),
            position=Position(x=float(position_data.get("x", 0.0)), y=float(position_data.get("y", 0.0))),
            waypoints=[int(value) for value in _as_list(_pick(data, "waypoints", default=[]))],
            max_health=max_health,
            health=health,
            liberation_pct=float(liberation),
            disabled=bool(_pick(data, "disabled", default=False)),
            regen_per_second=float(_pick(data, "regenPerSecond", "regerPerSecond", "regen_per_second", default=0.0) or 0.0),
            owner=owner,
            current_owner=current_owner,
            players=int(_pick(data, "players", "playerCount", default=0) or 0),
            statistics=stats,
            attacking=[int(value) for value in _as_list(_pick(data, "attacking", default=[]))],
            event=_pick(data, "event", default=None),
        )

    def normalize_assignments(self, raw: Any) -> list[Order]:
        items = _as_list(raw) or _as_list(_as_dict(raw).get("assignments")) or _as_list(_as_dict(raw).get("orders"))
        orders: list[Order] = []
        for item in items:
            data = _as_dict(item)
            try:
                reward_items = _as_list(_pick(data, "rewards", default=[]))
                reward = _pick(data, "reward", default=None)
                if reward is not None and not reward_items:
                    reward_items = [reward]
                expiration = _pick(data, "expiration", default=None)
                if expiration is None and _pick(data, "expiresIn", default=None) is not None:
                    expiration = datetime.now(timezone.utc) + timedelta(seconds=int(data["expiresIn"]))
                orders.append(
                    Order(
                        id=int(_pick(data, "id", default=0)),
                        title=str(_pick(data, "title", default="")),
                        briefing=str(_pick(data, "briefing", default="")),
                        description=str(_pick(data, "description", default="")),
                        type=int(_pick(data, "type", default=0) or 0),
                        flags=int(_pick(data, "flags", default=0) or 0),
                        expiration=expiration or datetime.now(timezone.utc),
                        progress=[int(value) for value in _as_list(_pick(data, "progress", default=[]))],
                        tasks=[Task.model_validate(task) for task in _as_list(_pick(data, "tasks", default=[]))],
                        rewards=[Reward.model_validate(reward_data) for reward_data in reward_items],
                    )
                )
            except (TypeError, ValueError, ValidationError) as exc:
                logger.warning("normalize_assignment_skipped error=%r", exc)
        return orders

    def normalize_dispatches(self, raw: Any) -> list[Dispatch]:
        items = _as_list(raw) or _as_list(_as_dict(raw).get("dispatches")) or _as_list(_as_dict(raw).get("news"))
        dispatches: list[Dispatch] = []
        for item in items:
            data = _as_dict(item)
            try:
                dispatches.append(
                    Dispatch(
                        id=int(_pick(data, "id", default=0)),
                        published=self._normalize_time(_pick(data, "published", default=0), data),
                        type=int(_pick(data, "type", default=0) or 0),
                        message=_pick(data, "message", default=None),
                    )
                )
            except (TypeError, ValueError, ValidationError) as exc:
                logger.warning("normalize_dispatch_skipped error=%r", exc)
        return dispatches

    def normalize_campaigns(self, raw: Any) -> list[dict[str, Any]]:
        items = _as_list(raw) or _as_list(_as_dict(raw).get("campaigns"))
        return [dict(item) for item in items if isinstance(item, dict)]

    def _normalize_statistics(self, raw: Any) -> Statistics:
        data = _as_dict(raw)
        return Statistics(
            missions_won=int(_pick(data, "missionsWon", "missions_won", default=0) or 0),
            missions_lost=int(_pick(data, "missionsLost", "missions_lost", default=0) or 0),
            mission_time=int(_pick(data, "missionTime", "mission_time", default=0) or 0),
            terminid_kills=int(_pick(data, "terminidKills", "terminid_kills", default=0) or 0),
            automaton_kills=int(_pick(data, "automatonKills", "automaton_kills", default=0) or 0),
            illuminate_kills=int(_pick(data, "illuminateKills", "illuminate_kills", default=0) or 0),
            bullets_fired=int(_pick(data, "bulletsFired", "bullets_fired", default=0) or 0),
            bullets_hit=int(_pick(data, "bulletsHit", "bullets_hit", default=0) or 0),
            time_played=int(_pick(data, "timePlayed", "time_played", default=0) or 0),
            deaths=int(_pick(data, "deaths", default=0) or 0),
            revives=int(_pick(data, "revives", default=0) or 0),
            friendlies=int(_pick(data, "friendlies", default=0) or 0),
            mission_success_rate=int(_pick(data, "missionSuccessRate", "mission_success_rate", default=0) or 0),
            accuracy=int(_pick(data, "accuracy", default=0) or 0),
            player_count=int(_pick(data, "playerCount", "player_count", default=0) or 0),
        )

    def _normalize_time(self, value: Any, context: dict[str, Any]) -> datetime:
        if isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.astimezone(timezone.utc)
        numeric = int(value or 0)
        start = _pick(context, "startDate", default=None) or self._war_start_unix
        if start is not None and numeric < 100_000_000:
            return utc_from_unix(int(start) + numeric)
        if numeric > 0:
            return utc_from_unix(numeric)
        return datetime.now(timezone.utc)
