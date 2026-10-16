"""A deliberately simple agent: its only job is to prove the plumbing works.

It plays the first playable card it can, takes the first option on every
screen and otherwise tries to move on. It will lose almost every run, but it
should never get stuck. Smarter agents replace ``decide``.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable

from .protocol import Message
from .state import CombatState, GameState

# Commands that move the game forward without choosing anything, in the order
# we prefer to try them.
ESCAPE_COMMANDS = ["proceed", "confirm", "leave", "skip", "return", "cancel"]

# Sent when there is nothing useful to do; the mod replies with a fresh state.
IDLE_COMMAND = "wait 30"

# After this many identical states in a row we assume our command isn't
# working (e.g. picking a potion with full potion slots) and try escapes.
STUCK_THRESHOLD = 2

# Starting a new run the moment the main menu appears after a game over has
# left the game stuck mid-transition, so give the menu time to settle first.
# The menu doesn't accept `wait`, so the bot pauses before replying instead.
RESTART_DELAY_SECONDS = 2.0


class SimpleAgent:
    def __init__(
        self,
        character: str = "ironclad",
        ascension: int = 0,
        restart_delay: float = RESTART_DELAY_SECONDS,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.character = character
        self.ascension = ascension
        self._restart_delay = restart_delay
        self._sleep = sleep
        self._was_in_game = False
        self._last_message: Message | None = None
        self._last_state_key: str | None = None
        self._repeats = 0

    def decide(self, message: Message) -> str | None:
        """Return the next command, or None if the game isn't ready for one."""
        if message.error is not None:
            # Error replies carry no game state; retry from the last known
            # state, counting the error as a sign we're stuck.
            self._repeats += 1
            if self._last_message is None or not message.ready_for_command:
                return IDLE_COMMAND if message.ready_for_command else None
            message = self._last_message
        else:
            self._track_repeats(message)
            self._last_message = message

        if not message.ready_for_command:
            return None

        commands = set(message.available_commands)
        if not message.in_game:
            if "start" in commands:
                if self._was_in_game:
                    self._sleep(self._restart_delay)
                    self._was_in_game = False
                return f"start {self.character} {self.ascension}"
            return IDLE_COMMAND
        self._was_in_game = True

        if self._repeats >= STUCK_THRESHOLD:
            return self._escape(commands)

        state = message.state
        if state is None:
            return self._escape(commands)
        if state.combat and ("play" in commands or "end" in commands):
            return self._combat(state.combat, commands)
        return self._screen(state, commands)

    def _track_repeats(self, message: Message) -> None:
        key = json.dumps(message.raw, sort_keys=True)
        self._repeats = self._repeats + 1 if key == self._last_state_key else 0
        self._last_state_key = key

    def _combat(self, combat: CombatState, commands: set[str]) -> str:
        if "play" in commands:
            targets = combat.targetable_monsters
            for index, card in enumerate(combat.hand):
                if not card.is_playable:
                    continue
                # CommunicationMod numbers hand cards from 1.
                if card.has_target:
                    if targets:
                        return f"play {index + 1} {targets[0][0]}"
                else:
                    return f"play {index + 1}"
        if "end" in commands:
            return "end"
        return self._escape(commands)

    def _screen(self, state: GameState, commands: set[str]) -> str:
        screen = state.screen_type
        if screen == "SHOP_ROOM" and "proceed" in commands:
            return "proceed"  # don't open the shop
        if screen == "SHOP_SCREEN" and "leave" in commands:
            return "leave"
        if screen in ("GRID", "HAND_SELECT") and "confirm" in commands:
            return "confirm"
        if "choose" in commands and state.choice_list:
            return "choose 0"
        return self._escape(commands)

    def _escape(self, commands: set[str]) -> str:
        options = [c for c in ESCAPE_COMMANDS if c in commands]
        if not options:
            return IDLE_COMMAND
        # Cycle through the options in case the first one doesn't help.
        return options[max(self._repeats - STUCK_THRESHOLD, 0) % len(options)]
