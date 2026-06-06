from __future__ import annotations

import asyncio
import logging
from collections.abc import Mapping
from typing import Any

import httpx

from app.config import Settings

logger = logging.getLogger(__name__)


class UpstreamHTTPClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        contact = settings.wardesk_contact
        self._client = httpx.AsyncClient(
            timeout=httpx.Timeout(20.0, connect=10.0),
            headers={
                "X-Super-Client": "wardesk",
                "X-Super-Contact": contact,
                "User-Agent": f"WarDesk/0.1 (+{contact})",
                "Accept": "application/json",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def get_json(self, url: str, *, params: Mapping[str, Any] | None = None) -> Any:
        return await self._request_json("GET", url, params=params)

    async def _request_json(self, method: str, url: str, *, params: Mapping[str, Any] | None = None) -> Any:
        attempts = 4
        delay = 0.8
        for attempt in range(1, attempts + 1):
            try:
                response = await self._client.request(method, url, params=params)
                if response.status_code == 429:
                    retry_after = response.headers.get("Retry-After")
                    sleep_for = float(retry_after) if retry_after and retry_after.isdigit() else delay
                    logger.warning("upstream_rate_limited url=%s attempt=%s sleep=%.2f", url, attempt, sleep_for)
                    await asyncio.sleep(sleep_for)
                    delay *= 2
                    continue
                remaining = response.headers.get("X-RateLimit-Remaining")
                if remaining == "0" and self._settings.rate_limit_guard:
                    logger.info("upstream_rate_limit_guard url=%s sleep=1.00", url)
                    await asyncio.sleep(1.0)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as exc:
                if attempt >= attempts:
                    logger.warning("upstream_request_failed url=%s attempt=%s error=%r", url, attempt, exc)
                    raise
                logger.info("upstream_request_retry url=%s attempt=%s error=%r", url, attempt, exc)
                await asyncio.sleep(delay)
                delay *= 2
        raise RuntimeError("unreachable retry loop")
