from __future__ import annotations

from typing import Any

from app.clients.base import UpstreamHTTPClient
from app.clients.sources.community import CommunitySource, _as_dict, _as_list, _pick
from app.config import Settings
from app.models.domain import Dispatch, Order, Planet, War


class DiveHarderSource(CommunitySource):
    """DiveHarder raw-source adapter normalized into WarDesk domain models."""

    name = "diveharder"

    def __init__(self, http: UpstreamHTTPClient, settings: Settings) -> None:
        super().__init__(http, settings)
        self._base = str(settings.diveharder_base_url).rstrip("/")

    async def resolve_war_id(self) -> int:
        raw = await self._http.get_json(f"{self._base}/raw/war_id")
        return int(_as_dict(raw).get("id", raw if isinstance(raw, int) else 0))

    async def fetch_war(self) -> Any:
        status = _as_dict(await self._http.get_json(f"{self._base}/raw/status"))
        war_info = _as_dict(await self._http.get_json(f"{self._base}/raw/war_info"))
        stats = await self._http.get_json(f"{self._base}/raw/planet_stats")
        galaxy_stats = _pick(_as_dict(stats), "galaxy_stats", "galaxyStats", "statistics", default={})
        return {**war_info, **status, "statistics": galaxy_stats}

    async def fetch_planets(self) -> Any:
        status = _as_dict(await self._http.get_json(f"{self._base}/raw/status"))
        war_info = _as_dict(await self._http.get_json(f"{self._base}/raw/war_info"))
        stats = await self._http.get_json(f"{self._base}/raw/planet_stats")
        return {"status": status, "war_info": war_info, "planet_stats": stats}

    async def fetch_planet(self, index: int) -> Any:
        raw = await self.fetch_planets()
        return {**_as_dict(raw), "planet_index": index}

    async def fetch_assignments(self) -> Any:
        return await self._http.get_json(f"{self._base}/raw/major_order")

    async def fetch_dispatches(self) -> Any:
        war_info = _as_dict(await self._http.get_json(f"{self._base}/raw/war_info"))
        news = await self._http.get_json(f"{self._base}/raw/news_feed")
        return {"war_info": war_info, "news": news}

    async def fetch_campaigns(self) -> Any:
        status = await self._http.get_json(f"{self._base}/raw/status")
        return _as_list(_as_dict(status).get("campaigns"))

    def normalize_war(self, raw: Any, *, resolved_war_id: int | None = None) -> War:
        self._remember_start_date(self._extract_start_date(_as_dict(raw)))
        return super().normalize_war(raw, resolved_war_id=resolved_war_id)

    def normalize_planets(self, raw: Any) -> list[Planet]:
        data = _as_dict(raw)
        if "status" in data or "war_info" in data:
            return self._normalize_raw_planet_bundle(data)
        return super().normalize_planets(raw)

    def normalize_planet(self, raw: Any) -> Planet:
        data = _as_dict(raw)
        if "status" in data or "war_info" in data:
            index = int(_pick(data, "planet_index", default=0) or 0)
            planets = self._normalize_raw_planet_bundle(data)
            for planet in planets:
                if planet.index == index:
                    return planet
            raise ValueError(f"planet {index} not found")
        return super().normalize_planet(raw)

    def normalize_assignments(self, raw: Any) -> list[Order]:
        return super().normalize_assignments(_assignment_items(raw))

    def normalize_dispatches(self, raw: Any) -> list[Dispatch]:
        self._remember_start_date(self._extract_start_date(_as_dict(raw)))
        return super().normalize_dispatches(raw)

    def _normalize_raw_planet_bundle(self, raw: dict[str, Any]) -> list[Planet]:
        status = _as_dict(_pick(raw, "status", default=raw))
        war_info = _as_dict(_pick(raw, "war_info", "warInfo", default=raw))
        planet_stats = _as_dict(_pick(raw, "planet_stats", "planetStats", default={}))
        info_by_index = {int(item.get("index", 0)): item for item in _as_list(_pick(war_info, "planetInfos", "planet_infos", default=[])) if isinstance(item, dict)}
        stats_by_index = {
            int(item.get("planetIndex", item.get("planet_index", 0))): item
            for item in _as_list(_pick(planet_stats, "planets_stats", "planetStats", "planetsStats", default=[]))
            if isinstance(item, dict)
        }
        attacking: dict[int, list[int]] = {}
        for attack in _as_list(_pick(status, "planetAttacks", "planet_attacks", default=[])):
            attack_data = _as_dict(attack)
            attacking.setdefault(int(_pick(attack_data, "source", default=0) or 0), []).append(int(_pick(attack_data, "target", default=0) or 0))
        event_by_index = {
            int(item.get("planetIndex", item.get("planet_index", 0))): item
            for item in _as_list(_pick(status, "planetEvents", "planet_events", default=[]))
            if isinstance(item, dict)
        }
        planets: list[Planet] = []
        for item in _as_list(_pick(status, "planetStatus", "planet_status", default=[])):
            planet_status = _as_dict(item)
            index = int(_pick(planet_status, "index", default=0) or 0)
            info = _as_dict(info_by_index.get(index))
            stats = _as_dict(stats_by_index.get(index))
            planets.append(
                self.normalize_planet(
                    {
                        **info,
                        **planet_status,
                        "name": _pick(info, "name", default=f"Planet {index}"),
                        "sector": _pick(info, "sector", default="UNKNOWN"),
                        "statistics": stats,
                        "attacking": attacking.get(index, []),
                        "event": event_by_index.get(index),
                    }
                )
            )
        return planets


def _assignment_items(raw: Any) -> list[Any]:
    data = _as_dict(raw)
    items = _as_list(raw) or _as_list(data.get("assignments")) or _as_list(data.get("orders"))
    if items:
        return items
    if "setting" in data:
        setting = _as_dict(data.get("setting"))
        return [
            {
                "id": _pick(data, "id32", "id", default=0),
                "title": _pick(setting, "overrideTitle", "title", default=""),
                "briefing": _pick(setting, "overrideBrief", "briefing", default=""),
                "description": _pick(setting, "taskDescription", "description", default=""),
                "type": _pick(setting, "type", default=0),
                "flags": _pick(setting, "flags", default=0),
                "expiresIn": _pick(data, "expiresIn", default=0),
                "progress": _pick(data, "progress", default=[]),
                "tasks": _pick(setting, "tasks", default=[]),
                "reward": _pick(setting, "reward", default=None),
                "rewards": _pick(setting, "rewards", default=[]),
            }
        ]
    return []
