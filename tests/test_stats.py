import json

from sts_bot.stats import RunLog, summarize


def test_records_each_run_once(load_message, tmp_path):
    log = RunLog(tmp_path / "runs.jsonl")
    game_over = load_message("game_over").state
    summary = log.observe(game_over)
    assert summary["floor"] == 16 and not summary["victory"]
    assert summary["killed_by"] == ["Acid Slime (M)"]
    assert log.observe(game_over) is None  # the game sends the screen more than once
    log.observe(None)  # main menu
    assert log.observe(game_over) is not None  # a new run, even with the same seed
    assert len((tmp_path / "runs.jsonl").read_text().splitlines()) == 2


def test_summary():
    runs = [
        {"victory": False, "floor": 16, "killed_by": ["Slime Boss"]},
        {"victory": False, "floor": 20, "killed_by": ["Gremlin Leader"]},
        {"victory": True, "floor": 51, "killed_by": None},
    ]
    text = summarize(json.loads(json.dumps(runs)))
    assert "runs: 3" in text and "wins: 1 (33%)" in text and "beat act 1: 2 (67%)" in text
    assert summarize([]) == "no runs recorded"
