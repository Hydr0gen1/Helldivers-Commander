from __future__ import annotations

from app.clients.sources.community import CommunitySource
from app.config import settings


class DummyHTTP:
    pass


def source() -> CommunitySource:
    return CommunitySource(DummyHTTP(), settings)  # type: ignore[arg-type]


def test_normalize_planet_computes_liberation_and_camel_contract() -> None:
    planet = source().normalize_planet(
        {
            "index": 1,
            "name": "Klen Dahth II",
            "sector": "Barnard",
            "position": {"x": 0.25, "y": -0.5},
            "waypoints": [2, 3],
            "maxHealth": 1000,
            "health": 250,
            "owner": 2,
            "regenPerSecond": 1.5,
            "players": 42,
            "statistics": {"playerCount": 42, "missionsWon": 7},
        }
    )

    assert planet.liberation_pct == 75.0
    assert planet.current_owner == "TERMINIDS"
    assert planet.model_dump(by_alias=True)["liberationPct"] == 75.0
    assert planet.statistics.player_count == 42


def test_normalize_assignment_accepts_reward_object() -> None:
    orders = source().normalize_assignments(
        [
            {
                "id": 99,
                "title": "Defend Managed Democracy",
                "expiration": "2026-06-07T00:00:00Z",
                "tasks": [{"type": 1, "values": [1, 2, 3], "valueTypes": [4]}],
                "reward": {"type": 1, "amount": 45, "id32": 10},
            }
        ]
    )

    assert len(orders) == 1
    assert orders[0].tasks[0].value_types == [4]
    assert orders[0].rewards[0].amount == 45
