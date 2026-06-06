from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.derive.liberation import LiberationPoint, derive_liberation


def series(start_pct: float, pct_per_hr: float) -> list[LiberationPoint]:
    base = datetime(2026, 6, 6, tzinfo=timezone.utc)
    return [
        LiberationPoint(ts=base + timedelta(minutes=minute), liberation_pct=start_pct + pct_per_hr * minute / 60.0)
        for minute in range(0, 31, 5)
    ]


def test_positive_synthetic_series_eta_approximately_ten_hours() -> None:
    derived = derive_liberation(series(50.0, 5.0), current_liberation_pct=50.0)

    assert derived.lib_rate_pct_per_hr is not None
    assert derived.lib_rate_pct_per_hr == 5.0
    assert derived.eta_hours is not None
    assert derived.eta_hours == 10.0
    assert derived.trend == "accelerating"
    assert derived.confidence > 0.0


def test_negative_slope_has_no_eta_and_losing_trend() -> None:
    derived = derive_liberation(series(50.0, -2.0), current_liberation_pct=49.0)

    assert derived.lib_rate_pct_per_hr is not None
    assert derived.lib_rate_pct_per_hr < 0.0
    assert derived.eta_hours is None
    assert derived.trend == "losing"
