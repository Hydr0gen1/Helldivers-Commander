from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timezone

from app.models.domain import Order, Planet, Task

TASK_TYPE_ERADICATION = 3
TASK_TYPE_LIBERATION = 11
TASK_TYPE_DEFENSE = 12
TASK_TYPE_CONTROL = 13

VALUE_TYPE_TARGET_PLANET = 12

LOGISTIC_SCALE_HOURS = 12.0


def estimate_order_probability(
    order: Order,
    *,
    planets: Mapping[int, Planet] | None = None,
    planet_eta_hours: Mapping[int, float | None] | None = None,
    now: datetime | None = None,
) -> float | None:
    """Estimate a Major Order win probability from task ETA margins.

    The function is intentionally pure: callers provide any current planet state and
    ETA values derived from snapshot history. Tasks with no useful liberation ETA
    signal are neutral; tasks that reference planets require ETA data.
    """
    del planets  # Reserved for task types that can use current planet state later.
    eta_by_planet = planet_eta_hours or {}
    current_time = _utc(now or datetime.now(timezone.utc))
    expiration = _utc(order.expiration)
    remaining_hours = (expiration - current_time).total_seconds() / 3600.0
    if remaining_hours <= 0.0:
        return 0.0

    margins: list[float] = []
    needs_eta = False
    missing_eta = False

    for task in order.tasks:
        contribution = _task_margin_hours(task, eta_by_planet=eta_by_planet, remaining_hours=remaining_hours)
        if contribution.needs_eta:
            needs_eta = True
        if contribution.missing_eta:
            missing_eta = True
        if contribution.margin_hours is not None:
            margins.append(contribution.margin_hours)

    if missing_eta or (needs_eta and not margins):
        return None
    if not margins:
        return None

    aggregate_margin = min(margins)
    return round(_logistic(aggregate_margin / LOGISTIC_SCALE_HOURS), 4)


def referenced_planet_indices(order: Order) -> set[int]:
    """Return concrete planet indices referenced by the order's tasks."""
    indices: set[int] = set()
    for task in order.tasks:
        indices.update(_task_planet_indices(task))
    return indices


@dataclass(frozen=True)
class _TaskContribution:
    margin_hours: float | None = None
    needs_eta: bool = False
    missing_eta: bool = False


def _task_margin_hours(
    task: Task,
    *,
    eta_by_planet: Mapping[int, float | None],
    remaining_hours: float,
) -> _TaskContribution:
    planet_indices = _task_planet_indices(task)

    if task.type == TASK_TYPE_ERADICATION:
        return _TaskContribution()

    if task.type in {TASK_TYPE_LIBERATION, TASK_TYPE_CONTROL}:
        if not planet_indices:
            return _TaskContribution()
        etas = _eta_values(planet_indices, eta_by_planet)
        if etas is None:
            return _TaskContribution(needs_eta=True, missing_eta=True)
        return _TaskContribution(margin_hours=remaining_hours - max(etas), needs_eta=True)

    if task.type == TASK_TYPE_DEFENSE:
        if not planet_indices:
            return _TaskContribution()
        etas = _eta_values(planet_indices, eta_by_planet)
        if etas is None:
            return _TaskContribution(needs_eta=True, missing_eta=True)
        # Defense/hold tasks succeed when the opposing ETA does not complete before expiry.
        return _TaskContribution(margin_hours=min(etas) - remaining_hours, needs_eta=True)

    return _TaskContribution()


def _eta_values(planet_indices: set[int], eta_by_planet: Mapping[int, float | None]) -> list[float] | None:
    etas: list[float] = []
    for index in planet_indices:
        eta = eta_by_planet.get(index)
        if eta is None or not math.isfinite(eta):
            return None
        etas.append(float(eta))
    return etas


def _task_planet_indices(task: Task) -> set[int]:
    indices: set[int] = set()
    for value, value_type in zip(task.values, task.value_types, strict=False):
        if value_type != VALUE_TYPE_TARGET_PLANET:
            continue
        # HellHub documents planet value 0 as "multiple planets". Treat it as
        # non-concrete rather than guessing at planet index 0.
        if value > 0:
            indices.add(value)
    return indices


def _logistic(value: float) -> float:
    if value >= 0:
        factor = math.exp(-value)
        return 1.0 / (1.0 + factor)
    factor = math.exp(value)
    return factor / (1.0 + factor)


def _utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)
