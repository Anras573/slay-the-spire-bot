import io
import json

from sts_bot.agent import IDLE_COMMAND, SimpleAgent
from sts_bot.protocol import Connection, Message


def message(commands, in_game=True, ready=True, **state):
    data = {"available_commands": commands, "ready_for_command": ready, "in_game": in_game}
    if state:
        data["game_state"] = state
    return Message.from_dict(data)


def card(playable=True, target=False):
    return {"name": "Strike", "is_playable": playable, "has_target": target}


def monster(hp=10, gone=False):
    return {"name": "Cultist", "current_hp": hp, "is_gone": gone, "half_dead": False}


def combat(hand, monsters, commands=("play", "end")):
    return message(
        list(commands),
        screen_type="NONE",
        combat_state={"hand": hand, "monsters": monsters},
    )


def test_starts_a_run_from_the_main_menu():
    agent = SimpleAgent(character="defect", ascension=5)
    assert agent.decide(message(["start", "state"], in_game=False)) == "start defect 5"


def test_waits_when_not_ready():
    assert SimpleAgent().decide(message(["state"], ready=False)) is None


def test_plays_first_playable_card_with_one_based_index():
    msg = combat([card(playable=False), card()], [monster()])
    assert SimpleAgent().decide(msg) == "play 2"


def test_targets_first_living_monster():
    msg = combat([card(target=True)], [monster(gone=True), monster(hp=0), monster()])
    assert SimpleAgent().decide(msg) == "play 1 2"


def test_ends_turn_when_nothing_playable():
    msg = combat([card(playable=False)], [monster()])
    assert SimpleAgent().decide(msg) == "end"


def test_picks_first_choice_on_screens():
    msg = message(["choose", "skip"], screen_type="CARD_REWARD", choice_list=["bash", "anger"])
    assert SimpleAgent().decide(msg) == "choose 0"


def test_skips_the_shop():
    msg = message(["choose", "proceed"], screen_type="SHOP_ROOM", choice_list=["shop"])
    assert SimpleAgent().decide(msg) == "proceed"


def test_proceeds_when_nothing_to_choose():
    msg = message(["proceed"], screen_type="COMBAT_REWARD", choice_list=[])
    assert SimpleAgent().decide(msg) == "proceed"


def test_escapes_when_the_same_state_repeats():
    agent = SimpleAgent()
    msg = message(["choose", "proceed"], screen_type="COMBAT_REWARD", choice_list=["potion"])
    assert agent.decide(msg) == "choose 0"
    assert agent.decide(msg) == "choose 0"
    assert agent.decide(msg) == "proceed"


def test_error_replies_reuse_last_state():
    agent = SimpleAgent()
    agent.decide(message(["choose", "proceed"], screen_type="EVENT", choice_list=["a"]))
    error = Message.from_dict({"error": "Invalid command", "ready_for_command": True})
    agent.decide(error)
    assert agent.decide(error) == "proceed"


def test_idles_when_no_command_applies():
    assert SimpleAgent().decide(message(["state", "wait"], screen_type="NONE")) == IDLE_COMMAND


def test_connection_reads_json_lines_and_writes_commands():
    inp = io.StringIO(json.dumps({"ready_for_command": True, "in_game": False}) + "\n\n")
    out = io.StringIO()
    conn = Connection(inp, out)
    conn.signal_ready()
    messages = list(conn.messages())
    conn.send("end")
    assert len(messages) == 1 and messages[0].ready_for_command
    assert out.getvalue() == "ready\nend\n"
