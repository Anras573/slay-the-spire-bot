"""Copy one example message per screen type from a recording into test fixtures.

Usage: python scripts/extract_fixtures.py SESSION.jsonl [OUT_DIR]

Writes OUT_DIR/<name>.json (default tests/fixtures), one per screen type, plus
"combat" for a turn where cards can be played and "paused" for a state with the
settings menu open. Existing fixtures are not overwritten.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def fixture_name(message: dict) -> str | None:
    state = message.get("game_state")
    if not state:
        return "main_menu" if not message.get("in_game") else None
    if state.get("is_screen_up") and state.get("screen_name") == "SETTINGS":
        return "paused"
    screen_type = state.get("screen_type", "NONE")
    if screen_type != "NONE":
        return screen_type.lower()
    if state.get("combat_state") and "play" in message.get("available_commands", []):
        return "combat"
    return None


def main() -> None:
    source = Path(sys.argv[1])
    out_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("tests/fixtures")
    out_dir.mkdir(parents=True, exist_ok=True)
    with source.open(encoding="utf-8") as lines:
        for line in lines:
            message = json.loads(line)["message"]
            name = fixture_name(message)
            path = out_dir / f"{name}.json"
            if name and not path.exists():
                path.write_text(json.dumps(message, indent=1) + "\n", encoding="utf-8")
                print(f"wrote {path}")


if __name__ == "__main__":
    main()
