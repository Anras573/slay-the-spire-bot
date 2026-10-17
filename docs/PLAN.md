# Plan

The goal is a bot that plays Slay the Spire (the first game) and wins runs.

## Architecture

```
Slay the Spire ── CommunicationMod ──stdin (JSON state)──▶ sts_bot (Python)
                                   ◀─stdout (commands)───
```

- **Game connection:** [CommunicationMod](https://github.com/ForgottenArbiter/CommunicationMod),
  running on ModTheSpire and BaseMod. It sends the full game state as JSON and accepts text
  commands, so we read no memory and scrape no screens.
- **Bot:** a Python process. `protocol.py` handles the wire format, `state.py` turns the JSON
  into typed classes, `agent.py` makes decisions and `recorder.py` saves everything it sees as
  JSON Lines.

### Command cheat sheet

| Command | Meaning |
| --- | --- |
| `start <class> [ascension] [seed]` | Start a run from the main menu |
| `play <card> [target]` | Play a card. Hand cards are numbered from **1**, monsters from 0, and dead monsters keep their slot |
| `end` | End the turn |
| `potion use\|discard <slot> [target]` | Use or discard a potion |
| `choose <index\|name>` | Pick from `choice_list` (rewards, map, events, shop, card grids) |
| `proceed` / `confirm`, `skip` / `cancel` / `return` / `leave` | The right-hand and left-hand screen buttons |
| `state` | Ask for the current state |
| `wait <frames>` | Wait, then send the state |

Each message lists the commands that are valid right now in `available_commands`.

## Roadmap

### 1. Plumbing ✅
- Python project skeleton, stdin/stdout loop, JSON recordings, file logging.
- A trivial agent that never gets stuck (it detects repeated states and moves on).
- **Done when:** the bot plays complete runs unattended, losing is fine.

### 2. State model ✅
- Typed classes (dataclasses) for the player, cards, monsters, relics, potions, the map and
  each screen, parsed from the JSON.
- Turn recorded sessions into test fixtures so decisions can be tested without the game
  (`scripts/extract_fixtures.py`).
- **Done when:** the agent no longer touches raw dicts.
- Still untyped (no recording yet, as the bot skips them): shops, boss relic rewards, hand
  selection, and Defect orbs. They parse as `UnknownScreen` or raw dicts until we have data.

### Learned from the first recordings
- On the first message of a fight, every monster's intent is `DEBUG` (not set yet). Real
  intents arrive with the next state, so block decisions on turn 1 need to wait for them.
- The settings menu (`screen_name: SETTINGS`) pauses the game. The bot can only wait it out;
  it logs a warning when this happens.

### 3. Rule-based bot (first version in place; needs in-game runs)
- **Combat** (`combat.py`): use potions when about to die (defensive ones first) and to open
  elite and boss fights (saving defensive ones); kill a monster when a card can; block when
  incoming damage beats current block; play powers; attack the weakest monster, preferring
  area damage against groups. Damage and block follow strength, weak, vulnerable, dexterity
  and frail. Card numbers come from `cards.py`, which covers most Ironclad cards.
- **Card rewards** (`cards.py`, `choices.py`): a score per Ironclad card; take the best if it
  clears a bar that rises once the deck has 20 cards, otherwise skip.
- **Map** (`pathing.py`): score every path to the top; elites only when healthy, rest sites
  when hurt.
- **Rest sites, upgrades, removals** (`choices.py`): rest below half HP (or below 80% before
  the boss), otherwise upgrade; upgrade Bash first; remove curses, then Strikes.
- **Run statistics** (`stats.py`): one line per run in `runs.jsonl`;
  `python -m sts_bot.stats` prints win rate, act 1 clear rate, floors and the deadliest fights.
- Not covered yet: shops (skipped), events (first option), boss relics (first option), card
  draw and exhaust synergies, and characters other than Ironclad.
- **Done when:** it reliably beats Act 1 with Ironclad at Ascension 0.

### 4. Combat search
- A combat simulator that applies card effects, powers and monster moves.
- Search over the sequences of plays in a turn (beam search, then MCTS) and score the
  resulting states.
- Consider [sts_lightspeed](https://github.com/gamerpuppy/sts_lightspeed) (a fast C++ simulator
  with Python bindings) instead of writing our own simulator.

### 5. Learning (optional)
- Train value or policy models for card picks and pathing, using the recorded runs
  and simulator self-play.

## Testing strategy

- Unit tests run on hand-written and recorded states: `pytest`.
- Watch the bot in the real game, using `bot.log` and the session recordings to diagnose
  bad decisions.
