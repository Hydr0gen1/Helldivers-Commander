from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any

import networkx as nx

from app.models.domain import Gambit, Planet

SUPER_EARTH = 1
ENEMY_FACTIONS = {2, 3, 4}
ENEMY_NAMES = {"TERMINIDS", "AUTOMATONS", "ILLUMINATE"}


def build_supply_graph(planets: Sequence[Planet]) -> nx.Graph:
    """Build the undirected supply-line graph from cached canonical planets."""

    by_index = {planet.index: planet for planet in planets}
    graph = nx.Graph()
    for planet in planets:
        graph.add_node(planet.index, planet=planet)
    for planet in planets:
        for target_index in planet.waypoints:
            if target_index in by_index and target_index != planet.index:
                graph.add_edge(planet.index, target_index)
    return graph


def find_gambits(planets: Sequence[Planet], campaigns: Sequence[dict[str, Any]] | None = None) -> list[Gambit]:
    """Return actionable supply-line graph detections from cached planet/campaign state only."""

    graph = build_supply_graph(planets)
    campaign_items = list(campaigns or [])
    detections: list[Gambit] = []
    seen: set[tuple[str, int, int]] = set()
    for detector in (detect_gambits, detect_sieges, detect_chokepoints):
        for gambit in detector(planets, campaign_items, graph):
            key = (gambit.kind, gambit.source_index, gambit.target_index)
            if key not in seen:
                seen.add(key)
                detections.append(gambit)
    return detections


def detect_gambits(planets: Sequence[Planet], campaigns: Sequence[dict[str, Any]] | None = None, graph: nx.Graph | None = None) -> list[Gambit]:
    by_index = {planet.index: planet for planet in planets}
    defense_requirements = _defense_requirements(planets, campaigns or [])
    attacks = _attack_edges(planets, campaigns or [])
    results: list[Gambit] = []
    for source_index, target_index in sorted(attacks):
        source = by_index.get(source_index)
        target = by_index.get(target_index)
        required_health = defense_requirements.get(target_index)
        if source is None or target is None or required_health is None:
            continue
        if not _is_enemy(source) or _is_enemy(target):
            continue
        if source.health < required_health:
            results.append(
                Gambit(
                    kind="GAMBIT",
                    source_index=source.index,
                    target_index=target.index,
                    note=(
                        f"Capture {source.name} ({source.health:,} health) to cut the defense on "
                        f"{target.name} ({required_health:,} defense health)."
                    ),
                )
            )
    return results


def detect_sieges(planets: Sequence[Planet], campaigns: Sequence[dict[str, Any]] | None = None, graph: nx.Graph | None = None) -> list[Gambit]:
    supply_graph = graph or build_supply_graph(planets)
    by_index = {planet.index: planet for planet in planets}
    attack_sources = {source for source, _target in _attack_edges(planets, campaigns or [])}
    results: list[Gambit] = []
    for planet in sorted(planets, key=lambda item: item.index):
        if not _is_enemy(planet) or planet.index in attack_sources:
            continue
        neighbors = [by_index[index] for index in supply_graph.neighbors(planet.index) if index in by_index]
        if neighbors and all(_is_super_earth(neighbor) for neighbor in neighbors):
            representative = min(neighbors, key=lambda item: item.index)
            results.append(
                Gambit(
                    kind="SIEGE",
                    source_index=representative.index,
                    target_index=planet.index,
                    note=f"{planet.name} is surrounded by Super Earth supply lines and should decay toward liberation.",
                )
            )
    return results


def detect_chokepoints(planets: Sequence[Planet], campaigns: Sequence[dict[str, Any]] | None = None, graph: nx.Graph | None = None) -> list[Gambit]:
    supply_graph = graph or build_supply_graph(planets)
    if supply_graph.number_of_nodes() < 3:
        return []
    by_index = {planet.index: planet for planet in planets}
    active = _active_front_indices(planets, campaigns or [], supply_graph)
    if not active:
        return []
    articulation_points = set(nx.articulation_points(supply_graph))
    results: list[Gambit] = []
    for index in sorted(articulation_points & active):
        planet = by_index.get(index)
        if planet is None:
            continue
        components_after_removal = nx.number_connected_components(_without_node(supply_graph, index))
        if components_after_removal <= nx.number_connected_components(supply_graph):
            continue
        results.append(
            Gambit(
                kind="CHOKEPOINT",
                source_index=index,
                target_index=index,
                note=f"{planet.name} is an active-front chokepoint; losing it would split the local supply network.",
            )
        )
    return results


def _without_node(graph: nx.Graph, index: int) -> nx.Graph:
    copy = graph.copy()
    copy.remove_node(index)
    return copy


def _active_front_indices(planets: Sequence[Planet], campaigns: Sequence[dict[str, Any]], graph: nx.Graph) -> set[int]:
    explicit_conflict = _campaign_planets(campaigns) | _event_planets(planets) | {node for edge in _attack_edges(planets, campaigns) for node in edge}
    active = set(explicit_conflict)
    for index in explicit_conflict:
        if index in graph:
            active.update(graph.neighbors(index))
    return active


def _defense_requirements(planets: Sequence[Planet], campaigns: Sequence[dict[str, Any]]) -> dict[int, int]:
    requirements: dict[int, int] = {}
    for planet in planets:
        event = _as_dict(planet.event)
        if event:
            value = _pick(event, "health", "maxHealth", "max_health", default=None)
            if value is not None:
                requirements[planet.index] = max(1, int(value))
    for campaign in campaigns:
        target_index = _index_from(campaign, "planetIndex", "planet_index", "targetIndex", "target_index")
        if target_index is None:
            continue
        value = _pick(campaign, "health", "maxHealth", "max_health", "requiredHealth", "required_health", default=None)
        if value is not None:
            requirements[target_index] = max(requirements.get(target_index, 0), int(value))
    return requirements


def _attack_edges(planets: Sequence[Planet], campaigns: Sequence[dict[str, Any]]) -> set[tuple[int, int]]:
    edges: set[tuple[int, int]] = set()
    for planet in planets:
        for target_index in planet.attacking:
            edges.add((planet.index, int(target_index)))
        event = _as_dict(planet.event)
        source = _index_from(event, "source", "sourceIndex", "source_index", "attacker", "attackerIndex", "attacker_index")
        target = _index_from(event, "target", "targetIndex", "target_index", "planetIndex", "planet_index")
        if source is not None:
            edges.add((source, target if target is not None else planet.index))
    for campaign in campaigns:
        source = _index_from(campaign, "source", "sourceIndex", "source_index", "attacker", "attackerIndex", "attacker_index")
        target = _index_from(campaign, "target", "targetIndex", "target_index", "planetIndex", "planet_index")
        if source is not None and target is not None:
            edges.add((source, target))
    return edges


def _campaign_planets(campaigns: Iterable[dict[str, Any]]) -> set[int]:
    indices: set[int] = set()
    for campaign in campaigns:
        for name in ("planetIndex", "planet_index", "targetIndex", "target_index", "sourceIndex", "source_index"):
            value = campaign.get(name)
            if value is not None:
                indices.add(int(value))
    return indices


def _event_planets(planets: Sequence[Planet]) -> set[int]:
    return {planet.index for planet in planets if planet.event is not None}


def _index_from(data: dict[str, Any], *names: str) -> int | None:
    value = _pick(data, *names, default=None)
    return int(value) if value is not None else None


def _pick(data: dict[str, Any], *names: str, default: Any = None) -> Any:
    for name in names:
        if name in data and data[name] is not None:
            return data[name]
    return default


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _is_super_earth(planet: Planet) -> bool:
    return planet.owner == SUPER_EARTH or planet.current_owner == "SUPER_EARTH"


def _is_enemy(planet: Planet) -> bool:
    return planet.owner in ENEMY_FACTIONS or planet.current_owner in ENEMY_NAMES
