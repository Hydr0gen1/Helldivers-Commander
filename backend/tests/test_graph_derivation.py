from __future__ import annotations

from app.derive.graph import find_gambits
from app.models.domain import Planet, Position


def planet(index: int, owner: int = 1, waypoints: list[int] | None = None, **kwargs: object) -> Planet:
    names = {1: "SUPER_EARTH", 2: "TERMINIDS", 3: "AUTOMATONS", 4: "ILLUMINATE"}
    return Planet(
        index=index,
        name=f"P{index}",
        owner=owner,
        current_owner=names.get(owner, "UNKNOWN"),
        position=Position(x=float(index), y=0.0),
        waypoints=waypoints or [],
        **kwargs,
    )


def test_fully_surrounded_enemy_planet_yields_siege() -> None:
    planets = [
        planet(1, 1, [2]),
        planet(2, 2, [1, 3, 4]),
        planet(3, 1, [2]),
        planet(4, 1, [2]),
    ]

    gambits = find_gambits(planets)

    assert [(gambit.kind, gambit.target_index) for gambit in gambits] == [("SIEGE", 2)]


def test_defense_with_fragile_attack_source_yields_gambit() -> None:
    planets = [
        planet(10, 3, [20], health=100, max_health=1_000, attacking=[20]),
        planet(20, 1, [10], event={"health": 500, "maxHealth": 500}),
    ]

    gambits = find_gambits(planets, campaigns=[{"planetIndex": 20, "type": 1, "health": 500}])

    assert [(gambit.kind, gambit.source_index, gambit.target_index) for gambit in gambits] == [("GAMBIT", 10, 20)]
    assert "cut the defense" in gambits[0].note


def test_articulation_planet_on_active_front_yields_chokepoint() -> None:
    planets = [
        planet(1, 1, [2]),
        planet(2, 1, [1, 3, 4]),
        planet(3, 1, [2]),
        planet(4, 2, [2], event={"health": 900}),
    ]

    gambits = find_gambits(planets, campaigns=[{"planetIndex": 4, "type": 1}])

    assert any(gambit.kind == "CHOKEPOINT" and gambit.target_index == 2 for gambit in gambits)


def test_normal_connected_front_has_no_spurious_graph_intel() -> None:
    planets = [
        planet(1, 1, [2]),
        planet(2, 1, [1, 3]),
        planet(3, 2, [2, 4]),
        planet(4, 2, [3]),
    ]

    gambits = find_gambits(planets)

    assert gambits == []
