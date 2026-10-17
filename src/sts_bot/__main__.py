"""Entry point: ``python -m sts_bot``, launched by CommunicationMod."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from .agent import IDLE_COMMAND, Agent
from .protocol import Connection
from .recorder import Recorder
from .stats import RunLog

log = logging.getLogger("sts_bot")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--character",
        default="ironclad",
        choices=["ironclad", "silent", "defect", "watcher"],
    )
    parser.add_argument("--ascension", type=int, default=0)
    parser.add_argument(
        "--log-dir",
        type=Path,
        default=Path.home() / ".sts_bot" / "logs",
        help="where to write bot logs and game recordings "
        "(the game sets the working directory, so use an absolute path)",
    )
    args = parser.parse_args(argv)

    args.log_dir.mkdir(parents=True, exist_ok=True)
    # Never log to stdout: it is the command channel to the game.
    logging.basicConfig(
        filename=args.log_dir / "bot.log",
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    connection = Connection()
    agent = Agent(character=args.character, ascension=args.ascension)
    recorder = Recorder(args.log_dir)
    runs = RunLog(args.log_dir / "runs.jsonl")
    log.info("starting; recording to %s", recorder.path)

    connection.signal_ready()
    paused = False
    try:
        for message in connection.messages():
            if message.state and message.state.is_paused != paused:
                paused = message.state.is_paused
                if paused:
                    log.warning("the settings menu is open, which pauses the game; close it")
                else:
                    log.info("the settings menu was closed")
            summary = runs.observe(message.state)
            if summary:
                log.info("run over: %s", summary)
            try:
                command = agent.decide(message)
            except Exception:
                log.exception("agent failed on %s", message.raw)
                command = IDLE_COMMAND if message.ready_for_command else None
            if message.error:
                log.warning("game reported error: %s", message.error)
            recorder.record(message.raw, command)
            if command is not None:
                log.info("%s -> %s", message.screen_type, command)
                connection.send(command)
    finally:
        recorder.close()
        log.info("game closed the connection; exiting")


if __name__ == "__main__":
    main()
