from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.derive.orders import estimate_order_probability, referenced_planet_indices
from app.models.domain import Order, Task

NOW = datetime(2026, 6, 8, 12, tzinfo=timezone.utc)


def order_with(tasks: list[Task], *, hours_remaining: float = 48.0) -> Order:
    return Order(id=7, title="MAJOR ORDER", expiration=NOW + timedelta(hours=hours_remaining), tasks=tasks)


def liberation_task(planet_index: int) -> Task:
    return Task(type=11, values=[1, 1, planet_index], valueTypes=[3, 11, 12])


def defense_task(planet_index: int) -> Task:
    return Task(type=12, values=[1, 1, planet_index], valueTypes=[3, 11, 12])


def eradication_task(goal: int) -> Task:
    return Task(type=3, values=[goal], valueTypes=[3])


def test_comfortable_liberation_eta_margin_is_more_likely_than_not() -> None:
    order = order_with([liberation_task(194)], hours_remaining=48.0)

    probability = estimate_order_probability(order, planet_eta_hours={194: 18.0}, now=NOW)

    assert probability is not None
    assert probability > 0.5


def test_impossible_liberation_eta_margin_is_near_zero() -> None:
    order = order_with([liberation_task(194)], hours_remaining=12.0)

    probability = estimate_order_probability(order, planet_eta_hours={194: 96.0}, now=NOW)

    assert probability is not None
    assert probability < 0.01


def test_relevant_planet_task_without_eta_data_returns_none() -> None:
    order = order_with([liberation_task(194)], hours_remaining=48.0)

    assert estimate_order_probability(order, planet_eta_hours={}, now=NOW) is None


def test_multi_task_order_with_one_failing_task_has_low_and_semantics_probability() -> None:
    order = order_with([liberation_task(194), liberation_task(195), eradication_task(1_000_000)], hours_remaining=24.0)

    probability = estimate_order_probability(order, planet_eta_hours={194: 6.0, 195: 72.0}, now=NOW)

    assert probability is not None
    assert probability < 0.05


def test_referenced_planet_indices_uses_value_types_not_fixed_positions() -> None:
    order = order_with([Task(type=11, values=[1, 321, 1], valueTypes=[3, 12, 11]), defense_task(0)])

    assert referenced_planet_indices(order) == {321}
