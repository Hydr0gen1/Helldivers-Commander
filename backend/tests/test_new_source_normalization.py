from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.clients.sources.diveharder import DiveHarderSource
from app.clients.sources.raw import RawCommunitySource
from app.config import settings


class DummyHTTP:
    async def get_json(self, url: str, **kwargs: Any) -> Any:
        raise AssertionError("network should not be used in normalization tests")


def diveharder() -> DiveHarderSource:
    return DiveHarderSource(DummyHTTP(), settings)  # type: ignore[arg-type]


def raw_source() -> RawCommunitySource:
    return RawCommunitySource(DummyHTTP(), settings)  # type: ignore[arg-type]


RAW_BUNDLE = {
    "war_info": {
        "warId": 801,
        "startDate": 1_700_000_000,
        "planetInfos": [
            {
                "index": 7,
                "name": {"en-US": "Mantes"},
                "sector": {"en-US": "Xzar"},
                "position": {"x": 0.2, "y": -0.3},
                "waypoints": [8],
                "maxHealth": 1000,
                "disabled": False,
                "initialOwner": 3,
            }
        ],
    },
    "status": {
        "warId": 801,
        "time": 3600,
        "impactMultiplier": 1.25,
        "planetStatus": [{"index": 7, "owner": 2, "health": 250, "regenPerSecond": 1.5, "players": 42}],
        "planetAttacks": [{"source": 7, "target": 8}],
        "campaigns": [{"id": 1, "planetIndex": 7, "type": 0, "count": 1}],
    },
    "planet_stats": {
        "galaxy_stats": {"missionsWon": 10, "bugKills": 22, "accurracy": 50, "playerCount": 42},
        "planets_stats": [{"planetIndex": 7, "missionsWon": 3, "bugKills": 4, "playerCount": 42}],
    },
}

ASSIGNMENT = {
    "id32": 99,
    "progress": [1],
    "expiresIn": 3600,
    "setting": {
        "type": 11,
        "overrideTitle": {"en-US": "Hold the Line"},
        "overrideBrief": {"en-US": "Brief"},
        "taskDescription": {"en-US": "Do the thing"},
        "tasks": [{"type": 1, "values": [7], "valueTypes": [3]}],
        "reward": {"type": 1, "id32": 123, "amount": 45},
        "flags": 0,
    },
}

NEWS = [{"id": 5, "published": 120, "type": 2, "message": {"en-US": "Dispatch text"}}]


def test_diveharder_normalizes_captured_raw_samples() -> None:
    source = diveharder()
    source._war_start_unix = 1_700_000_000

    war = source.normalize_war({**RAW_BUNDLE["war_info"], **RAW_BUNDLE["status"], "statistics": RAW_BUNDLE["planet_stats"]["galaxy_stats"]})
    planets = source.normalize_planets(RAW_BUNDLE)
    orders = source.normalize_assignments(ASSIGNMENT)
    dispatches = source.normalize_dispatches(NEWS)

    assert war.time == datetime.fromtimestamp(1_700_003_600, tz=timezone.utc)
    assert war.statistics.terminid_kills == 22
    assert planets[0].name == "Mantes"
    assert planets[0].sector == "Xzar"
    assert planets[0].liberation_pct == 75.0
    assert planets[0].attacking == [8]
    assert planets[0].statistics.terminid_kills == 4
    assert orders[0].title == "Hold the Line"
    assert orders[0].tasks[0].value_types == [3]
    assert dispatches[0].message == "Dispatch text"


def test_raw_adapter_normalizes_captured_raw_samples_with_war_clock() -> None:
    source = raw_source()
    source._war_id = 801

    war = source.normalize_war({**RAW_BUNDLE["war_info"], **RAW_BUNDLE["status"], "statistics": RAW_BUNDLE["planet_stats"]["galaxy_stats"]})
    planets = source.normalize_planets(RAW_BUNDLE)
    orders = source.normalize_assignments(ASSIGNMENT)
    dispatches = source.normalize_dispatches(NEWS)

    assert war.war_id == 801
    assert war.time == datetime.fromtimestamp(1_700_003_600, tz=timezone.utc)
    assert planets[0].current_owner == "TERMINIDS"
    assert orders[0].description == "Do the thing"
    assert dispatches[0].published == datetime.fromtimestamp(1_700_000_120, tz=timezone.utc)
