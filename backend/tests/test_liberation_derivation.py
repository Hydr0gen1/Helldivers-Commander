from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.derive.liberation import SnapshotPoint, eta_hours, lib_rate, trend


def series(start_pct: float, slope_pct_per_hr: float) -> list[SnapshotPoint]:
    start = datetime(2026, 6, 6, tzinfo=timezone.utc)
    return [
        SnapshotPoint(ts=start + timedelta(minutes=5 * index), liberation_pct=start_pct + slope_pct_per_hr * (5 * index / 60))
        for index in range(7)
    ]


def test_positive_synthetic_series_eta() -> None:
    points = series(50.0, 5.0)
    rate = lib_rate(points)

    assert rate is not None
    assert rate == pytest_approx(5.0, abs=0.01)
    assert eta_hours(50.0, rate) == pytest_approx(10.0, abs=0.05)


def test_negative_synthetic_series_losing() -> None:
    points = series(50.0, -3.0)
    rate = lib_rate(points)

    assert rate is not None
    assert eta_hours(points[-1].liberation_pct, rate) is None
    assert trend(points, rate) == "losing"


def pytest_approx(value: float, *, abs: float) -> object:
    import pytest

    return pytest.approx(value, abs=abs)
