"""CommunicationMod wire protocol.

The game launches this process and talks to it over pipes:

* game -> bot: one JSON object per line on stdin, sent whenever the game is
  stable and waiting for input (or in reply to a command).
* bot -> game: one plain-text command per line on stdout.

Because stdout is the command channel, nothing else may ever be printed to it.
Use the ``logging`` module (configured to write to a file) instead of ``print``.
"""

from __future__ import annotations

import json
import sys
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import Any, TextIO


@dataclass(frozen=True)
class Message:
    """One message from CommunicationMod."""

    available_commands: list[str] = field(default_factory=list)
    ready_for_command: bool = False
    in_game: bool = False
    game_state: dict[str, Any] | None = None
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Message:
        return cls(
            available_commands=list(data.get("available_commands", [])),
            ready_for_command=bool(data.get("ready_for_command", False)),
            in_game=bool(data.get("in_game", False)),
            game_state=data.get("game_state"),
            error=data.get("error"),
            raw=data,
        )

    @property
    def screen_type(self) -> str | None:
        return self.game_state.get("screen_type") if self.game_state else None

    @property
    def in_combat(self) -> bool:
        return bool(self.game_state and self.game_state.get("combat_state"))


class Connection:
    """Reads messages from and sends commands to CommunicationMod."""

    def __init__(self, inp: TextIO = sys.stdin, out: TextIO = sys.stdout) -> None:
        self._in = inp
        self._out = out

    def signal_ready(self) -> None:
        """Must be sent once at startup, or CommunicationMod times out."""
        self.send("ready")

    def send(self, command: str) -> None:
        self._out.write(command + "\n")
        self._out.flush()

    def messages(self) -> Iterator[Message]:
        for line in self._in:
            line = line.strip()
            if line:
                yield Message.from_dict(json.loads(line))
