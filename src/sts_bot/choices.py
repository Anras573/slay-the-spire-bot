"""Rule-based decisions outside combat: rewards, rest sites and card grids.

Each function returns an index into the screen's choices (which lines up with
the game's ``choice_list``), or None to skip or move on.
"""

from __future__ import annotations

from . import cards
from .state import (
    Card,
    CardRewardScreen,
    CombatRewardScreen,
    GameState,
    GridScreen,
    RestScreen,
)

# Card rewards must score at least this much to be taken. Thin decks draw
# their best cards more often, so the bar rises as the deck grows.
MIN_REWARD_SCORE = 45
MIN_REWARD_SCORE_LARGE_DECK = 60
LARGE_DECK = 20

# Act bosses are on floors 16, 33 and 50; the rest site before them is the
# last chance to heal.
BOSS_FLOORS = (16, 33, 50)
REST_BELOW_HP = 0.5
REST_BEFORE_BOSS_BELOW_HP = 0.8


def card_reward(screen: CardRewardScreen, state: GameState) -> int | None:
    if not screen.cards:
        return None
    index, best = max(enumerate(screen.cards), key=lambda c: cards.reward_score(c[1]))
    bar = MIN_REWARD_SCORE_LARGE_DECK if len(state.deck) >= LARGE_DECK else MIN_REWARD_SCORE
    return index if cards.reward_score(best) >= bar else None


def combat_reward(
    screen: CombatRewardScreen, state: GameState, skip_cards: bool = False
) -> int | None:
    """Take every reward, except potions when there's no free slot.

    ``skip_cards`` leaves card rewards alone, once we've looked and declined.
    """
    slots_full = all(not p.is_empty_slot for p in state.potions)
    for index, reward in enumerate(screen.rewards):
        if reward.reward_type == "POTION" and slots_full:
            continue
        if reward.reward_type == "CARD" and skip_cards:
            continue
        return index
    return None


def rest(screen: RestScreen, state: GameState) -> int | None:
    if not screen.rest_options:
        return None
    hp = state.current_hp / max(state.max_hp, 1)
    before_boss = state.floor + 1 in BOSS_FLOORS
    wants_rest = hp < REST_BELOW_HP or (before_boss and hp < REST_BEFORE_BOSS_BELOW_HP)
    preference = ["rest", "smith"] if wants_rest else ["smith", "rest"]
    for option in preference:
        if option in screen.rest_options:
            return screen.rest_options.index(option)
    return 0


def _upgrade_score(card: Card) -> int:
    if card.id == "Bash":
        return 90  # the starter card that gains the most from an upgrade
    if card.id in ("Strike_R", "Defend_R"):
        return 10
    return cards.reward_score(card)


def _removal_score(card: Card) -> int:
    if card.type == "CURSE":
        return 100
    return {"Strike_R": 50, "Defend_R": 40}.get(card.id, 100 - cards.reward_score(card) - 50)


def grid(screen: GridScreen) -> int | None:
    """Which card to pick on a card grid (upgrade, remove or transform)."""
    selected = {c.uuid for c in screen.selected_cards}
    candidates = [(i, c) for i, c in enumerate(screen.cards) if c.uuid not in selected]
    if not candidates:
        return None
    if screen.for_upgrade:
        candidates = [(i, c) for i, c in candidates if not c.upgrades or c.id == "Searing Blow"]
        key = _upgrade_score
    elif screen.for_purge or screen.for_transform:
        key = _removal_score
    else:
        return candidates[0][0]
    if not candidates:
        return None
    index, _ = max(candidates, key=lambda c: key(c[1]))
    return index
