"""Combat rules on hand-built fights."""

from dataclasses import replace

from sts_bot.combat import block, choose_play, choose_potion, damage
from sts_bot.state import (
    Card,
    CombatState,
    GameState,
    Monster,
    Player,
    Potion,
    Power,
    UnknownScreen,
)


def card(card_id, card_type="ATTACK", cost=1, target=None, upgrades=0, playable=True):
    has_target = card_type == "ATTACK" if target is None else target
    return Card(id=card_id, name=card_id.removesuffix("_R"), uuid=card_id, type=card_type,
                rarity="COMMON", cost=cost, upgrades=upgrades, has_target=has_target,
                is_playable=playable)  # fmt: skip


STRIKE = card("Strike_R")
DEFEND = card("Defend_R", "SKILL", target=False)
BASH = card("Bash", cost=2)
CLEAVE = card("Cleave", target=False)
INFLAME = card("Inflame", "POWER", target=False)


def monster(hp=40, attack=0, hits=1, block_=0, powers=(), gone=False):
    return Monster(id="m", name="m", current_hp=hp, max_hp=hp, block=block_,
                   intent="ATTACK" if attack else "BUFF", move_adjusted_damage=attack or -1,
                   move_hits=hits, is_gone=gone, powers=powers)  # fmt: skip


def fight(hand, monsters, energy=3, hp=50, block_=0, powers=()):
    player = Player(current_hp=hp, max_hp=80, block=block_, energy=energy, powers=powers)
    return CombatState(player=player, monsters=tuple(monsters), hand=tuple(hand), turn=2)


def test_damage_applies_strength_weak_and_vulnerable():
    strong = fight([STRIKE], [monster()], powers=(Power("Strength", "Strength", 2),))
    assert damage(STRIKE, strong, strong.monsters[0]) == 8
    vulnerable = monster(powers=(Power("Vulnerable", "Vulnerable", 1),))
    assert damage(STRIKE, fight([STRIKE], [vulnerable]), vulnerable) == 9
    weak = fight([STRIKE], [monster()], powers=(Power("Weakened", "Weakened", 1),))
    assert damage(STRIKE, weak, weak.monsters[0]) == 4  # floor(6 * 0.75)
    assert damage(replace(STRIKE, upgrades=1), weak, weak.monsters[0]) == 6


def test_heavy_blade_multiplies_strength():
    blade = card("Heavy Blade", cost=2)
    strong = fight([blade], [monster()], powers=(Power("Strength", "Strength", 2),))
    assert damage(blade, strong, strong.monsters[0]) == 14 + 2 * 3


def test_block_applies_dexterity_and_frail():
    player = Player(current_hp=50, max_hp=80, powers=(Power("Dexterity", "Dexterity", 2),))
    assert block(DEFEND, player) == 7
    frail = Player(current_hp=50, max_hp=80, powers=(Power("Frail", "Frail", 1),))
    assert block(DEFEND, frail) == 3


def test_kills_when_it_can():
    state = fight([DEFEND, STRIKE], [monster(hp=30, attack=20), monster(hp=6, attack=5)])
    assert choose_play(state).command() == "play 2 1"


def test_blocks_incoming_damage_before_attacking():
    state = fight([STRIKE, DEFEND], [monster(attack=10)])
    assert choose_play(state).command() == "play 2"


def test_existing_block_counts():
    state = fight([STRIKE, DEFEND], [monster(attack=10)], block_=10)
    assert choose_play(state).command() == "play 1 0"


def test_multi_hit_attacks_add_up():
    state = fight([STRIKE, DEFEND], [monster(attack=3, hits=2)], block_=5)
    assert choose_play(state).command() == "play 2"  # 6 incoming beats 5 block


def test_plays_powers_when_safe():
    assert choose_play(fight([STRIKE, INFLAME], [monster()])).command() == "play 2"


def test_attacks_the_weakest_monster():
    state = fight([STRIKE], [monster(hp=30), monster(hp=12, block_=0), monster(hp=20)])
    assert choose_play(state).command() == "play 1 1"


def test_prefers_area_damage_against_groups():
    state = fight([STRIKE, CLEAVE], [monster(hp=30), monster(hp=30), monster(hp=30)])
    assert choose_play(state).command() == "play 2"


def test_dead_monsters_are_not_targeted():
    state = fight([STRIKE], [monster(gone=True, hp=0), monster(hp=30)])
    assert choose_play(state).command() == "play 1 1"


def test_respects_energy():
    assert choose_play(fight([BASH], [monster()], energy=1)) is None


def test_never_pays_hp_it_does_not_have():
    hemokinesis = card("Hemokinesis")
    assert choose_play(fight([hemokinesis], [monster()], hp=2)) is None
    assert choose_play(fight([hemokinesis], [monster()], hp=3)) is not None


def test_plays_leftover_skills_before_ending_the_turn():
    flex = card("Flex", "SKILL", cost=0, target=False)
    assert choose_play(fight([flex], [monster()])).command() == "play 1"


def test_ends_turn_with_only_curses():
    curse = card("Regret", "CURSE", cost=-2, target=False, playable=False)
    assert choose_play(fight([curse], [monster()])) is None


def game(combat, room="MonsterRoom", potions=()):
    return GameState(
        screen_type="NONE", screen=UnknownScreen("NONE"), choice_list=(), character="IRONCLAD",
        ascension_level=0, seed=0, act=1, floor=5, act_boss="", current_hp=combat.player.current_hp,
        max_hp=80, gold=0, deck=(), relics=(), potions=tuple(potions), map=(), room_type=room,
        combat=combat,
    )  # fmt: skip


FIRE = Potion("Fire Potion", "Fire Potion", can_use=True, requires_target=True)
BLOCK = Potion("Block Potion", "Block Potion", can_use=True)


def test_keeps_potions_in_normal_fights():
    assert choose_potion(game(fight([], [monster(attack=5)]), potions=[FIRE])) is None


def test_uses_potions_at_the_start_of_elite_fights():
    state = replace(fight([], [monster(hp=40), monster(hp=10)]), turn=1)
    assert choose_potion(game(state, "MonsterRoomElite", [FIRE])) == "potion use 0 1"


def test_prefers_defensive_potions_when_about_to_die():
    state = fight([], [monster(attack=60)])
    assert choose_potion(game(state, potions=[FIRE, BLOCK])) == "potion use 1"


def test_saves_defensive_potions_at_the_start_of_big_fights():
    state = replace(fight([], [monster(attack=5)]), turn=1)
    assert choose_potion(game(state, "MonsterRoomBoss", [BLOCK])) is None
    assert choose_potion(game(state, "MonsterRoomBoss", [BLOCK, FIRE])) == "potion use 1 0"
