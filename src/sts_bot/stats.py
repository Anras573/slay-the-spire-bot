"""Per-run results, so changes to the rules can be measured.

The bot appends one JSON line per finished run to ``runs.jsonl`` in its log
folder. Summarise them with ``python -m sts_bot.stats [runs.jsonl]``.
"""

from __future__ import annotations

import json
import sys
import time
from collections import Counter
from pathlib import Path

from . import __version__
from .state import GameOverScreen, GameState


def run_summary(state: GameState, screen: GameOverScreen) -> dict:
    combat = state.combat
    killed_by = [m.name for _, m in combat.targetable_monsters] if combat else []
    return {
        "time": time.time(),
        "bot_version": __version__,
        "character": state.character,
        "ascension": state.ascension_level,
        "seed": state.seed,
        "victory": screen.victory,
        "score": screen.score,
        "act": state.act,
        "floor": state.floor,
        "room": state.room_type,
        "killed_by": None if screen.victory else killed_by,
        "deck_size": len(state.deck),
        "relics": [r.id for r in state.relics],
    }


class RunLog:
    """Appends a summary the first time each run's game-over screen appears."""

    def __init__(self, path: Path) -> None:
        self.path = path
        self._recorded_seed: int | None = None

    def observe(self, state: GameState | None) -> dict | None:
        if state is None:
            self._recorded_seed = None  # back at the main menu
            return None
        if not isinstance(state.screen, GameOverScreen):
            return None
        if state.seed == self._recorded_seed:
            return None
        self._recorded_seed = state.seed
        summary = run_summary(state, state.screen)
        with self.path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(summary) + "\n")
        return summary


def summarize(runs: list[dict]) -> str:
    if not runs:
        return "no runs recorded"
    wins = sum(r["victory"] for r in runs)
    floors = sorted(r["floor"] for r in runs)
    act1 = sum(r["floor"] > 16 or r["victory"] for r in runs)
    killers = Counter(", ".join(r["killed_by"]) or "?" for r in runs if not r["victory"])
    lines = [
        f"runs: {len(runs)}",
        f"wins: {wins} ({wins / len(runs):.0%})",
        f"beat act 1: {act1} ({act1 / len(runs):.0%})",
        f"floor reached: median {floors[len(floors) // 2]}, best {floors[-1]}",
        "deadliest: " + "; ".join(f"{name} x{n}" for name, n in killers.most_common(5)),
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    args = sys.argv[1:] if argv is None else argv
    path = Path(args[0]) if args else Path.home() / ".sts_bot" / "logs" / "runs.jsonl"
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    print(summarize([json.loads(line) for line in lines if line.strip()]))


if __name__ == "__main__":
    main()
