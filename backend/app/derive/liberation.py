from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal

import numpy as np
from scipy.stats import theilslopes

DERIVATION_WINDOW_MINUTES = 30
Trend = Literal["accelerating", "steady", "stalling", "losing"]


@dataclass(frozen=True)
class LiberationPoint:
    ts: datetime
    liberation_pct: float
    players: int = 0


@dataclass(frozen=True)
class LiberationDerived:
    lib_rate_pct_per_hr: float | None
    decay_pct_per_hr: float
    eta_hours: float | None
    confidence: float
    trend: Trend


def liberation_pct(health: int, max_health: int) -> float:
    return max(0.0, min(100.0, (1.0 - health / max(max_health, 1)) * 100.0))


def decay_pct_per_hr(regen_per_second: float, max_health: int) -> float:
    if max_health <= 0:
        return 0.0
    return max(0.0, regen_per_second * 3600.0 / max_health * 100.0)


def derive_liberation(
    points: Sequence[LiberationPoint],
    *,
    current_liberation_pct: float | None = None,
    regen_per_second: float = 0.0,
    max_health: int = 1_000_000,
    window_minutes: int = DERIVATION_WINDOW_MINUTES,
) -> LiberationDerived:
    windowed = trailing_window(points, minutes=window_minutes)
    rate, low, high = lib_rate(windowed)
    current_pct = current_liberation_pct if current_liberation_pct is not None else (windowed[-1].liberation_pct if windowed else 0.0)
    decay = decay_pct_per_hr(regen_per_second, max_health)
    eta = eta_hours(current_pct, rate)
    confidence = slope_confidence(rate, low, high, len(windowed), window_minutes)
    return LiberationDerived(
        lib_rate_pct_per_hr=rate,
        decay_pct_per_hr=decay,
        eta_hours=eta,
        confidence=confidence,
        trend=trend_label(rate),
    )


def trailing_window(points: Sequence[LiberationPoint], *, minutes: int = DERIVATION_WINDOW_MINUTES) -> list[LiberationPoint]:
    ordered = sorted(points, key=lambda point: _utc(point.ts))
    if not ordered:
        return []
    cutoff = _utc(ordered[-1].ts) - timedelta(minutes=minutes)
    return [point for point in ordered if _utc(point.ts) >= cutoff]


def lib_rate(points: Sequence[LiberationPoint]) -> tuple[float | None, float | None, float | None]:
    if len(points) < 2:
        return None, None, None
    base = _utc(points[0].ts)
    hours = np.array([(_utc(point.ts) - base).total_seconds() / 3600.0 for point in points], dtype=float)
    values = np.array([point.liberation_pct for point in points], dtype=float)
    if float(hours[-1] - hours[0]) <= 0.0:
        return None, None, None
    slope, intercept, low, high = theilslopes(values, hours, alpha=0.90)
    return float(slope), float(low), float(high)


def eta_hours(current_liberation_pct: float, rate_pct_per_hr: float | None) -> float | None:
    if rate_pct_per_hr is None or rate_pct_per_hr <= 0:
        return None
    return max(0.0, (100.0 - current_liberation_pct) / rate_pct_per_hr)


def slope_confidence(
    rate_pct_per_hr: float | None,
    low_pct_per_hr: float | None,
    high_pct_per_hr: float | None,
    point_count: int,
    window_minutes: int = DERIVATION_WINDOW_MINUTES,
) -> float:
    if rate_pct_per_hr is None or low_pct_per_hr is None or high_pct_per_hr is None or point_count < 2:
        return 0.0
    span_score = min(1.0, max(0.0, point_count / max(2.0, window_minutes / 5.0)))
    ci_width = abs(high_pct_per_hr - low_pct_per_hr)
    magnitude = max(abs(rate_pct_per_hr), 0.1)
    ci_score = max(0.0, 1.0 - ci_width / (magnitude * 4.0))
    return round(min(1.0, span_score * ci_score), 3)


def trend_label(rate_pct_per_hr: float | None) -> Trend:
    if rate_pct_per_hr is None:
        return "stalling"
    if rate_pct_per_hr < 0:
        return "losing"
    if rate_pct_per_hr < 0.25:
        return "stalling"
    if rate_pct_per_hr > 3.0:
        return "accelerating"
    return "steady"


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
