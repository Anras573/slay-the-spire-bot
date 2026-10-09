# slay-the-spire-bot

A bot that plays Slay the Spire (the first game), written in Python. It talks to the
game through [CommunicationMod](https://github.com/ForgottenArbiter/CommunicationMod).

The current bot is a placeholder: it plays the first playable card, takes the first
option on every screen and records everything it sees. It exists to prove the
connection works. See [docs/PLAN.md](docs/PLAN.md) for the roadmap.

## How it works

The game launches the bot as a child process. Whenever the game waits for input,
CommunicationMod writes the game state as one JSON line to the bot's **stdin**. The bot
replies with a text command on **stdout**, for example `play 1 0`, `end`, `choose 2` or
`proceed`. Because stdout is the command channel, the bot logs only to files.

## Setup

1. **Python environment** (Python 3.10+):

   ```sh
   python -m venv .venv
   .venv/bin/pip install -e ".[dev]"      # Windows: .venv\Scripts\pip
   .venv/bin/pytest
   ```

2. **Mods.** Subscribe to these on the Steam Workshop:
   [ModTheSpire](https://steamcommunity.com/sharedfiles/filedetails/?id=1605060445),
   [BaseMod](https://steamcommunity.com/sharedfiles/filedetails/?id=1605833019) and
   CommunicationMod. Launch Slay the Spire with mods, enable all three, and start the
   game once so that CommunicationMod creates its config file.

3. **Point CommunicationMod at the bot.** Edit its `config.properties` (the locations
   for each OS are listed in
   [config/config.properties.example](config/config.properties.example)) and set
   `command` to the absolute path of the venv's Python followed by `-m sts_bot`.

4. **Run.** With `runAtGameStart=true` the bot starts with the game. Otherwise, start
   it from the main menu: Mods → CommunicationMod → Config → Start external process.
   The bot starts an Ironclad run and plays it.

## Options

```
python -m sts_bot [--character ironclad|silent|defect|watcher] [--ascension N] [--log-dir DIR]
```

Logs go to `~/.sts_bot/logs` by default:

- `bot.log`: what the bot decided and why it failed, if it did
- `session-*.jsonl`: every message received and the command sent in reply, for debugging
  and as test fixtures

If the bot fails to start, check `communication_mod_errors.log` in the game folder.
