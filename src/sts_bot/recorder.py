"""Records every message and the command sent in reply as JSON Lines.

The recordings are the raw material for debugging, replaying decisions in tests
and, later on, training data.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any


class Recorder:
    def __init__(self, log_dir: Path) -> None:
        log_dir.mkdir(parents=True, exist_ok=True)
        self.path = log_dir / f"session-{time.strftime('%Y%m%d-%H%M%S')}.jsonl"
        self._file = self.path.open("a", encoding="utf-8")

    def record(self, message: dict[str, Any], command: str | None) -> None:
        entry = {"time": time.time(), "message": message, "command": command}
        self._file.write(json.dumps(entry) + "\n")
        self._file.flush()

    def close(self) -> None:
        self._file.close()
