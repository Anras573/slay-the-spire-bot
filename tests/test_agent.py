"""How the agent turns messages into commands: plumbing, fallbacks and routing."""

import io
import json

from sts_bot.agent import IDLE_COMMAND, INTENT_WAIT_COMMAND, INTENT_WAITS, Agent
from sts_bot.protocol import Connection, Message


def message(commands, in_game=True, ready=True, **state):
    data = {"available_commands": commands, "ready_for_command": ready, "in_game": in_game}
    if state:
        data["game_state"] = state
    return Message.from_dict(data)


def strike():
    return {"id": "Strike_R", "name": "Strike", "type": "ATTACK", "cost": 1,
            "is_playable": True, "has_target": True}  # fmt: skip


def fight(monsters, hand=None, commands=("play", "end", "wait")):
    return message(
        list(commands),
        screen_type="NONE",
        floor=3,
        combat_state={
            "hand": hand if hand is not None else [strike()],
            "monsters": monsters,
            "player": {"current_hp": 50, "max_hp": 80, "energy": 3},
            "turn": 1,
        },
    )


def cultist(intent="ATTACK", hp=40):
    return {"name": "Cultist", "current_hp": hp, "intent": intent,
            "move_adjusted_damage": 6, "move_hits": 1}  # fmt: skip


def test_starts_a_run_from_the_main_menu():
    agent = Agent(character="defect", ascension=5)
    assert agent.decide(message(["start", "state"], in_game=False)) == "start defect 5"


def test_pauses_before_starting_a_new_run_after_a_game():
    sleeps = []
    agent = Agent(restart_delay=2.0, sleep=sleeps.append)
    menu = message(["start", "state"], in_game=False)
    agent.decide(menu)
    assert sleeps == []  # no pause when the game has just been launched
    agent.decide(message(["proceed"], screen_type="GAME_OVER"))
    assert agent.decide(menu) == "start ironclad 0"
    assert sleeps == [2.0]


def test_waits_when_not_ready():
    assert Agent().decide(message(["state"], ready=False)) is None


def test_plays_cards_with_one_based_index():
    unplayable = {**strike(), "is_playable": False}
    assert Agent().decide(fight([cultist()], hand=[unplayable, strike()])) == "play 2 0"


def test_ends_turn_when_nothing_playable():
    assert Agent().decide(fight([cultist()], hand=[])) == "end"


def test_waits_for_intents_then_plays_anyway():
    agent = Agent()
    blind = fight([cultist(intent="DEBUG")])
    for _ in range(INTENT_WAITS):
        assert agent.decide(blind) == INTENT_WAIT_COMMAND
    assert agent.decide(blind) == "play 1 0"


def test_ends_turn_when_a_play_does_not_change_the_state():
    agent = Agent()
    stuck = fight([cultist()])
    assert agent.decide(stuck) == "play 1 0"
    assert agent.decide(stuck) == "play 1 0"
    assert agent.decide(stuck) == "end"


def test_skips_the_shop():
    msg = message(["choose", "proceed"], screen_type="SHOP_ROOM", choice_list=["shop"])
    assert Agent().decide(msg) == "proceed"


def test_takes_first_option_on_screens_without_rules():
    msg = message(["choose"], screen_type="EVENT", choice_list=["talk"])
    assert Agent().decide(msg) == "choose 0"


def test_proceeds_when_nothing_to_choose():
    msg = message(["proceed"], screen_type="COMBAT_REWARD", choice_list=[])
    assert Agent().decide(msg) == "proceed"


def test_escapes_when_the_same_state_repeats():
    agent = Agent()
    msg = message(["choose", "proceed"], screen_type="EVENT", choice_list=["a"])
    assert agent.decide(msg) == "choose 0"
    assert agent.decide(msg) == "choose 0"
    assert agent.decide(msg) == "proceed"


def test_error_replies_reuse_last_state():
    agent = Agent()
    agent.decide(message(["choose", "proceed"], screen_type="EVENT", choice_list=["a"]))
    error = Message.from_dict({"error": "Invalid command", "ready_for_command": True})
    agent.decide(error)
    assert agent.decide(error) == "proceed"


def test_idles_when_no_command_applies():
    assert Agent().decide(message(["state", "wait"], screen_type="NONE")) == IDLE_COMMAND


def test_declined_card_reward_is_not_reopened(load_message):
    agent = Agent()
    weak_cards = load_message("card_reward")  # True Grit, Bloodletting, Flex
    rewards = message(
        ["choose", "proceed"],
        screen_type="COMBAT_REWARD",
        floor=weak_cards.state.floor,
        choice_list=["card"],
        screen_state={"rewards": [{"reward_type": "CARD"}]},
    )
    assert agent.decide(rewards) == "choose 0"
    # True Grit scores 55, enough for a starter deck; make the deck large.
    big_deck = {**weak_cards.raw}
    big_deck["game_state"] = {**big_deck["game_state"], "deck": [strike()] * 25}
    assert agent.decide(Message.from_dict(big_deck)) == "skip"
    assert agent.decide(rewards) == "proceed"


def test_recorded_fight_waits_for_intents(load_message):
    # The first message of a fight has no intents yet.
    assert Agent().decide(load_message("combat")) == INTENT_WAIT_COMMAND


def test_recorded_boss_fight_drinks_block_potion_when_about_to_die(load_message):
    # 4 HP against 7 incoming damage, holding a Block Potion in slot 0.
    assert Agent().decide(load_message("combat_slime_boss")) == "potion use 0"


def test_recorded_paused_game_is_left_to_the_player(load_message):
    assert Agent().decide(load_message("paused")) == IDLE_COMMAND


def test_connection_reads_json_lines_and_writes_commands():
    inp = io.StringIO(json.dumps({"ready_for_command": True, "in_game": False}) + "\n\n")
    out = io.StringIO()
    conn = Connection(inp, out)
    conn.signal_ready()
    messages = list(conn.messages())
    conn.send("end")
    assert len(messages) == 1 and messages[0].ready_for_command
    assert out.getvalue() == "ready\nend\n"
