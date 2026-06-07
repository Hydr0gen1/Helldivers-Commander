from __future__ import annotations

from typing import Any

from app.clients.base import UpstreamHTTPClient
from app.clients.sources.community import _as_dict, _as_list, _pick
from app.clients.sources.diveharder import DiveHarderSource, _assignment_items
from app.config import Settings
from app.models.domain import Dispatch, Order, Planet, War


class RawCommunitySource(DiveHarderSource):
    """Last-resort adapter for the community API's raw game-server endpoints."""

    name = "raw"

    def __init__(self, http: UpstreamHTTPClient, settings: Settings) -> None:
        super().__init__(http, settings)
        self._base = str(settings.community_base_url).rstrip("/")
        self._war_id: int | None = None

    async def resolve_war_id(self) -> int:
        raw = await self._http.get_json(f"{self._base}/raw/api/WarSeason/current/WarID")
        self._war_id = int(_as_dict(raw).get("id", raw if isinstance(raw, int) else 0))
        return self._war_id

    async def _current_war_id(self) -> int:
        return self._war_id or await self.resolve_war_id()

    async def _war_info(self) -> dict[str, Any]:
        war_id = await self._current_war_id()
        info = _as_dict(await self._http.get_json(f"{self._base}/raw/api/WarSeason/{war_id}/WarInfo"))
        self._war_start_unix = int(_pick(info, "startDate", default=0) or 0) or self._war_start_unix
        return info

    async def fetch_war(self) -> Any:
        war_id = await self._current_war_id()
        war_info = await self._war_info()
        status = _as_dict(await self._http.get_json(f"{self._base}/raw/api/WarSeason/{war_id}/Status"))
        stats = await self._http.get_json(f"{self._base}/raw/api/Stats/war/{war_id}/summary")
        galaxy_stats = _pick(_as_dict(stats), "galaxy_stats", "galaxyStats", "statistics", default=stats)
        return {**war_info, **status, "statistics": galaxy_stats, "warId": war_id}

    async def fetch_planets(self) -> Any:
        war_id = await self._current_war_id()
        war_info = await self._war_info()
        status = _as_dict(await self._http.get_json(f"{self._base}/raw/api/WarSeason/{war_id}/Status"))
        stats = await self._http.get_json(f"{self._base}/raw/api/Stats/war/{war_id}/summary")
        return {"status": status, "war_info": war_info, "planet_stats": stats}

    async def fetch_assignments(self) -> Any:
        war_id = await self._current_war_id()
        return await self._http.get_json(f"{self._base}/raw/api/v2/Assignment/War/{war_id}")

    async def fetch_dispatches(self) -> Any:
        war_id = await self._current_war_id()
        war_info = await self._war_info()
        news = await self._http.get_json(f"{self._base}/raw/api/NewsFeed/{war_id}")
        return {"war_info": war_info, "news": news}

    async def fetch_campaigns(self) -> Any:
        war_id = await self._current_war_id()
        status = await self._http.get_json(f"{self._base}/raw/api/WarSeason/{war_id}/Status")
        return _as_list(_as_dict(status).get("campaigns"))

    def normalize_war(self, raw: Any, *, resolved_war_id: int | None = None) -> War:
        data = _as_dict(raw)
        if _pick(data, "startDate", default=None) is not None:
            self._war_start_unix = int(_pick(data, "startDate", default=0) or 0) or self._war_start_unix
        return super().normalize_war(data, resolved_war_id=resolved_war_id or self._war_id)

    def normalize_planets(self, raw: Any) -> list[Planet]:
        data = _as_dict(raw)
        war_info = _as_dict(_pick(data, "war_info", "warInfo", default={}))
        if _pick(war_info, "startDate", default=None) is not None:
            self._war_start_unix = int(_pick(war_info, "startDate", default=0) or 0) or self._war_start_unix
        return super().normalize_planets(raw)

    def normalize_assignments(self, raw: Any) -> list[Order]:
        return super().normalize_assignments(_assignment_items(raw))

    def normalize_dispatches(self, raw: Any) -> list[Dispatch]:
        data = _as_dict(raw)
        war_info = _as_dict(_pick(data, "war_info", "warInfo", default={}))
        if _pick(war_info, "startDate", default=None) is not None:
            self._war_start_unix = int(_pick(war_info, "startDate", default=0) or 0) or self._war_start_unix
        return super().normalize_dispatches(_pick(data, "news", "dispatches", default=raw))
