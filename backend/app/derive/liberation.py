from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

import numpy as np
from scipy.stats import theilslopes

DEFAULT_DERIVATION_WINDOW_MINUTES = 30
Trend = Literal["accelerating", "steady", "stalling", "losing"]


@dataclass(frozen=True, slots=True)
class SnapshotPoint:
    ts: datetime
    liberation_pct: float
    players: int = 0


def liberation_pct(health: int, max_health: int) -> float:
    return max(0.0, min(100.0, (1.0 - health / max(max_health, 1)) * 100.0))


def decay_pct_per_hr(regen_per_second: float, max_health: int) -> float:
    return max(0.0, regen_per_second * 3600.0 / max(max_health, 1) * 100.0)


def trailing_window(
    points: list[SnapshotPoint],
    *,
    window_minutes: int = DEFAULT_DERIVATION_WINDOW_MINUTES,
    now: datetime | None = None,
) -> list[SnapshotPoint]:
    if not points:
        return []
    sorted_points = sorted(points, key=lambda point: point.ts)
    end = now or sorted_points[-1].ts
    if end.tzinfo is None:
        end = end.replace(tzinfo=timezone.utc)
    start = end - timedelta(minutes=window_minutes)
    window = [point for point in sorted_points if point.ts >= start]
    return window if len(window) >= 2 else sorted_points[-2:]


def _hours_from_start(points: list[SnapshotPoint]) -> np.ndarray:
    start = points[0].ts
    return np.array([(point.ts - start).total_seconds() / 3600.0 for point in points], dtype=float)


def lib_rate(
    points: list[SnapshotPoint],
    *,
    window_minutes: int = DEFAULT_DERIVATION_WINDOW_MINUTES,
) -> float | None:
    window = trailing_window(points, window_minutes=window_minutes)
    if len(window) < 2:
        return None
    x = _hours_from_start(window)
    y = np.array([point.liberation_pct for point in window], dtype=float)
    if float(np.ptp(x)) <= 0.0:
        return None
    slope, _intercept, _low, _high = theilslopes(y, x)
    return float(slope)


def slope_ci(points: list[SnapshotPoint], *, window_minutes: int = DEFAULT_DERIVATION_WINDOW_MINUTES) -> tuple[float, float] | None:
    window = trailing_window(points, window_minutes=window_minutes)
    if len(window) < 2:
        return None
    x = _hours_from_start(window)
    y = np.array([point.liberation_pct for point in window], dtype=float)
    if float(np.ptp(x)) <= 0.0:
        return None
    _slope, _intercept, low, high = theilslopes(y, x)
    return float(low), float(high)


def eta_hours(current_pct: float, rate_pct_per_hr: float | None) -> float | None:
    if rate_pct_per_hr is None or rate_pct_per_hr <= 0:
        return None
    return max(0.0, (100.0 - current_pct) / rate_pct_per_hr)


def confidence(points: list[SnapshotPoint], *, window_minutes: int = DEFAULT_DERIVATION_WINDOW_MINUTES) -> float:
    window = trailing_window(points, window_minutes=window_minutes)
    if len(window) < 2:
        return 0.0
    interval = slope_ci(window, window_minutes=window_minutes)
    rate = lib_rate(window, window_minutes=window_minutes)
    if interval is None or rate is None:
        return 0.0
    low, high = interval
    width = abs(high - low)
    rate_scale = max(abs(rate), 0.01)
    ci_factor = max(0.0, min(1.0, 1.0 - width / (rate_scale * 4.0)))
    sample_factor = max(0.0, min(1.0, len(window) / 6.0))
    return ci_factor * sample_factor


def trend(points: list[SnapshotPoint], rate_pct_per_hr: float | None = None) -> Trend:
    rate = lib_rate(points) if rate_pct_per_hr is None else rate_pct_per_hr
    if rate is None or abs(rate) < 0.05:
        return "stalling"
    if rate < 0:
        return "losing"
    window = trailing_window(points)
    if len(window) >= 4:
        midpoint = len(window) // 2
        early = lib_rate(window[: midpoint + 1])
        late = lib_rate(window[midpoint:])
        if early is not None and late is not None and late > early + 0.5:
            return "accelerating"
    return "steady"
