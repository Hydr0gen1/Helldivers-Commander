from __future__ import annotations

from datetime import datetime, timezone

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


def test_normalize_planets_keeps_real_v1_sample_with_string_owner() -> None:
    # Captured from GET https://api.helldivers2.dev/api/v1/planets with the required WarDesk headers.
    raw_planets = [
        {
            "index": 0,
            "name": "SUPER EARTH",
            "sector": "Sol",
            "biome": {
                "name": "Super Earth",
                "description": "Super Earth is the blinding beacon that shines the light of democracy through the stars.",
            },
            "hazards": [{"name": "None", "description": "This planet's environment is not yet known."}],
            "hash": 897386910,
            "position": {"x": 0, "y": 0},
            "waypoints": [],
            "maxHealth": 1000000,
            "health": 1000000,
            "disabled": False,
            "owner": "Humans",
            "initialOwner": "Humans",
            "currentOwner": "Humans",
            "regenPerSecond": 4.1666665,
            "event": None,
            "statistics": {
                "missionsWon": 16617128,
                "missionsLost": 2352672,
                "missionTime": 51859791134,
                "terminidKills": 12625,
                "automatonKills": 4527,
                "illuminateKills": 8000366239,
                "bulletsFired": 38835674135,
                "bulletsHit": 41179630762,
                "timePlayed": 51859791134,
                "deaths": 120601807,
                "revives": 0,
                "friendlies": 17284178,
                "missionSuccessRate": 87,
                "accuracy": 100,
                "playerCount": 204,
            },
            "attacking": [],
        }
    ]

    planets = source().normalize_planets(raw_planets)

    assert len(planets) == 1
    assert planets[0].index == 0
    assert planets[0].owner == 1
    assert planets[0].current_owner == "SUPER_EARTH"


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


def test_normalize_war_uses_start_date_plus_war_relative_time() -> None:
    war = source().normalize_war(
        {
            "warId": 801,
            "startDate": 1_700_000_000,
            "time": 3_600,
            "impactMultiplier": 1.0,
            "statistics": {},
        }
    )

    assert war.time == datetime.fromtimestamp(1_700_003_600, tz=timezone.utc)
