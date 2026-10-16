"""What Ironclad's cards do, since CommunicationMod only sends a card's id and cost.

Numbers are (base, upgraded) values from the game's card data. Cards not listed
are treated as having no known damage or block: the combat rules still play
them, just after the cards they understand.
"""

from __future__ import annotations

from dataclasses import dataclass

from .state import Card

Pair = tuple[int, int]


@dataclass(frozen=True)
class CardData:
    damage: Pair = (0, 0)  # per hit
    hits: Pair = (1, 1)
    block: Pair = (0, 0)
    aoe: bool = False  # hits every monster
    strength_multiplier: Pair = (1, 1)  # Heavy Blade
    hp_cost: int = 0  # HP lost when played

    def value(self, pair: Pair, card: Card) -> int:
        return pair[1] if card.upgrades else pair[0]


CARDS: dict[str, CardData] = {
    # Starter
    "Strike_R": CardData(damage=(6, 9)),
    "Defend_R": CardData(block=(5, 8)),
    "Bash": CardData(damage=(8, 10)),
    # Common
    "Anger": CardData(damage=(6, 8)),
    "Armaments": CardData(block=(5, 5)),
    "Clash": CardData(damage=(14, 18)),
    "Cleave": CardData(damage=(8, 11), aoe=True),
    "Clothesline": CardData(damage=(12, 14)),
    "Headbutt": CardData(damage=(9, 12)),
    "Heavy Blade": CardData(damage=(14, 14), strength_multiplier=(3, 5)),
    "Iron Wave": CardData(damage=(5, 7), block=(5, 7)),
    "Perfected Strike": CardData(damage=(6, 6)),  # plus a bonus per Strike, see damage()
    "Pommel Strike": CardData(damage=(9, 10)),
    "Shrug It Off": CardData(block=(8, 11)),
    "Sword Boomerang": CardData(damage=(3, 3), hits=(3, 4)),
    "Thunderclap": CardData(damage=(4, 7), aoe=True),
    "True Grit": CardData(block=(7, 9)),
    "Twin Strike": CardData(damage=(5, 7), hits=(2, 2)),
    "Wild Strike": CardData(damage=(12, 17)),
    # Uncommon
    "Blood for Blood": CardData(damage=(18, 22)),
    "Bloodletting": CardData(hp_cost=3),
    "Carnage": CardData(damage=(20, 28)),
    "Dropkick": CardData(damage=(5, 8)),
    "Flame Barrier": CardData(block=(12, 16)),
    "Ghostly Armor": CardData(block=(10, 13)),
    "Hemokinesis": CardData(damage=(15, 20), hp_cost=2),
    "Power Through": CardData(block=(15, 20)),
    "Pummel": CardData(damage=(2, 2), hits=(4, 5)),
    "Rampage": CardData(damage=(8, 8)),
    "Reckless Charge": CardData(damage=(7, 10)),
    "Searing Blow": CardData(damage=(12, 16)),
    "Sentinel": CardData(block=(5, 8)),
    "Sever Soul": CardData(damage=(16, 22)),
    "Uppercut": CardData(damage=(13, 13)),
    "Whirlwind": CardData(damage=(5, 8), aoe=True),  # hits once per energy
    # Rare
    "Bludgeon": CardData(damage=(32, 42)),
    "Feed": CardData(damage=(10, 12)),
    "Immolate": CardData(damage=(21, 28), aoe=True),
    "Impervious": CardData(block=(30, 40)),
    "Offering": CardData(hp_cost=6),
    "Reaper": CardData(damage=(4, 5), aoe=True),
}

UNKNOWN = CardData()

# How much we want each card as a reward, 0-100. Tuned for a simple bot that
# can't plan combos: reliable damage, block and card draw beat build-arounds.
CARD_REWARD_SCORES: dict[str, int] = {
    "Offering": 80,
    "Immolate": 80,
    "Shrug It Off": 75,
    "Uppercut": 75,
    "Feed": 75,
    "Impervious": 75,
    "Whirlwind": 70,
    "Pommel Strike": 70,
    "Carnage": 70,
    "Inflame": 70,
    "Flame Barrier": 70,
    "Shockwave": 70,
    "Bludgeon": 70,
    "Hemokinesis": 65,
    "Disarm": 65,
    "Battle Trance": 65,
    "Reaper": 65,
    "Thunderclap": 60,
    "Cleave": 60,
    "Twin Strike": 60,
    "Ghostly Armor": 60,
    "Metallicize": 60,
    "Fiend Fire": 60,
    "Headbutt": 55,
    "Iron Wave": 55,
    "Clothesline": 55,
    "Sword Boomerang": 55,
    "True Grit": 55,
    "Feel No Pain": 55,
    "Pummel": 55,
    "Blood for Blood": 55,
    "Power Through": 55,
    "Anger": 50,
    "Armaments": 50,
    "Perfected Strike": 50,
    "Dropkick": 50,
    "Spot Weakness": 50,
    "Burning Pact": 50,
    "Sever Soul": 50,
    "Corruption": 50,
    "Wild Strike": 45,
    "Heavy Blade": 45,
    "Rampage": 45,
    "Seeing Red": 45,
    "Sentinel": 45,
    "Second Wind": 45,
    "Dark Embrace": 45,
    "Combust": 45,
    "Infernal Blade": 45,
    "Juggernaut": 45,
    "Double Tap": 45,
    "Body Slam": 40,
    "Searing Blow": 40,
    "Intimidate": 40,
    "Bloodletting": 40,
    "Rage": 40,
    "Reckless Charge": 40,
    "Barricade": 40,
    "Berserk": 40,
}
DEFAULT_REWARD_SCORE = 30


def data(card: Card) -> CardData:
    return CARDS.get(card.id, UNKNOWN)


def reward_score(card: Card) -> int:
    return CARD_REWARD_SCORES.get(card.id, DEFAULT_REWARD_SCORE)


def is_strike(card: Card) -> bool:
    return "Strike" in card.name
