"""The rule-based agent: turns each message from the game into a command.

Combat goes to ``combat``, map routing to ``pathing`` and other screens to
``choices``. Screens without rules yet (shops, events, boss relics) take the
first option or move on. Whatever happens, the agent should never get stuck:
if the game state stops changing, it falls back to commands that move on.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable

from . import choices, combat, pathing
from .protocol import Message
from .state import (
    CardRewardScreen,
    CombatRewardScreen,
    CombatState,
    GameState,
    GridScreen,
    MapScreen,
    RestScreen,
)

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

# On the first message of a fight, monsters haven't picked their moves yet.
# Wait this many times for their intents before playing blind.
INTENT_WAITS = 3
INTENT_WAIT_COMMAND = "wait 10"


class Agent:
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
        self._intent_waits: dict[tuple[int, int], int] = {}
        self._declined_card_floor: int | None = None

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

        state = message.state
        in_combat = state is not None and state.combat is not None
        if self._repeats >= STUCK_THRESHOLD:
            if in_combat and "end" in commands:
                return "end"
            return self._escape(commands)

        if state is None:
            return self._escape(commands)
        if state.combat and ("play" in commands or "end" in commands):
            return self._combat(state, state.combat, commands)
        return self._screen(state, commands)

    def _track_repeats(self, message: Message) -> None:
        key = json.dumps(message.raw, sort_keys=True)
        self._repeats = self._repeats + 1 if key == self._last_state_key else 0
        self._last_state_key = key

    def _combat(self, state: GameState, fight: CombatState, commands: set[str]) -> str:
        if not combat.intents_known(fight) and "wait" in commands:
            key = (state.floor, fight.turn)
            waits = self._intent_waits.get(key, 0)
            if waits < INTENT_WAITS:
                self._intent_waits[key] = waits + 1
                self._repeats = 0  # an unchanged state here is expected
                return INTENT_WAIT_COMMAND
        if "potion" in commands:
            potion = combat.choose_potion(state)
            if potion:
                return potion
        if "play" in commands:
            play = combat.choose_play(fight)
            if play:
                return play.command()
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
        if "choose" not in commands or not state.choice_list:
            return self._escape(commands)

        index: int | None = 0
        match state.screen:
            case CardRewardScreen() as rewards:
                index = choices.card_reward(rewards, state)
                if index is None:
                    # Skipping leaves the card in the reward list; remember
                    # not to open it again on this floor.
                    self._declined_card_floor = state.floor
                    return "skip" if "skip" in commands else self._escape(commands)
            case CombatRewardScreen() as rewards:
                skip_cards = self._declined_card_floor == state.floor
                index = choices.combat_reward(rewards, state, skip_cards=skip_cards)
            case RestScreen() as rest:
                index = choices.rest(rest, state)
            case GridScreen() as grid:
                index = choices.grid(grid)
            case MapScreen() as map_screen:
                index = pathing.choose_next_node(map_screen, state)
        if index is None:
            return self._escape(commands)
        return f"choose {index}"

    def _escape(self, commands: set[str]) -> str:
        options = [c for c in ESCAPE_COMMANDS if c in commands]
        if not options:
            return IDLE_COMMAND
        # Cycle through the options in case the first one doesn't help.
        return options[max(self._repeats - STUCK_THRESHOLD, 0) % len(options)]
