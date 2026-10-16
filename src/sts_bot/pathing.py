"""Rule-based map routing: score every path to the top, take the best one."""

from __future__ import annotations

from functools import cache

from .state import GameState, MapNode, MapScreen

HEALTHY = 0.75  # fraction of max HP above which elites are worth fighting
WOUNDED = 0.5  # fraction of max HP below which rest sites are worth a lot


def node_value(symbol: str, hp_fraction: float) -> float:
    """How much we want to visit a room of this type right now."""
    if symbol == "E":
        return 1.5 if hp_fraction >= HEALTHY else -3.0
    if symbol == "R":
        return 3.0 if hp_fraction < WOUNDED else 1.0
    return {
        "M": 1.0,  # a card reward, for a little HP
        "T": 1.5,  # a free relic
        "?": 0.8,
        "$": 0.0,  # the bot doesn't shop yet
    }.get(symbol, 0.0)


def choose_next_node(screen: MapScreen, state: GameState) -> int:
    """Index of the next node to travel to."""
    if len(screen.next_nodes) < 2:
        return 0  # one way forward, or only the boss is left
    hp = state.current_hp / max(state.max_hp, 1)
    nodes: dict[tuple[int, int], MapNode] = {(n.x, n.y): n for n in state.map}

    @cache
    def best_path(x: int, y: int) -> float:
        node = nodes.get((x, y))
        if node is None:
            return 0.0
        onward = [best_path(cx, cy) for cx, cy in node.children]
        return node_value(node.symbol, hp) + max(onward, default=0.0)

    scores = [
        best_path(n.x, n.y) if (n.x, n.y) in nodes else node_value(n.symbol, hp)
        for n in screen.next_nodes
    ]
    return max(range(len(scores)), key=scores.__getitem__)
