from __future__ import annotations

from typing import Any

import networkx as nx

from app.models.domain import Gambit, Planet

SUPER_EARTH_FACTION_ID = 1
SUPER_EARTH_FACTION_NAME = "SUPER_EARTH"


def build_supply_graph(planets: list[Planet]) -> nx.Graph:
    """Build an undirected supply-line graph from canonical planets."""
    by_index = {planet.index: planet for planet in planets}
    graph = nx.Graph()
    for planet in planets:
        graph.add_node(planet.index, planet=planet)
    for planet in planets:
        for target_index in planet.waypoints:
            if target_index in by_index and target_index != planet.index:
                graph.add_edge(planet.index, target_index)
    return graph


def find_gambits(planets: list[Planet], campaigns: list[dict[str, Any]] | None = None) -> list[Gambit]:
    """Return supply-line graph intelligence derived only from cached state."""
    campaign_items = campaigns or []
    results = [
        *_find_gambit_defenses(planets, campaign_items),
        *_find_sieges(planets, campaign_items),
        *_find_chokepoints(planets, campaign_items),
    ]
    return _dedupe(results)


def _find_gambit_defenses(planets: list[Planet], campaigns: list[dict[str, Any]]) -> list[Gambit]:
    by_index = {planet.index: planet for planet in planets}
    defenses = _defense_requirements(planets, campaigns)
    gambits: list[Gambit] = []
    for source in planets:
        if _is_super_earth(source):
            continue
        for target_index in source.attacking:
            target = by_index.get(target_index)
            required_health = defenses.get(target_index)
            if target is None or required_health is None:
                continue
            if _effective_health(source) < required_health:
                gambits.append(
                    Gambit(
                        kind="GAMBIT",
                        source_index=source.index,
                        target_index=target.index,
                        note=(
                            f"Capture {source.name} ({_effective_health(source):,} HP remaining) to sever the "
                            f"defense of {target.name} ({required_health:,} HP required)."
                        ),
                    )
                )
    return gambits


def _find_sieges(planets: list[Planet], campaigns: list[dict[str, Any]]) -> list[Gambit]:
    by_index = {planet.index: planet for planet in planets}
    active_campaign_planets = _campaign_planet_indices(campaigns)
    graph = build_supply_graph(planets)
    sieges: list[Gambit] = []
    for planet in planets:
        if _is_super_earth(planet) or planet.attacking or planet.event or planet.index in active_campaign_planets:
            continue
        neighbors = [by_index[index] for index in graph.neighbors(planet.index) if index in by_index]
        if not neighbors:
            continue
        if all(_is_super_earth(neighbor) for neighbor in neighbors):
            representative = min(neighbors, key=lambda neighbor: neighbor.index)
            sieges.append(
                Gambit(
                    kind="SIEGE",
                    source_index=representative.index,
                    target_index=planet.index,
                    note=f"{planet.name} is surrounded by Super Earth supply lines and should decay toward liberation.",
                )
            )
    return sieges


def _find_chokepoints(planets: list[Planet], campaigns: list[dict[str, Any]]) -> list[Gambit]:
    by_index = {planet.index: planet for planet in planets}
    graph = build_supply_graph(planets)
    if graph.number_of_nodes() < 3:
        return []

    active_front = _active_front_indices(planets, campaigns, graph)
    articulation_points = set(nx.articulation_points(graph))
    betweenness_points = _high_betweenness_points(graph, active_front)
    candidates = sorted((articulation_points | betweenness_points) & active_front)

    chokepoints: list[Gambit] = []
    for index in candidates:
        planet = by_index.get(index)
        if planet is None:
            continue
        if not _touches_contested_edge(planet, by_index, graph) and not _has_active_conflict(planet, campaigns):
            continue
        disconnected_parts = nx.number_connected_components(_graph_without_node(graph, index))
        note = f"{planet.name} is a front-line chokepoint; losing it would split nearby supply access."
        if disconnected_parts > 1:
            note = f"{planet.name} is a front-line chokepoint; removing it splits the network into {disconnected_parts} components."
        chokepoints.append(Gambit(kind="CHOKEPOINT", source_index=index, target_index=index, note=note))
    return chokepoints


def _campaign_planet_index(campaign: dict[str, Any]) -> int | None:
    planet = campaign.get("planet")
    if isinstance(planet, dict):
        planet_index = _int_field(planet, "index")
        if planet_index is not None:
            return planet_index
    return _int_field(campaign, "planetIndex", "planet_index", "planet")


def _campaign_planet_indices(campaigns: list[dict[str, Any]]) -> set[int]:
    return {planet_index for campaign in campaigns if (planet_index := _campaign_planet_index(campaign)) is not None}


def _defense_requirements(planets: list[Planet], campaigns: list[dict[str, Any]]) -> dict[int, int]:
    requirements: dict[int, int] = {}
    for campaign in campaigns:
        planet_index = _campaign_planet_index(campaign)
        if planet_index is None:
            continue
        required_health = _health_requirement(campaign)
        if required_health is not None:
            requirements[planet_index] = required_health
    for planet in planets:
        if not planet.event:
            continue
        required_health = _health_requirement(planet.event)
        if required_health is not None:
            requirements[planet.index] = max(requirements.get(planet.index, 0), required_health)
    return requirements


def _health_requirement(data: dict[str, Any]) -> int | None:
    for key in ("health", "maxHealth", "max_health", "requiredHealth", "required_health", "eventHealth", "event_health"):
        value = data.get(key)
        if value is None:
            continue
        try:
            amount = int(float(value))
        except (TypeError, ValueError):
            continue
        if amount > 0:
            return amount
    return None


def _active_front_indices(planets: list[Planet], campaigns: list[dict[str, Any]], graph: nx.Graph) -> set[int]:
    active: set[int] = set()
    for planet in planets:
        if planet.event or planet.attacking:
            active.add(planet.index)
            active.update(planet.attacking)
    for campaign in campaigns:
        planet_index = _campaign_planet_index(campaign)
        if planet_index is not None:
            active.add(planet_index)
    expanded = set(active)
    for index in active:
        if index in graph:
            expanded.update(graph.neighbors(index))
    return expanded


def _has_active_conflict(planet: Planet, campaigns: list[dict[str, Any]]) -> bool:
    if planet.event or planet.attacking:
        return True
    return any(_campaign_planet_index(campaign) == planet.index for campaign in campaigns)


def _touches_contested_edge(planet: Planet, by_index: dict[int, Planet], graph: nx.Graph) -> bool:
    return any(
        (neighbor := by_index.get(neighbor_index)) is not None and _is_super_earth(planet) != _is_super_earth(neighbor)
        for neighbor_index in graph.neighbors(planet.index)
    )


def _high_betweenness_points(graph: nx.Graph, active_front: set[int]) -> set[int]:
    if graph.number_of_nodes() < 4 or not active_front:
        return set()
    centrality = nx.betweenness_centrality(graph, normalized=True)
    front_scores = {index: score for index, score in centrality.items() if index in active_front and score >= 0.35}
    if not front_scores:
        return set()
    max_score = max(front_scores.values())
    return {index for index, score in front_scores.items() if score == max_score or score >= 0.5}


def _graph_without_node(graph: nx.Graph, index: int) -> nx.Graph:
    trimmed = graph.copy()
    trimmed.remove_node(index)
    return trimmed


def _is_super_earth(planet: Planet) -> bool:
    return planet.owner == SUPER_EARTH_FACTION_ID or planet.current_owner == SUPER_EARTH_FACTION_NAME


def _effective_health(planet: Planet) -> int:
    return max(0, int(planet.health))


def _int_field(data: dict[str, Any], *keys: str) -> int | None:
    for key in keys:
        value = data.get(key)
        if value is None:
            continue
        try:
            return int(value)
        except (TypeError, ValueError):
            continue
    return None


def _dedupe(gambits: list[Gambit]) -> list[Gambit]:
    seen: set[tuple[str, int, int]] = set()
    unique: list[Gambit] = []
    for gambit in gambits:
        key = (gambit.kind, gambit.source_index, gambit.target_index)
        if key in seen:
            continue
        seen.add(key)
        unique.append(gambit)
    return unique
