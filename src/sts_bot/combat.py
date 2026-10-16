"""Rule-based combat: pick one action at a time, greedily.

In order of priority:
1. Use a potion when this turn's damage would kill us, or on turn 1 of an
   elite or boss fight.
2. Play a card that kills a monster.
3. Block when monsters will hit harder than our current block.
4. Play powers.
5. Attack the monster closest to death with the most damage per energy.
6. Play anything else that's playable, then end the turn.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from . import cards
from .state import Card, CombatState, GameState, Monster, Player, Power

ELITE_OR_BOSS_ROOMS = ("MonsterRoomElite", "MonsterRoomBoss")

# Potions that keep us alive, preferred when this turn's damage would kill us.
DEFENSIVE_POTIONS = ("Block Potion", "Blood Potion", "Fruit Juice", "Regen Potion", "GhostInAJar")


@dataclass(frozen=True)
class Play:
    hand_index: int  # 0-based position in the hand
    target: int | None = None

    def command(self) -> str:
        # CommunicationMod numbers hand cards from 1.
        command = f"play {self.hand_index + 1}"
        return command if self.target is None else f"{command} {self.target}"


def intents_known(combat: CombatState) -> bool:
    """False on the first message of a fight, before monsters pick their moves."""
    return all(m.intent != "DEBUG" for m in combat.monsters if m.is_targetable)


def _power(powers: tuple[Power, ...], power_id: str) -> int:
    return next((p.amount for p in powers if p.id == power_id), 0)


def energy_cost(card: Card, player: Player) -> int:
    return player.energy if card.cost == -1 else max(card.cost, 0)


def damage(card: Card, combat: CombatState, monster: Monster) -> int:
    """Damage the card deals to one monster, after strength, weak and vulnerable."""
    info = cards.data(card)
    player = combat.player
    base = info.value(info.damage, card)
    if card.id == "Body Slam":
        base = player.block
    elif card.id == "Perfected Strike":
        piles = combat.hand + combat.draw_pile + combat.discard_pile
        per_strike = 3 if card.upgrades else 2
        base += per_strike * sum(1 for c in piles if cards.is_strike(c))
    if base <= 0:
        return 0
    per_hit = base + _power(player.powers, "Strength") * info.value(info.strength_multiplier, card)
    if _power(player.powers, "Weakened"):
        per_hit *= 0.75
    if _power(monster.powers, "Vulnerable"):
        per_hit *= 1.5
    hits = player.energy if card.cost == -1 else info.value(info.hits, card)
    return max(math.floor(per_hit), 0) * hits


def block(card: Card, player: Player) -> int:
    info = cards.data(card)
    base = info.value(info.block, card)
    if base <= 0:
        return 0
    amount = base + _power(player.powers, "Dexterity")
    if _power(player.powers, "Frail"):
        amount *= 0.75
    return max(math.floor(amount), 0)


def _effective_hp(monster: Monster) -> int:
    return monster.current_hp + monster.block


def _playable(combat: CombatState) -> list[tuple[int, Card]]:
    player = combat.player
    result = []
    for index, card in enumerate(combat.hand):
        if not card.is_playable or energy_cost(card, player) > player.energy:
            continue
        if card.cost == -1 and player.energy == 0:
            continue  # X-cost card with nothing to spend
        hp_cost = cards.data(card).hp_cost
        if hp_cost and hp_cost >= player.current_hp:
            continue  # would kill us
        result.append((index, card))
    return result


def _per_energy(value: float, card: Card, player: Player) -> float:
    return value / max(energy_cost(card, player), 0.5)


def choose_play(combat: CombatState) -> Play | None:
    """The card to play next, or None to end the turn."""
    playable = _playable(combat)
    targets = combat.targetable_monsters
    if not playable or not targets:
        return None
    player = combat.player

    def play(index: int, card: Card, target: int | None) -> Play:
        return Play(index, target if card.has_target else None)

    # 2. Kill something. Prefer the monster that would hit us hardest.
    kills = []
    for index, card in playable:
        # Random-target attacks (e.g. Sword Boomerang) can't be aimed at a kill.
        if card.type != "ATTACK" or not (card.has_target or cards.data(card).aoe):
            continue
        for target, monster in targets:
            if damage(card, combat, monster) >= _effective_hp(monster):
                kills.append((-monster.incoming_damage, energy_cost(card, player), index, target))
                if not card.has_target:
                    break
    if kills:
        _, _, index, target = min(kills)
        return play(index, combat.hand[index], target)

    # 3. Block what's coming.
    need_block = combat.incoming_damage - player.block if intents_known(combat) else 0
    if need_block > 0:
        blockers = [(block(c, player), i, c) for i, c in playable if block(c, player) > 0]
        if blockers:
            _, index, card = max(blockers, key=lambda b: (_per_energy(b[0], b[2], player), b[0]))
            return play(index, card, targets[0][0])

    # 4. Powers pay off over the rest of the fight.
    for index, card in playable:
        if card.type == "POWER":
            return play(index, card, targets[0][0])

    # 5. Attack the monster closest to death.
    weakest_target, weakest = min(targets, key=lambda t: _effective_hp(t[1]))
    attacks = []
    for index, card in playable:
        if card.type != "ATTACK":
            continue
        dealt = damage(card, combat, weakest)
        if cards.data(card).aoe:
            dealt = sum(damage(card, combat, m) for _, m in targets)
        attacks.append((_per_energy(dealt, card, player), dealt, index))
    if attacks:
        _, _, index = max(attacks)
        return play(index, combat.hand[index], weakest_target)

    # 6. Use up the rest: skills (block is never wasted) and playable statuses.
    order = {"SKILL": 0, "STATUS": 1}
    rest = [(order.get(c.type, 2), i, c) for i, c in playable if c.type != "CURSE"]
    if rest:
        _, index, card = min(rest)
        return play(index, card, weakest_target)
    return None


def choose_potion(state: GameState) -> str | None:
    """A ``potion use`` command, or None to keep our potions."""
    combat = state.combat
    if combat is None or not intents_known(combat):
        return None
    usable = [(slot, p) for slot, p in enumerate(state.potions) if p.can_use]
    targets = combat.targetable_monsters
    if not usable or not targets:
        return None
    player = combat.player
    in_danger = combat.incoming_damage - player.block >= player.current_hp
    if in_danger:
        usable.sort(key=lambda u: u[1].id not in DEFENSIVE_POTIONS)
    elif state.room_type in ELITE_OR_BOSS_ROOMS and combat.turn == 1:
        # Open big fights with everything else; keep defensive potions for emergencies.
        usable = [u for u in usable if u[1].id not in DEFENSIVE_POTIONS]
    else:
        return None
    if not usable:
        return None
    slot, potion = usable[0]
    if potion.requires_target:
        target, _ = min(targets, key=lambda t: _effective_hp(t[1]))
        return f"potion use {slot} {target}"
    return f"potion use {slot}"
