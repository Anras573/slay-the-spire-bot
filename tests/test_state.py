"""Parsing tests against messages recorded from the real game."""

from pathlib import Path

import pytest

from sts_bot.protocol import Message
from sts_bot.state import (
    CardRewardScreen,
    ChestScreen,
    CombatRewardScreen,
    EventScreen,
    GameOverScreen,
    GameState,
    GridScreen,
    MapScreen,
    RestScreen,
    UnknownScreen,
)

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.mark.parametrize("name", sorted(p.stem for p in FIXTURES.glob("*.json")))
def test_every_fixture_parses_into_a_typed_screen(load_message, name):
    message = load_message(name)
    if name == "main_menu":
        assert message.state is None
        return
    assert message.state is not None
    assert not isinstance(message.state.screen, UnknownScreen)


def test_run_summary(load_message):
    state = load_message("map").state
    assert state.character == "IRONCLAD"
    assert state.act == 1
    assert state.max_hp == 80
    assert state.act_boss
    assert state.deck
    assert state.relics[0].name == "Burning Blood"
    assert all(p.is_empty_slot for p in state.potions)
    assert state.map and all(n.symbol for n in state.map)


def test_combat_at_fight_start(load_message):
    combat = load_message("combat").state.combat
    assert combat.turn == 1
    assert combat.player.energy == 3
    assert [c.name for c in combat.hand] == ["Strike", "Defend", "Strike", "Strike", "Strike"]
    strike = combat.hand[0]
    assert strike.type == "ATTACK" and strike.cost == 1 and strike.has_target
    # Intents aren't set yet on the first message of a fight.
    assert {m.intent for m in combat.monsters} == {"DEBUG"}
    assert combat.incoming_damage == 0


def test_dead_monsters_keep_their_target_index(load_message):
    combat = load_message("combat_slime_boss").state.combat
    assert len(combat.monsters) == 7
    assert [i for i, _ in combat.targetable_monsters] == [6]
    # Dead slimes still report attack damage; only the living one counts.
    assert combat.incoming_damage == 7


def test_player_powers(load_message):
    player = load_message("combat_slime_boss").state.combat.player
    assert player.current_hp == 4
    assert {p.id: p.amount for p in player.powers} == {"Strength": 3, "Weakened": 1}


def test_screens(load_message):
    assert isinstance(load_message("event").state.screen, EventScreen)
    neow = load_message("event").state.screen
    assert neow.event_name == "Neow" and neow.options[0].label

    map_screen = load_message("map").state.screen
    assert isinstance(map_screen, MapScreen)
    assert [n.symbol for n in map_screen.next_nodes] and map_screen.current_node is not None

    reward = load_message("card_reward").state.screen
    assert isinstance(reward, CardRewardScreen) and len(reward.cards) == 3

    rewards = load_message("combat_reward").state.screen
    assert isinstance(rewards, CombatRewardScreen)
    assert {r.reward_type for r in rewards.rewards} <= {"GOLD", "POTION", "RELIC", "CARD"}

    rest = load_message("rest").state.screen
    assert isinstance(rest, RestScreen) and rest.rest_options == ("rest", "smith")

    grid = load_message("grid").state.screen
    assert isinstance(grid, GridScreen) and grid.for_purge and grid.num_cards == 1

    assert isinstance(load_message("chest").state.screen, ChestScreen)

    game_over = load_message("game_over").state.screen
    assert isinstance(game_over, GameOverScreen) and not game_over.victory


def test_settings_menu_means_paused(load_message):
    assert load_message("paused").state.is_paused
    assert not load_message("combat").state.is_paused


def test_missing_fields_get_defaults():
    state = GameState.from_dict({"screen_type": "SHOP_SCREEN", "combat_state": {"hand": [{}]}})
    assert isinstance(state.screen, UnknownScreen)
    assert state.combat.hand[0].cost == 0
    assert state.combat.player.current_hp == 0


def test_unparseable_state_does_not_crash():
    message = Message.from_dict({"in_game": True, "game_state": {"deck": "not a list"}})
    assert message.state is None
