"""Typed model of the game state sent by CommunicationMod.

Only fields seen in real recordings are modelled. Parsing is lenient: a
missing field gets a default instead of raising, so a game or mod update that
drops a field doesn't crash the bot mid-run. Screens without a typed model yet
(shops, boss rewards, hand selection, ...) are parsed as ``UnknownScreen``,
which keeps the raw data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

Json = dict[str, Any]


def _list(data: Json, key: str) -> list[Any]:
    return data.get(key) or []


@dataclass(frozen=True)
class Power:
    id: str
    name: str
    amount: int
    just_applied: bool = False

    @classmethod
    def from_dict(cls, d: Json) -> Power:
        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            amount=d.get("amount", 0),
            just_applied=d.get("just_applied", False),
        )


def _powers(d: Json) -> tuple[Power, ...]:
    return tuple(Power.from_dict(p) for p in _list(d, "powers"))


@dataclass(frozen=True)
class Card:
    id: str
    name: str
    uuid: str
    type: str  # ATTACK, SKILL, POWER, STATUS, CURSE
    rarity: str  # BASIC, COMMON, UNCOMMON, RARE, SPECIAL, CURSE
    cost: int  # -1 for X cost, -2 for unplayable
    upgrades: int = 0
    has_target: bool = False
    is_playable: bool = False
    exhausts: bool = False
    ethereal: bool = False

    @classmethod
    def from_dict(cls, d: Json) -> Card:
        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            uuid=d.get("uuid", ""),
            type=d.get("type", ""),
            rarity=d.get("rarity", ""),
            cost=d.get("cost", 0),
            upgrades=d.get("upgrades", 0),
            has_target=d.get("has_target", False),
            is_playable=d.get("is_playable", False),
            exhausts=d.get("exhausts", False),
            ethereal=d.get("ethereal", False),
        )


def _cards(d: Json, key: str) -> tuple[Card, ...]:
    return tuple(Card.from_dict(c) for c in _list(d, key))


@dataclass(frozen=True)
class Relic:
    id: str
    name: str
    counter: int = -1

    @classmethod
    def from_dict(cls, d: Json) -> Relic:
        return cls(id=d.get("id", ""), name=d.get("name", ""), counter=d.get("counter", -1))


@dataclass(frozen=True)
class Potion:
    id: str
    name: str
    can_use: bool = False
    can_discard: bool = False
    requires_target: bool = False

    @property
    def is_empty_slot(self) -> bool:
        return self.id == "Potion Slot"

    @classmethod
    def from_dict(cls, d: Json) -> Potion:
        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            can_use=d.get("can_use", False),
            can_discard=d.get("can_discard", False),
            requires_target=d.get("requires_target", False),
        )


@dataclass(frozen=True)
class Monster:
    id: str
    name: str
    current_hp: int
    max_hp: int
    block: int = 0
    intent: str = ""  # ATTACK, DEFEND, BUFF, DEBUFF, ATTACK_DEBUFF, UNKNOWN, DEBUG, ...
    move_id: int = -1
    move_base_damage: int = -1
    move_adjusted_damage: int = -1  # after strength, vulnerable, etc.; -1 if not attacking
    move_hits: int = 0
    last_move_id: int | None = None
    second_last_move_id: int | None = None
    half_dead: bool = False
    is_gone: bool = False
    powers: tuple[Power, ...] = ()

    @property
    def is_targetable(self) -> bool:
        return self.current_hp > 0 and not self.is_gone and not self.half_dead

    @property
    def incoming_damage(self) -> int:
        """Total damage this monster's move will deal before block."""
        if not self.is_targetable or self.move_adjusted_damage < 0:
            return 0
        return self.move_adjusted_damage * max(self.move_hits, 1)

    @classmethod
    def from_dict(cls, d: Json) -> Monster:
        return cls(
            id=d.get("id", ""),
            name=d.get("name", ""),
            current_hp=d.get("current_hp", 0),
            max_hp=d.get("max_hp", 0),
            block=d.get("block", 0),
            intent=d.get("intent", ""),
            move_id=d.get("move_id", -1),
            move_base_damage=d.get("move_base_damage", -1),
            move_adjusted_damage=d.get("move_adjusted_damage", -1),
            move_hits=d.get("move_hits", 0),
            last_move_id=d.get("last_move_id"),
            second_last_move_id=d.get("second_last_move_id"),
            half_dead=d.get("half_dead", False),
            is_gone=d.get("is_gone", False),
            powers=_powers(d),
        )


@dataclass(frozen=True)
class Player:
    current_hp: int
    max_hp: int
    block: int = 0
    energy: int = 0
    powers: tuple[Power, ...] = ()
    # Not modelled yet: no Defect recording to learn the orb fields from.
    orbs: tuple[Json, ...] = ()

    @classmethod
    def from_dict(cls, d: Json) -> Player:
        return cls(
            current_hp=d.get("current_hp", 0),
            max_hp=d.get("max_hp", 0),
            block=d.get("block", 0),
            energy=d.get("energy", 0),
            powers=_powers(d),
            orbs=tuple(_list(d, "orbs")),
        )


@dataclass(frozen=True)
class CombatState:
    player: Player
    monsters: tuple[Monster, ...]
    hand: tuple[Card, ...]
    draw_pile: tuple[Card, ...] = ()
    discard_pile: tuple[Card, ...] = ()
    exhaust_pile: tuple[Card, ...] = ()
    limbo: tuple[Card, ...] = ()
    turn: int = 0
    cards_discarded_this_turn: int = 0
    times_damaged: int = 0

    @property
    def targetable_monsters(self) -> list[tuple[int, Monster]]:
        """(target index, monster) pairs. Dead monsters keep their index."""
        return [(i, m) for i, m in enumerate(self.monsters) if m.is_targetable]

    @property
    def incoming_damage(self) -> int:
        return sum(m.incoming_damage for m in self.monsters)

    @classmethod
    def from_dict(cls, d: Json) -> CombatState:
        return cls(
            player=Player.from_dict(d.get("player") or {}),
            monsters=tuple(Monster.from_dict(m) for m in _list(d, "monsters")),
            hand=_cards(d, "hand"),
            draw_pile=_cards(d, "draw_pile"),
            discard_pile=_cards(d, "discard_pile"),
            exhaust_pile=_cards(d, "exhaust_pile"),
            limbo=_cards(d, "limbo"),
            turn=d.get("turn", 0),
            cards_discarded_this_turn=d.get("cards_discarded_this_turn", 0),
            times_damaged=d.get("times_damaged", 0),
        )


@dataclass(frozen=True)
class MapNode:
    x: int
    y: int
    symbol: str  # M monster, E elite, R rest, $ shop, ? event, T treasure
    children: tuple[tuple[int, int], ...] = ()
    parents: tuple[tuple[int, int], ...] = ()

    @classmethod
    def from_dict(cls, d: Json) -> MapNode:
        return cls(
            x=d.get("x", 0),
            y=d.get("y", 0),
            symbol=d.get("symbol", ""),
            children=tuple((c.get("x", 0), c.get("y", 0)) for c in _list(d, "children")),
            parents=tuple((p.get("x", 0), p.get("y", 0)) for p in _list(d, "parents")),
        )


# --- Screens ---------------------------------------------------------------


@dataclass(frozen=True)
class EventOption:
    choice_index: int
    label: str
    text: str = ""
    disabled: bool = False


@dataclass(frozen=True)
class EventScreen:
    event_id: str
    event_name: str
    body_text: str
    options: tuple[EventOption, ...]

    @classmethod
    def from_dict(cls, d: Json) -> EventScreen:
        return cls(
            event_id=d.get("event_id", ""),
            event_name=d.get("event_name", ""),
            body_text=d.get("body_text", ""),
            options=tuple(
                EventOption(
                    choice_index=o.get("choice_index", 0),
                    label=o.get("label", ""),
                    text=o.get("text", ""),
                    disabled=o.get("disabled", False),
                )
                for o in _list(d, "options")
            ),
        )


@dataclass(frozen=True)
class MapScreen:
    current_node: MapNode | None
    next_nodes: tuple[MapNode, ...]
    boss_available: bool = False
    first_node_chosen: bool = False

    @classmethod
    def from_dict(cls, d: Json) -> MapScreen:
        current = d.get("current_node")
        return cls(
            current_node=MapNode.from_dict(current) if current else None,
            next_nodes=tuple(MapNode.from_dict(n) for n in _list(d, "next_nodes")),
            boss_available=d.get("boss_available", False),
            first_node_chosen=d.get("first_node_chosen", False),
        )


@dataclass(frozen=True)
class CardRewardScreen:
    cards: tuple[Card, ...]
    skip_available: bool = False
    bowl_available: bool = False

    @classmethod
    def from_dict(cls, d: Json) -> CardRewardScreen:
        return cls(
            cards=_cards(d, "cards"),
            skip_available=d.get("skip_available", False),
            bowl_available=d.get("bowl_available", False),
        )


@dataclass(frozen=True)
class Reward:
    reward_type: str  # GOLD, POTION, RELIC, CARD, ...
    gold: int = 0
    potion: Potion | None = None
    relic: Relic | None = None


@dataclass(frozen=True)
class CombatRewardScreen:
    rewards: tuple[Reward, ...]

    @classmethod
    def from_dict(cls, d: Json) -> CombatRewardScreen:
        rewards = []
        for r in _list(d, "rewards"):
            potion, relic = r.get("potion"), r.get("relic")
            rewards.append(
                Reward(
                    reward_type=r.get("reward_type", ""),
                    gold=r.get("gold", 0),
                    potion=Potion.from_dict(potion) if potion else None,
                    relic=Relic.from_dict(relic) if relic else None,
                )
            )
        return cls(rewards=tuple(rewards))


@dataclass(frozen=True)
class RestScreen:
    rest_options: tuple[str, ...]  # e.g. "rest", "smith"
    has_rested: bool = False

    @classmethod
    def from_dict(cls, d: Json) -> RestScreen:
        return cls(
            rest_options=tuple(_list(d, "rest_options")),
            has_rested=d.get("has_rested", False),
        )


@dataclass(frozen=True)
class GridScreen:
    """A grid of cards to pick from: removing, upgrading, transforming, ..."""

    cards: tuple[Card, ...]
    selected_cards: tuple[Card, ...] = ()
    num_cards: int = 1
    any_number: bool = False
    confirm_up: bool = False
    for_upgrade: bool = False
    for_transform: bool = False
    for_purge: bool = False

    @classmethod
    def from_dict(cls, d: Json) -> GridScreen:
        return cls(
            cards=_cards(d, "cards"),
            selected_cards=_cards(d, "selected_cards"),
            num_cards=d.get("num_cards", 1),
            any_number=d.get("any_number", False),
            confirm_up=d.get("confirm_up", False),
            for_upgrade=d.get("for_upgrade", False),
            for_transform=d.get("for_transform", False),
            for_purge=d.get("for_purge", False),
        )


@dataclass(frozen=True)
class ChestScreen:
    chest_type: str
    chest_open: bool = False

    @classmethod
    def from_dict(cls, d: Json) -> ChestScreen:
        return cls(chest_type=d.get("chest_type", ""), chest_open=d.get("chest_open", False))


@dataclass(frozen=True)
class GameOverScreen:
    score: int
    victory: bool

    @classmethod
    def from_dict(cls, d: Json) -> GameOverScreen:
        return cls(score=d.get("score", 0), victory=d.get("victory", False))


@dataclass(frozen=True)
class NoScreen:
    """No screen is up, e.g. during a fight."""


@dataclass(frozen=True)
class UnknownScreen:
    """A screen without a typed model yet."""

    screen_type: str
    raw: Json = field(default_factory=dict)


Screen = (
    NoScreen
    | EventScreen
    | MapScreen
    | CardRewardScreen
    | CombatRewardScreen
    | RestScreen
    | GridScreen
    | ChestScreen
    | GameOverScreen
    | UnknownScreen
)

_SCREEN_PARSERS = {
    "NONE": lambda _: NoScreen(),
    "EVENT": EventScreen.from_dict,
    "MAP": MapScreen.from_dict,
    "CARD_REWARD": CardRewardScreen.from_dict,
    "COMBAT_REWARD": CombatRewardScreen.from_dict,
    "REST": RestScreen.from_dict,
    "GRID": GridScreen.from_dict,
    "CHEST": ChestScreen.from_dict,
    "GAME_OVER": GameOverScreen.from_dict,
}


def parse_screen(screen_type: str, data: Json) -> Screen:
    parser = _SCREEN_PARSERS.get(screen_type)
    return parser(data) if parser else UnknownScreen(screen_type, data)


# --- Game state ------------------------------------------------------------


@dataclass(frozen=True)
class GameState:
    screen_type: str  # NONE in combat, else EVENT, MAP, CARD_REWARD, ...
    screen: Screen
    choice_list: tuple[str, ...]
    character: str  # IRONCLAD, THE_SILENT, DEFECT, WATCHER
    ascension_level: int
    seed: int
    act: int
    floor: int
    act_boss: str
    current_hp: int
    max_hp: int
    gold: int
    deck: tuple[Card, ...]
    relics: tuple[Relic, ...]
    potions: tuple[Potion, ...]
    map: tuple[MapNode, ...]
    room_phase: str = ""  # COMBAT, EVENT, COMPLETE, INCOMPLETE
    room_type: str = ""  # e.g. MonsterRoom, NeowRoom
    action_phase: str = ""  # WAITING_ON_USER or EXECUTING_ACTIONS
    current_action: str | None = None
    # The screen overlaying the room, e.g. SETTINGS when the pause menu is open.
    screen_name: str = ""
    is_screen_up: bool = False
    combat: CombatState | None = None

    @property
    def is_paused(self) -> bool:
        """The settings menu is open, which pauses the game."""
        return self.is_screen_up and self.screen_name == "SETTINGS"

    @classmethod
    def from_dict(cls, d: Json) -> GameState:
        screen_type = d.get("screen_type", "NONE")
        combat = d.get("combat_state")
        return cls(
            screen_type=screen_type,
            screen=parse_screen(screen_type, d.get("screen_state") or {}),
            choice_list=tuple(_list(d, "choice_list")),
            character=d.get("class", ""),
            ascension_level=d.get("ascension_level", 0),
            seed=d.get("seed", 0),
            act=d.get("act", 0),
            floor=d.get("floor", 0),
            act_boss=d.get("act_boss", ""),
            current_hp=d.get("current_hp", 0),
            max_hp=d.get("max_hp", 0),
            gold=d.get("gold", 0),
            deck=_cards(d, "deck"),
            relics=tuple(Relic.from_dict(r) for r in _list(d, "relics")),
            potions=tuple(Potion.from_dict(p) for p in _list(d, "potions")),
            map=tuple(MapNode.from_dict(n) for n in _list(d, "map")),
            room_phase=d.get("room_phase", ""),
            room_type=d.get("room_type", ""),
            action_phase=d.get("action_phase", ""),
            current_action=d.get("current_action"),
            screen_name=d.get("screen_name", ""),
            is_screen_up=d.get("is_screen_up", False),
            combat=CombatState.from_dict(combat) if combat else None,
        )
