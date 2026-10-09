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
- **Bot:** a Python process. `protocol.py` handles the wire format, `agent.py` makes decisions
  and `recorder.py` saves everything it sees as JSON Lines.

### Command cheat sheet

| Command | Meaning |
| --- | --- |
| `start <class> [ascension] [seed]` | Start a run from the main menu |
| `play <card> [target]` | Play a card. Hand cards are numbered from **1**, monsters from 0 |
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

### 2. State model
- Typed classes (dataclasses) for the player, cards, monsters, relics, potions, the map and
  each screen, parsed from the JSON.
- Turn recorded sessions into test fixtures so decisions can be tested without the game.
- **Done when:** the agent no longer touches raw dicts.

### 3. Rule-based bot
- **Combat:** block when the incoming damage (from monster intents) would hurt, otherwise
  maximise damage. Kill the lowest-HP enemy first. Use potions in elite and boss fights.
- **Card rewards:** a ranked card list per character, plus deck-size awareness.
- **Map:** score paths (elites when healthy, rest sites before bosses, shops when rich).
- **Events, shops, rest sites:** simple heuristics.
- **Run statistics:** log the floor reached, the cause of death and the win rate per version.
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
