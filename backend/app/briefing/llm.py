from __future__ import annotations

from datetime import datetime, timezone

from app.models.domain import BriefingResponse, Dispatch


class BriefingGenerator:
    def __init__(self) -> None:
        self._last_dispatch_id: int | None = None
        self._cached = BriefingResponse(text="Awaiting fresh Super Earth intelligence.", generated_at=datetime.now(timezone.utc))

    async def generate(self, dispatches: list[Dispatch]) -> BriefingResponse:
        newest = max((dispatch.id for dispatch in dispatches), default=None)
        if newest == self._last_dispatch_id:
            return self._cached
        self._last_dispatch_id = newest
        latest = next((dispatch for dispatch in sorted(dispatches, key=lambda d: d.published, reverse=True) if dispatch.message), None)
        text = latest.message if latest and latest.message else "No current dispatches. Maintain readiness."
        self._cached = BriefingResponse(text=text, generated_at=datetime.now(timezone.utc))
        return self._cached
