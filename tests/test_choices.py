"""Out-of-combat rules: rewards, rest sites, card grids and the map."""

from dataclasses import replace

from sts_bot import choices, pathing
from sts_bot.state import Card, CombatRewardScreen, GridScreen, MapNode, MapScreen, Potion, Reward


def card(card_id, card_type="ATTACK", upgrades=0):
    return Card(id=card_id, name=card_id, uuid=f"{card_id}-{upgrades}", type=card_type,
                rarity="COMMON", cost=1, upgrades=upgrades)  # fmt: skip


def test_takes_good_card_rewards(load_message):
    state = load_message("card_reward").state  # True Grit, Bloodletting, Flex
    assert choices.card_reward(state.screen, state) == 0


def test_skips_card_rewards_once_the_deck_is_big(load_message):
    state = load_message("card_reward").state
    big = replace(state, deck=state.deck * 3)
    assert choices.card_reward(state.screen, big) is None


def test_takes_rewards_but_not_potions_without_a_free_slot(load_message):
    state = load_message("map").state
    screen = CombatRewardScreen((Reward("POTION"), Reward("GOLD", gold=10)))
    assert choices.combat_reward(screen, state) == 0  # empty slots
    full = replace(state, potions=(Potion("Fire Potion", "Fire Potion"),) * 3)
    assert choices.combat_reward(screen, full) == 1
    assert choices.combat_reward(screen, state, skip_cards=True) == 0
    assert choices.combat_reward(CombatRewardScreen((Reward("CARD"),)), state, True) is None


def test_rests_when_hurt_and_upgrades_otherwise(load_message):
    state = load_message("rest").state
    screen = state.screen  # rest, smith
    assert choices.rest(screen, replace(state, current_hp=30, max_hp=80, floor=5)) == 0
    assert choices.rest(screen, replace(state, current_hp=70, max_hp=80, floor=5)) == 1
    # The rest site before the act boss is the last chance to heal.
    assert choices.rest(screen, replace(state, current_hp=55, max_hp=80, floor=15)) == 0


def test_upgrades_bash_first_and_removes_curses_then_strikes():
    deck = (card("Strike_R"), card("Bash"), card("Defend_R", "SKILL"), card("Regret", "CURSE"))
    assert choices.grid(GridScreen(cards=deck[:3], for_upgrade=True)) == 1
    assert choices.grid(GridScreen(cards=deck, for_purge=True)) == 3
    assert choices.grid(GridScreen(cards=deck[:3], for_purge=True)) == 0


def test_does_not_upgrade_twice():
    deck = (card("Bash", upgrades=1), card("Strike_R"))
    assert choices.grid(GridScreen(cards=deck, for_upgrade=True)) == 1


def node(x, y, symbol, children=()):
    return MapNode(x=x, y=y, symbol=symbol, children=tuple(children))


def map_state(load_message, hp):
    state = load_message("map").state
    #   y=1:  E (0,1)   R (2,1)
    #   y=0:  M (0,0)   M (2,0)
    nodes = (node(0, 0, "M", [(0, 1)]), node(2, 0, "M", [(2, 1)]), node(0, 1, "E"), node(2, 1, "R"))
    screen = MapScreen(current_node=None, next_nodes=nodes[:2])
    return screen, replace(state, map=nodes, current_hp=hp, max_hp=80)


def test_heads_for_elites_when_healthy(load_message):
    screen, state = map_state(load_message, hp=80)
    assert pathing.choose_next_node(screen, state) == 0


def test_heads_for_rest_sites_when_hurt(load_message):
    screen, state = map_state(load_message, hp=30)
    assert pathing.choose_next_node(screen, state) == 1


def test_recorded_map_choice_is_valid(load_message):
    state = load_message("map").state
    assert pathing.choose_next_node(state.screen, state) in range(len(state.choice_list))


def test_goes_to_the_boss_when_it_is_the_only_way_on(load_message):
    state = load_message("map").state
    boss_only = MapScreen(current_node=None, next_nodes=(), boss_available=True)
    assert pathing.choose_next_node(boss_only, state) == 0
