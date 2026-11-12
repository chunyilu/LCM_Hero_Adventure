"""
Model Layer: Arithmetic State Engine, Adaptive Edge AI, and JRPG Game State.

Implements:
- LCM calculation & problem generation across 4 pedagogical zones:
  1. Whispering Woods (Prime Pair / Coprimes, e.g. [3, 5])
  2. Shadow Caves (Overlapping Factors, e.g. [4, 6])
  3. Misty Barrens (Contained Multiples, e.g. [3, 6])
  4. Demon Castle (Three-Number Rush, e.g. [3, 4, 6])
- Step-by-step Short Division (短除法) and Multiples-Listing explanation generator
- Adaptive Edge AI offline performance model tracking response latency & accuracy
- Hero progression, Equipment Shop (Multiplier Sword, Prime Number Shield),
  Princess Rescue Progress, Stage-End Cutscenes, and Leaderboard.
"""

from __future__ import annotations

import enum
import json
import math
import os
import random
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple


class ProblemType(enum.Enum):
    """The 4 core mathematical concepts corresponding to the 4 game zones."""
    PRIME_PAIR = "prime_pair"                 # Zone 1: Coprime numbers (LCM = a * b)
    OVERLAPPING_FACTORS = "overlapping"       # Zone 2: Shared factors > 1, neither divides the other
    CONTAINED_MULTIPLES = "contained"         # Zone 3: Larger is already a multiple of smaller
    THREE_NUMBER_RUSH = "three_number_rush"   # Zone 4: 3 distinct numbers


class GameScene(enum.Enum):
    """High-level game state scenes."""
    TITLE = "title"
    EXPLORE = "explore"
    COMBAT = "combat"
    FAIRY_TUTORIAL = "fairy_tutorial"
    SHOP = "shop"
    CUTSCENE = "cutscene"
    AI_DASHBOARD = "ai_dashboard"
    LEADERBOARD = "leaderboard"
    VICTORY = "victory"
    GAME_OVER = "game_over"


class TileType(enum.Enum):
    """Map tile types for the 2D exploration view."""
    FLOOR = 0
    WALL = 1
    SHOP = 2
    PORTAL = 3
    DECOR = 4
    SIGN = 5


@dataclass
class ShortDivisionStep:
    """Represents one step in the Short Division (短除法) algorithm."""
    divisor: int
    input_numbers: Tuple[int, ...]
    output_numbers: Tuple[int, ...]
    explanation: str


@dataclass
class LCMProblem:
    """Represents a monster's Mathematical Shield problem and educational breakdown."""
    numbers: Tuple[int, ...]
    problem_type: ProblemType
    lcm: int
    spell_cards: List[int]
    short_division_steps: List[ShortDivisionStep]
    final_remainders: Tuple[int, ...]
    all_factors_for_lcm: List[int]
    multiples_dict: Dict[int, List[int]]
    concept_hint: str

    def evaluate_choice(self, chosen_value: int) -> Tuple[bool, str]:
        """
        Evaluate a player's selected spell card value.
        Returns (is_correct, educational_feedback).
        """
        if chosen_value == self.lcm:
            nums_str = ", ".join(str(n) for n in self.numbers)
            return True, f"Direct Hit! {self.lcm} is the Least Common Multiple of [{nums_str}]!"

        # Check if chosen_value is a common multiple, just not the LEAST
        is_common_multiple = all(chosen_value > 0 and chosen_value % n == 0 for n in self.numbers)
        nums_str = ", ".join(str(n) for n in self.numbers)
        if is_common_multiple and chosen_value > self.lcm:
            return (
                False,
                f"Shield Deflected! {chosen_value} IS a common multiple of [{nums_str}], "
                f"but NOT the LEAST (smallest) one!",
            )

        # Check which numbers do not divide chosen_value
        non_divisors = [n for n in self.numbers if chosen_value % n != 0]
        if non_divisors:
            nd_str = " and ".join(str(n) for n in non_divisors)
            return (
                False,
                f"Shield Deflected! {chosen_value} is not divisible by {nd_str}!",
            )

        return False, f"Shield Deflected! {chosen_value} is not the LCM of [{nums_str}]."


def compute_lcm(numbers: Tuple[int, ...]) -> int:
    """Compute the Least Common Multiple of a tuple of positive integers."""
    result = numbers[0]
    for n in numbers[1:]:
        result = (result * n) // math.gcd(result, n)
    return result


def build_short_division(numbers: Tuple[int, ...]) -> Tuple[List[ShortDivisionStep], Tuple[int, ...], List[int]]:
    """
    Build the Short Division (短除法) steps for 2 or 3 numbers.
    For 2 numbers: divide by smallest prime factor shared by both until coprime.
    For 3 numbers: divide by smallest prime factor shared by at least 2 numbers
    (first checking all 3, then any 2) as taught in standard elementary short division.
    """
    current = list(numbers)
    steps: List[ShortDivisionStep] = []
    divisors_used: List[int] = []
    primes = [2, 3, 5, 7, 11, 13, 17, 19]

    while True:
        found_divisor: Optional[int] = None
        # First look for a prime that divides ALL current numbers
        for p in primes:
            if all(x % p == 0 for x in current):
                found_divisor = p
                break
        # For 3 numbers, if no prime divides all 3, check if a prime divides at least 2 of them
        if found_divisor is None and len(current) >= 3:
            for p in primes:
                divisible_count = sum(1 for x in current if x % p == 0)
                if divisible_count >= 2:
                    found_divisor = p
                    break

        if found_divisor is None:
            break

        before = tuple(current)
        next_row = []
        divisible_nums = []
        for x in current:
            if x % found_divisor == 0:
                next_row.append(x // found_divisor)
                divisible_nums.append(str(x))
            else:
                next_row.append(x)
        after = tuple(next_row)
        steps.append(
            ShortDivisionStep(
                divisor=found_divisor,
                input_numbers=before,
                output_numbers=after,
                explanation=(
                    f"Divide {', '.join(divisible_nums)} by common prime factor {found_divisor} "
                    f"-> {list(after)}"
                ),
            )
        )
        divisors_used.append(found_divisor)
        current = next_row

    final_remainders = tuple(current)
    all_factors = divisors_used + [r for r in final_remainders if r != 1 or len(divisors_used) == 0]
    if not all_factors:
        all_factors = [1]
    return steps, final_remainders, all_factors


@dataclass
class TypePerformanceRecord:
    """Performance metrics for a single ProblemType in the Adaptive Edge AI model."""
    attempts: int = 0
    correct: int = 0
    incorrect: int = 0
    slow_responses: int = 0  # Responses taking > 15.0 seconds
    total_latency_sec: float = 0.0
    recent_latencies: List[float] = field(default_factory=list)
    spawn_weight: float = 1.0

    @property
    def avg_latency(self) -> float:
        if not self.recent_latencies:
            return 0.0
        return sum(self.recent_latencies) / len(self.recent_latencies)

    @property
    def accuracy(self) -> float:
        if self.attempts == 0:
            return 1.0
        return self.correct / self.attempts


class AdaptiveEdgeAI:
    """
    Offline Performance Model (Adaptive Edge AI Integration).

    Monitors:
    - Response latency per problem type & specific shield sets (threshold: 15.0s)
    - Accuracy / mistake streaks per problem type

    Targeted Spawning:
    - If a player struggles with a problem type (e.g. taking > 15 seconds to solve [6, 8]
      or making errors on Overlapping Factors), increases the spawn weight of that
      problem type and similar shield sets until proficiency improves.
    """

    SLOW_THRESHOLD_SECONDS: float = 15.0

    def __init__(self) -> None:
        self.records: Dict[ProblemType, TypePerformanceRecord] = {
            pt: TypePerformanceRecord() for pt in ProblemType
        }
        # Track specific shield number tuples that caused struggle (latency > 15s or wrong answer)
        self.struggle_shields: Dict[Tuple[int, ...], float] = {}
        self.event_log: List[str] = [
            "Edge AI initialized: monitoring latency & shield mastery."
        ]

    def record_attempt(
        self,
        problem_type: ProblemType,
        shield_numbers: Tuple[int, ...],
        is_correct: bool,
        latency_sec: float,
    ) -> str:
        """
        Update offline performance metrics and recalculate dynamic spawn weights.
        Returns a status note describing any AI adaptation triggered.
        """
        rec = self.records[problem_type]
        rec.attempts += 1
        rec.total_latency_sec += max(0.1, latency_sec)
        rec.recent_latencies.append(max(0.1, latency_sec))
        if len(rec.recent_latencies) > 8:
            rec.recent_latencies.pop(0)

        adaptation_note = ""
        is_slow = latency_sec > self.SLOW_THRESHOLD_SECONDS

        if is_correct:
            rec.correct += 1
            if is_slow:
                rec.slow_responses += 1
                rec.spawn_weight = min(4.0, rec.spawn_weight + 0.75)
                self.struggle_shields[shield_numbers] = min(
                    3.5, self.struggle_shields.get(shield_numbers, 1.0) + 1.0
                )
                adaptation_note = (
                    f"AI Notice: Solved {list(shield_numbers)} in {latency_sec:.1f}s (>15s). "
                    f"Boosting '{problem_type.value}' practice rate (weight {rec.spawn_weight:.2f}x)."
                )
            else:
                # Fast & accurate -> gradually decay extra weight toward baseline 1.0
                if rec.spawn_weight > 1.0:
                    rec.spawn_weight = max(1.0, rec.spawn_weight - 0.35)
                if shield_numbers in self.struggle_shields:
                    self.struggle_shields[shield_numbers] -= 0.6
                    if self.struggle_shields[shield_numbers] <= 1.0:
                        del self.struggle_shields[shield_numbers]
                adaptation_note = (
                    f"AI Notice: Fast mastery on {list(shield_numbers)} ({latency_sec:.1f}s)! "
                    f"Proficiency rating updated."
                )
        else:
            rec.incorrect += 1
            if is_slow:
                rec.slow_responses += 1
            rec.spawn_weight = min(4.5, rec.spawn_weight + 1.1)
            self.struggle_shields[shield_numbers] = min(
                4.0, self.struggle_shields.get(shield_numbers, 1.0) + 1.25
            )
            adaptation_note = (
                f"AI Notice: Struggle detected on {list(shield_numbers)} ({problem_type.value}). "
                f"Increasing targeted spawn weight to {rec.spawn_weight:.2f}x."
            )

        self.event_log.insert(0, adaptation_note)
        if len(self.event_log) > 12:
            self.event_log.pop()
        return adaptation_note

    def choose_problem_type(self, zone_index: int, rng: Optional[random.Random] = None) -> ProblemType:
        """
        Select the problem type for a new monster encounter.
        While each zone introduces a primary concept, the Adaptive Edge AI can inject
        targeted review monsters from struggling categories if their spawn_weight > 1.25.
        """
        rand = rng or random
        zone_default_map = {
            1: ProblemType.PRIME_PAIR,
            2: ProblemType.OVERLAPPING_FACTORS,
            3: ProblemType.CONTAINED_MULTIPLES,
            4: ProblemType.THREE_NUMBER_RUSH,
        }
        primary_type = zone_default_map.get(zone_index, ProblemType.PRIME_PAIR)

        # Candidate types: unlocked up to current zone + any struggling type with weight > 1.25
        unlocked_types = [
            zone_default_map[z] for z in range(1, min(4, max(1, zone_index)) + 1)
        ]
        for pt, rec in self.records.items():
            if rec.spawn_weight > 1.25 and pt not in unlocked_types:
                unlocked_types.append(pt)

        weights: List[float] = []
        for pt in unlocked_types:
            base_w = 2.2 if pt == primary_type else 0.6
            ai_multiplier = self.records[pt].spawn_weight
            # If a category has elevated AI spawn weight, amplify it strongly
            if ai_multiplier > 1.2:
                weights.append(base_w * (ai_multiplier ** 1.5))
            else:
                weights.append(base_w)

        return rand.choices(unlocked_types, weights=weights, k=1)[0]

    def needs_extra_reinforcement(self, problem_type: ProblemType) -> bool:
        """Return True if the AI model currently flags this problem type as needing extra practice."""
        return self.records[problem_type].spawn_weight >= 1.5


class ArithmeticEngine:
    """
    Decoupled Arithmetic State Engine.
    Generates LCM problems, distractors, Short Division steps, and Multiples tables.
    """

    # Curated problem pools per mathematical concept
    POOLS: Dict[ProblemType, List[Tuple[int, ...]]] = {
        ProblemType.PRIME_PAIR: [
            (2, 3),
            (2, 5),
            (3, 5),
            (2, 7),
            (3, 7),
            (4, 5),
            (3, 8),
            (4, 9),
            (5, 6),
            (5, 7),
            (5, 8),
            (7, 8),
        ],
        ProblemType.OVERLAPPING_FACTORS: [
            (4, 6),
            (6, 8),
            (6, 9),
            (6, 10),
            (8, 10),
            (8, 12),
            (9, 12),
            (10, 15),
            (12, 15),
            (12, 16),
            (14, 21),
        ],
        ProblemType.CONTAINED_MULTIPLES: [
            (2, 4),
            (2, 6),
            (3, 6),
            (3, 9),
            (4, 8),
            (4, 12),
            (5, 10),
            (5, 15),
            (6, 12),
            (6, 18),
            (7, 14),
            (8, 16),
        ],
        ProblemType.THREE_NUMBER_RUSH: [
            (2, 3, 4),
            (3, 4, 6),
            (2, 3, 6),
            (2, 4, 6),
            (2, 5, 10),
            (3, 5, 15),
            (2, 3, 5),
            (3, 6, 9),
            (4, 6, 8),
            (3, 4, 8),
            (2, 6, 9),
            (4, 6, 12),
        ],
    }

    CONCEPT_HINTS: Dict[ProblemType, str] = {
        ProblemType.PRIME_PAIR: (
            "Prime / Coprime Pair: These numbers share NO common factor except 1! "
            "Multiply them directly: a x b = LCM."
        ),
        ProblemType.OVERLAPPING_FACTORS: (
            "Overlapping Factors: These numbers share a common factor! "
            "Use Short Division so you do not multiply the shared factor twice."
        ),
        ProblemType.CONTAINED_MULTIPLES: (
            "Contained Multiples: Look closely! Is the larger number already a multiple "
            "of the smaller number? If so, the larger number IS the LCM!"
        ),
        ProblemType.THREE_NUMBER_RUSH: (
            "Three-Number Rush: Find the smallest number divisible by ALL THREE shield numbers! "
            "Use Short Division step by step."
        ),
    }

    def __init__(self, ai_model: Optional[AdaptiveEdgeAI] = None, seed: Optional[int] = None) -> None:
        self.ai_model = ai_model or AdaptiveEdgeAI()
        self.rng = random.Random(seed)

    def generate_problem(
        self,
        problem_type: Optional[ProblemType] = None,
        zone_index: int = 1,
        specific_numbers: Optional[Tuple[int, ...]] = None,
    ) -> LCMProblem:
        """Generate a complete LCMProblem with smart educational distractors."""
        if specific_numbers is not None:
            numbers = specific_numbers
            if problem_type is None:
                problem_type = self._classify_numbers(numbers)
        else:
            if problem_type is None:
                problem_type = self.ai_model.choose_problem_type(zone_index, self.rng)
            pool = self.POOLS[problem_type]
            # Weight specific shields higher if player struggled with them or similar numbers
            weights: List[float] = []
            for candidate in pool:
                w = self.ai_model.struggle_shields.get(candidate, 1.0)
                # Also boost similar shield sets sharing numbers with a struggled shield
                for struggled_nums, s_weight in self.ai_model.struggle_shields.items():
                    if candidate != struggled_nums and set(candidate) & set(struggled_nums):
                        w += (s_weight - 1.0) * 0.5
                weights.append(w)
            numbers = self.rng.choices(pool, weights=weights, k=1)[0]

        lcm_val = compute_lcm(numbers)
        spell_cards = self._generate_spell_cards(numbers, lcm_val)
        steps, remainders, all_factors = build_short_division(numbers)

        # Build multiples list up to at least the LCM + 1 step
        multiples_dict: Dict[int, List[int]] = {}
        for n in numbers:
            count = max(5, min(10, (lcm_val // n) + 2))
            multiples_dict[n] = [n * i for i in range(1, count + 1)]

        return LCMProblem(
            numbers=numbers,
            problem_type=problem_type,
            lcm=lcm_val,
            spell_cards=spell_cards,
            short_division_steps=steps,
            final_remainders=remainders,
            all_factors_for_lcm=all_factors,
            multiples_dict=multiples_dict,
            concept_hint=self.CONCEPT_HINTS[problem_type],
        )

    @staticmethod
    def _classify_numbers(numbers: Tuple[int, ...]) -> ProblemType:
        if len(numbers) >= 3:
            return ProblemType.THREE_NUMBER_RUSH
        a, b = min(numbers), max(numbers)
        if b % a == 0:
            return ProblemType.CONTAINED_MULTIPLES
        if math.gcd(a, b) == 1:
            return ProblemType.PRIME_PAIR
        return ProblemType.OVERLAPPING_FACTORS

    def _generate_spell_cards(self, numbers: Tuple[int, ...], lcm_val: int) -> List[int]:
        """
        Generate 4 multiple-choice spell cards containing:
        - The exact LCM (correct answer)
        - A common multiple trap (e.g., 2 * LCM or 3 * LCM, or product of numbers when GCD > 1)
        - An addition or partial multiple trap (e.g., sum of numbers, or multiple of only one number)
        - Another plausible number
        """
        candidates: List[int] = []
        raw_product = 1
        for n in numbers:
            raw_product *= n

        # 1. Non-least common multiple traps (crucial per Game Concept Doc: e.g. [4,6] -> 24, 36)
        if raw_product > lcm_val:
            candidates.append(raw_product)
        candidates.append(lcm_val * 2)
        candidates.append(lcm_val * 3)

        # 2. Multiple of one number but not the other (e.g. for [4, 6] -> 10, 8, 16, 18)
        max_n = max(numbers)
        min_n = min(numbers)
        candidates.extend([
            sum(numbers),
            max_n * 2,
            min_n * 3,
            lcm_val - min_n if lcm_val > min_n else lcm_val + min_n,
            lcm_val + 2,
            lcm_val - 2 if lcm_val > 4 else lcm_val + 4,
        ])

        # Filter unique positive integers != lcm_val
        distractors: List[int] = []
        for c in candidates:
            if c > 0 and c != lcm_val and c not in distractors:
                distractors.append(c)

        # Ensure at least one common multiple > lcm_val is included as a pedagogical distractor
        common_mult_distractor = raw_product if raw_product > lcm_val else lcm_val * 2
        chosen_distractors = [common_mult_distractor]

        other_pool = [d for d in distractors if d != common_mult_distractor]
        self.rng.shuffle(other_pool)
        for d in other_pool:
            if len(chosen_distractors) < 3:
                chosen_distractors.append(d)

        fallback = lcm_val + 1
        while len(chosen_distractors) < 3:
            if fallback != lcm_val and fallback not in chosen_distractors:
                chosen_distractors.append(fallback)
            fallback += 1

        cards = [lcm_val] + chosen_distractors[:3]
        return sorted(cards)


@dataclass
class ShopItem:
    """Equipment or consumable item in the Village Shop."""
    id: str
    name: str
    category: str  # "sword", "shield", "consumable", "charm"
    cost: int
    description: str
    tier_level: int = 1
    hp_bonus: int = 0
    heal_amount: int = 0
    star_multiplier: float = 1.0
    gold_bonus: int = 0
    purchased: bool = False


@dataclass
class MonsterEntity:
    """A monster on the exploration map and in combat."""
    id: int
    name: str
    species: str  # "slime", "bat", "golem", "knight", "demon_king"
    grid_x: int
    grid_y: int
    zone_index: int
    is_boss: bool = False
    problem: Optional[LCMProblem] = None
    defeated: bool = False
    attack_damage: int = 1
    gold_reward: int = 25
    star_reward: int = 100


@dataclass
class CutsceneData:
    """Data for the Stage-End Princess Reward Cutscene."""
    zone_completed: int
    title: str
    princess_dialogue: List[str]
    gift_item_name: str
    new_hero_tier_name: str
    new_tier_index: int
    bonus_gold: int
    bonus_stars: int


@dataclass
class LeaderboardEntry:
    """Hall of Fame leaderboard entry."""
    name: str
    star_points: int
    tier_name: str
    zones_cleared: int
    is_player: bool = False


class HeroModel:
    """Stores the Hero's stats, equipment, and narrative tier progression."""

    TIER_NAMES = {
        1: "Apprentice Numerist",
        2: "Prime Knight",
        3: "Factor Paladin",
        4: "Holy Arithmancer",
        5: "Grand Champion of LCM",
    }

    def __init__(self) -> None:
        self.max_hp: int = 5
        self.hp: int = 5
        self.star_points: int = 0
        self.gold: int = 40
        self.tier: int = 1
        self.grid_x: int = 2
        self.grid_y: int = 5
        self.facing: str = "right"  # "left", "right", "up", "down"

        # Equipment tiers & visuals
        self.sword_name: str = "Wooden Training Sword"
        self.sword_level: int = 0  # 0: Wooden, 1: Multiplier Sword, 2: Twin Multiplier Blade, 3: Legendary Holy Sword
        self.shield_name: str = "Buckler of Ones"
        self.shield_level: int = 0  # 0: Basic, 1: Prime Number Shield, 2: Aegis of Eratosthenes
        self.has_fairy_charm: bool = False

        # Performance stats
        self.monsters_defeated: int = 0
        self.correct_answers: int = 0
        self.wrong_answers: int = 0
        self.streak: int = 0

    @property
    def tier_title(self) -> str:
        return self.TIER_NAMES.get(self.tier, "Hero")

    @property
    def star_multiplier(self) -> float:
        base = 1.0 + (0.25 * self.sword_level) + (0.1 * (self.tier - 1))
        return round(base, 2)


class ZoneConfig:
    """Metadata and layout generator for each of the 4 Level Zones."""

    ZONE_INFO = {
        1: {
            "name": "1. Whispering Woods",
            "subtitle": "Prime Pair Sanctuary",
            "shield_type_label": "Prime Pair (e.g., [3, 5])",
            "concept_desc": "Coprime numbers where the LCM is simply the product (3 x 5 = 15).",
            "milestone": "Hero leaves the home village; defeats simple slimes.",
            "problem_type": ProblemType.PRIME_PAIR,
            "monster_species": [("Emerald Slime", "slime"), ("Forest Slime", "slime"), ("King Slime", "slime")],
            "gift_name": "Starlight Crest of Primes",
            "unlocked_tier_name": "Prime Knight",
        },
        2: {
            "name": "2. Shadow Caves",
            "subtitle": "Caverns of Overlapping Factors",
            "shield_type_label": "Overlapping Factors (e.g., [4, 6])",
            "concept_desc": "Numbers sharing common factors; encourages list-matching or short division.",
            "milestone": "Explores the deep caverns; rescues trapped villagers.",
            "problem_type": ProblemType.OVERLAPPING_FACTORS,
            "monster_species": [("Echo Bat", "bat"), ("Crystal Golem", "golem"), ("Obsidian Warden", "golem")],
            "gift_name": "Lantern of Common Divisors",
            "unlocked_tier_name": "Factor Paladin",
        },
        3: {
            "name": "3. Misty Barrens",
            "subtitle": "Plains of Contained Multiples",
            "shield_type_label": "Contained Multiples (e.g., [3, 6])",
            "concept_desc": "The larger number is already a multiple of the smaller number (LCM = 6).",
            "milestone": "Earns the legendary Holy Sword; reaches the castle gates.",
            "problem_type": ProblemType.CONTAINED_MULTIPLES,
            "monster_species": [("Mist Phantom", "knight"), ("Mirage Lancer", "knight"), ("Gatekeeper General", "knight")],
            "gift_name": "The Legendary Holy Sword",
            "unlocked_tier_name": "Holy Arithmancer",
        },
        4: {
            "name": "4. Demon Castle",
            "subtitle": "Citadel of the Three-Number Rush",
            "shield_type_label": "Three-Number Rush (e.g., [3, 4, 6])",
            "concept_desc": "Compounding LCM steps across three distinct values (LCM = 12).",
            "milestone": "Final boss battle against the Demon King; saves the princess.",
            "problem_type": ProblemType.THREE_NUMBER_RUSH,
            "monster_species": [("Chaos Gargoyle", "golem"), ("Abyssal Executioner", "knight"), ("Demon King Malphas", "demon_king")],
            "gift_name": "Crown of Eternal Harmony",
            "unlocked_tier_name": "Grand Champion of LCM",
        },
    }


class GameStateModel:
    """
    Master Game State Model coordinating:
    - Hero, Shop, Zones (1..4), Exploration Grid, Monsters
    - Active Combat State, Consecutive Wrong Counter (for Tutorial Fairy)
    - Princess Rescue Progress Bar (0.0 to 1.0)
    - Adaptive Edge AI & Arithmetic Engine
    """

    MAP_COLS = 16
    MAP_ROWS = 10

    def __init__(self, seed: Optional[int] = None) -> None:
        self.ai = AdaptiveEdgeAI()
        self.engine = ArithmeticEngine(ai_model=self.ai, seed=seed)
        self.hero = HeroModel()
        self.scene: GameScene = GameScene.TITLE
        self.previous_scene: GameScene = GameScene.EXPLORE

        self.current_zone: int = 1
        self.max_zones: int = 4
        self.total_Required_battles_per_zone: int = 3
        self.zones_cleared: int = 0

        # Map & entities for current zone
        self.grid: List[List[TileType]] = []
        self.monsters: List[MonsterEntity] = []
        self.signpost_message: str = ""
        self.status_banner: str = "Welcome to LCM Hero Adventure! Use Arrow Keys/WASD to explore."

        # Combat state
        self.active_monster: Optional[MonsterEntity] = None
        self.consecutive_wrong_in_battle: int = 0
        self.total_consecutive_wrong: int = 0
        self.combat_feedback: str = ""
        self.combat_result_state: str = "ready"  # "ready", "hit_anim", "deflect_anim"
        self.selected_card_index: int = 0
        self.question_timer_sec: float = 0.0
        self.fairy_auto_triggered: bool = False
        self.fairy_step_index: int = 0
        self.fairy_tab: str = "short_division"  # "short_division" or "multiples"

        # Cutscene state
        self.active_cutscene: Optional[CutsceneData] = None

        # Shop catalog
        self.shop_items: List[ShopItem] = self._create_shop_items()

        # Leaderboard entries
        self.leaderboard: List[LeaderboardEntry] = [
            LeaderboardEntry("Princess Aria's Champion", 1850, "Grand Champion of LCM", 4),
            LeaderboardEntry("Sir Euclid", 1400, "Holy Arithmancer", 3),
            LeaderboardEntry("Lady Hypatia", 1050, "Factor Paladin", 2),
            LeaderboardEntry("Young Gauss", 650, "Prime Knight", 1),
            LeaderboardEntry("Novice Timmy", 250, "Apprentice Numerist", 1),
        ]

        # Build Zone 1
        self.load_zone(1)

    def _create_shop_items(self) -> List[ShopItem]:
        return [
            ShopItem(
                id="multiplier_sword_1",
                name="The Multiplier Sword",
                category="sword",
                cost=50,
                description="Changes weapon to a glowing golden blade! +25% Star Points & +10 Gold per win.",
                tier_level=1,
                star_multiplier=1.25,
                gold_bonus=10,
            ),
            ShopItem(
                id="prime_shield_1",
                name="The Prime Number Shield",
                category="shield",
                cost=60,
                description="Sacred emerald shield etched with primes! Increases Max HP by +3 and heals +3 HP.",
                tier_level=1,
                hp_bonus=3,
                heal_amount=3,
            ),
            ShopItem(
                id="multiplier_sword_2",
                name="Arcane Multiplier Greatsword",
                category="sword",
                cost=120,
                description="Upgrades weapon visuals with twin energy runes! +50% Star Points & +20 Gold per win.",
                tier_level=2,
                star_multiplier=1.50,
                gold_bonus=20,
            ),
            ShopItem(
                id="prime_shield_2",
                name="Aegis of Eratosthenes",
                category="shield",
                cost=130,
                description="Ultimate platinum prime barrier! Increases Max HP by +4 and fully restores HP.",
                tier_level=2,
                hp_bonus=4,
                heal_amount=99,
            ),
            ShopItem(
                id="fairy_charm",
                name="Fairy Tutor Lantern",
                category="charm",
                cost=75,
                description="Summons the Short Division Fairy hint after just 1 mistake (or press H anytime)!",
                tier_level=1,
            ),
            ShopItem(
                id="potion",
                name="Elixir of Numeracy",
                category="consumable",
                cost=25,
                description=" Drink a refreshing math potion to restore +3 HP immediately (repeatable).",
                tier_level=1,
                heal_amount=3,
            ),
        ]

    @property
    def princess_rescue_progress(self) -> float:
        """
        Compute overall narrative progress toward rescuing the Princess (0.0 to 1.0).
        Each of the 4 zones contributes 0.25 of total progress, subdivided by monsters defeated in the zone.
        """
        if self.scene == GameScene.VICTORY or self.zones_cleared >= self.max_zones:
            return 1.0
        base_progress = (self.current_zone - 1) / self.max_zones
        total_in_zone = max(1, len(self.monsters))
        defeated_in_zone = sum(1 for m in self.monsters if m.defeated)
        zone_fraction = (defeated_in_zone / total_in_zone) * (1.0 / self.max_zones)
        return min(1.0, round(base_progress + zone_fraction, 3))

    def load_zone(self, zone_index: int) -> None:
        """Initialize the 2D tile map and spawn monsters for the given zone (1..4)."""
        self.current_zone = zone_index
        info = ZoneConfig.ZONE_INFO[zone_index]

        # Build 16x10 map grid
        grid = [[TileType.FLOOR for _ in range(self.MAP_COLS)] for _ in range(self.MAP_ROWS)]
        for c in range(self.MAP_COLS):
            grid[0][c] = TileType.WALL
            grid[self.MAP_ROWS - 1][c] = TileType.WALL
        for r in range(self.MAP_ROWS):
            grid[r][0] = TileType.WALL
            grid[r][self.MAP_COLS - 1] = TileType.WALL

        # Decorative obstacles that leave clear paths
        decor_coords = [(2, 4), (2, 9), (7, 4), (7, 9), (4, 7), (5, 7)]
        for r, c in decor_coords:
            grid[r][c] = TileType.DECOR

        # Village Shop at top-left (row 2, col 2) and Signpost at (row 3, col 3)
        grid[2][2] = TileType.SHOP
        grid[3][3] = TileType.SIGN
        # Portal / Castle Gate at right side (row 5, col 14)
        grid[5][14] = TileType.PORTAL

        self.grid = grid
        self.hero.grid_x = 2
        self.hero.grid_y = 5
        self.hero.facing = "right"
        self.signpost_message = f"{info['name']}: {info['concept_desc']}"

        # Spawn 3 core monsters + 1 extra monster if Adaptive AI flags extra reinforcement
        species_list = info["monster_species"]
        positions = [(6, 3), (9, 6), (12, 5)]
        self.monsters = []
        for idx, (m_name, m_species) in enumerate(species_list):
            gx, gy = positions[idx]
            is_boss = idx == len(species_list) - 1
            prob = self.engine.generate_problem(
                problem_type=info["problem_type"] if is_boss else None,
                zone_index=zone_index,
            )
            self.monsters.append(
                MonsterEntity(
                    id=idx + 1,
                    name=m_name,
                    species=m_species,
                    grid_x=gx,
                    grid_y=gy,
                    zone_index=zone_index,
                    is_boss=is_boss,
                    problem=prob,
                    attack_damage=2 if (is_boss and zone_index == 4) else 1,
                    gold_reward=30 + zone_index * 15 + (25 if is_boss else 0),
                    star_reward=100 + zone_index * 25 + (50 if is_boss else 0),
                )
            )

        # Adaptive Edge AI targeted extra spawn if player struggled recently
        if any(self.ai.needs_extra_reinforcement(pt) for pt in ProblemType):
            struggling_pt = max(
                ProblemType, key=lambda pt: self.ai.records[pt].spawn_weight
            )
            extra_prob = self.engine.generate_problem(
                problem_type=struggling_pt, zone_index=zone_index
            )
            self.monsters.insert(
                1,
                MonsterEntity(
                    id=99,
                    name="Adaptive Mirage Slime",
                    species="slime",
                    grid_x=6,
                    grid_y=7,
                    zone_index=zone_index,
                    is_boss=False,
                    problem=extra_prob,
                    attack_damage=1,
                    gold_reward=35,
                    star_reward=125,
                ),
            )

        self.status_banner = (
            f"Entered {info['name']}! Defeat all monsters to unlock the portal."
        )

    def all_zone_monsters_defeated(self) -> bool:
        return all(m.defeated for m in self.monsters)

    def move_hero(self, dx: int, dy: int) -> str:
        """
        Move the hero on the exploration map.
        Checks collisions with walls, shops, signs, portals, and monsters.
        """
        if self.scene != GameScene.EXPLORE:
            return ""

        if dx < 0:
            self.hero.facing = "left"
        elif dx > 0:
            self.hero.facing = "right"
        elif dy < 0:
            self.hero.facing = "up"
        elif dy > 0:
            self.hero.facing = "down"

        nx = self.hero.grid_x + dx
        ny = self.hero.grid_y + dy

        if not (0 <= nx < self.MAP_COLS and 0 <= ny < self.MAP_ROWS):
            return "blocked"

        tile = self.grid[ny][nx]
        if tile in (TileType.WALL, TileType.DECOR):
            self.status_banner = "Path blocked by obstacle."
            return "blocked"

        # Check monster encounter at destination tile
        for monster in self.monsters:
            if not monster.defeated and monster.grid_x == nx and monster.grid_y == ny:
                self.hero.grid_x = nx
                self.hero.grid_y = ny
                self.start_combat(monster)
                return "combat"

        self.hero.grid_x = nx
        self.hero.grid_y = ny

        if tile == TileType.SHOP:
            self.scene = GameScene.SHOP
            self.status_banner = "Welcome to the Village Equipment Shop!"
            return "shop"

        if tile == TileType.SIGN:
            self.status_banner = f"Signpost: {self.signpost_message}"
            return "sign"

        if tile == TileType.PORTAL:
            if self.all_zone_monsters_defeated():
                self.trigger_stage_end_cutscene()
                return "cutscene"
            remaining = sum(1 for m in self.monsters if not m.defeated)
            self.status_banner = (
                f"The Castle Gate is sealed! Defeat {remaining} more monster(s) in this zone first."
            )
            return "portal_locked"

        return "moved"

    def start_combat(self, monster: MonsterEntity) -> None:
        """Enter turn-based LCM Shield combat with the encountered monster."""
        self.active_monster = monster
        if self.active_monster.problem is None:
            info = ZoneConfig.ZONE_INFO[self.current_zone]
            self.active_monster.problem = self.engine.generate_problem(
                problem_type=info["problem_type"], zone_index=self.current_zone
            )
        self.scene = GameScene.COMBAT
        self.consecutive_wrong_in_battle = 0
        self.selected_card_index = 0
        self.question_timer_sec = 0.0
        self.combat_result_state = "ready"
        nums_str = ", ".join(str(n) for n in self.active_monster.problem.numbers)
        self.combat_feedback = (
            f"A wild {monster.name} appears with Mathematical Shield [{nums_str}]! "
            f"Cast the Least Common Multiple (LCM) spell to break it!"
        )

    def submit_spell_card(self, card_index: int) -> Tuple[bool, str]:
        """
        Player casts one of the 4 multiple-choice spell cards in combat.
        Returns (is_correct, outcome_type) where outcome_type is one of:
        'monster_defeated', 'fairy_triggered', 'game_over', 'shield_deflected'.
        """
        if self.active_monster is None or self.active_monster.problem is None:
            return False, "none"

        problem = self.active_monster.problem
        if not (0 <= card_index < len(problem.spell_cards)):
            return False, "none"

        chosen_val = problem.spell_cards[card_index]
        is_correct, feedback = problem.evaluate_choice(chosen_val)
        latency = max(0.2, self.question_timer_sec)

        # Record in Adaptive Edge AI offline performance model
        ai_note = self.ai.record_attempt(
            problem_type=problem.problem_type,
            shield_numbers=problem.numbers,
            is_correct=is_correct,
            latency_sec=latency,
        )

        if is_correct:
            self.combat_result_state = "hit_anim"
            self.consecutive_wrong_in_battle = 0
            self.total_consecutive_wrong = 0
            self.hero.correct_answers += 1
            self.hero.streak += 1
            self.hero.monsters_defeated += 1

            # Calculate rewards with sword bonuses
            earned_stars = int(
                round(self.active_monster.star_reward * self.hero.star_multiplier)
            )
            sword_gold_bonus = self.hero.sword_level * 10
            earned_gold = self.active_monster.gold_reward + sword_gold_bonus

            self.hero.star_points += earned_stars
            self.hero.gold += earned_gold
            self.active_monster.defeated = True

            self.combat_feedback = (
                f"{feedback} Shield shattered! +{earned_stars} Star Points, +{earned_gold} Gold! "
                f"({ai_note})"
            )
            self._sync_leaderboard()
            return True, "monster_defeated"

        # Incorrect choice: Shield deflects spell & monster counters!
        self.combat_result_state = "deflect_anim"
        self.consecutive_wrong_in_battle += 1
        self.total_consecutive_wrong += 1
        self.hero.wrong_answers += 1
        self.hero.streak = 0
        damage = self.active_monster.attack_damage
        self.hero.hp = max(0, self.hero.hp - damage)
        self.question_timer_sec = 0.0

        if self.hero.hp <= 0:
            self.combat_feedback = f"{feedback} {self.active_monster.name} counterattacks! Hero fell in battle..."
            self.scene = GameScene.GAME_OVER
            self._sync_leaderboard()
            return False, "game_over"

        # Check Short Division Tutorial Fairy trigger (2 wrong in a row, or 1 if Fairy Charm owned)
        fairy_threshold = 1 if self.hero.has_fairy_charm else 2
        if self.consecutive_wrong_in_battle >= fairy_threshold:
            self.combat_feedback = (
                f"{feedback} (-{damage} HP). The Short Division Tutorial Fairy appears to help!"
            )
            self.open_fairy_tutorial(auto_triggered=True)
            return False, "fairy_triggered"

        self.combat_feedback = (
            f"{feedback} Monster counters for -{damage} HP! "
            f"(1 more mistake summons the Tutorial Fairy, or press H for help!)"
        )
        return False, "shield_deflected"

    def finish_combat_victory(self) -> None:
        """Return from a victorious battle to the exploration map (or trigger final boss cutscene)."""
        if self.active_monster and self.active_monster.is_boss and self. all_zone_monsters_defeated():
            self.active_monster = None
            self.trigger_stage_end_cutscene()
            return

        self.active_monster = None
        self.scene = GameScene.EXPLORE
        if self.all_zone_monsters_defeated():
            self.status_banner = (
                "All monsters in this zone defeated! Head right to the glowing Castle Gate Portal!"
            )
        else:
            remaining = sum(1 for m in self.monsters if not m.defeated)
            self.status_banner = (
                f"Victory! {remaining} monster(s) left in this zone. Progress Bar advanced!"
            )

    def open_fairy_tutorial(self, auto_triggered: bool = False) -> None:
        """Open the Short Division Tutorial Fairy overlay for the active combat problem."""
        if self.active_monster is None or self.active_monster.problem is None:
            return
        self.fairy_auto_triggered = auto_triggered
        self.fairy_step_index = 0
        self.fairy_tab = "short_division"
        self.scene = GameScene.FAIRY_TUTORIAL

    def close_fairy_tutorial(self) -> None:
        """Close the Fairy tutorial and resume combat."""
        self.scene = GameScene.COMBAT

    def buy_shop_item(self, item_index: int) -> Tuple[bool, str]:
        """Attempt to purchase an item from the Equipment Shop."""
        if not (0 <= item_index < len(self.shop_items)):
            return False, "Invalid item selection."

        item = self.shop_items[item_index]
        if item.purchased and item.category != "consumable":
            return False, f"You already own {item.name}!"

        if self.hero.gold < item.cost:
            return False, f"Not enough Gold! Need {item.cost}G (You have {self.hero.gold}G)."

        if item.category == "consumable" and self.hero.hp >= self.hero.max_hp:
            return False, "Your HP is already full!"

        self.hero.gold -= item.cost

        if item.category == "sword":
            item.purchased = True
            if item.tier_level >= self.hero.sword_level:
                self.hero.sword_level = item.tier_level
                self.hero.sword_name = item.name
            return True, f"Equipped {item.name}! Weapon visuals & Star multiplier upgraded!"

        if item.category == "shield":
            item.purchased = True
            self.hero.max_hp += item.hp_bonus
            self.hero.hp = min(self.hero.max_hp, self.hero.hp + item.heal_amount)
            if item.tier_level >= self.hero.shield_level:
                self.hero.shield_level = item.tier_level
                self.hero.shield_name = item.name
            return True, f"Equipped {item.name}! Max HP increased to {self.hero.max_hp}!"

        if item.category == "charm":
            item.purchased = True
            self.hero.has_fairy_charm = True
            return True, f"Purchased {item.name}! The Tutorial Fairy now assists immediately!"

        if item.category == "consumable":
            self.hero.hp = min(self.hero.max_hp, self.hero.hp + item.heal_amount)
            return True, f"Drank {item.name}! Restored HP ({self.hero.hp}/{self.hero.max_hp})."

        return False, "Unknown item type."

    def trigger_stage_end_cutscene(self) -> None:
        """
        Trigger the Stage-End Princess Reward Cutscene upon clearing a full zone.
        The Princess sends a magical item down from her tower to unlock a new character tier.
        """
        info = ZoneConfig.ZONE_INFO[self.current_zone]
        new_tier = min(5, self.current_zone + 1)
        bonus_gold = 50 * self.current_zone
        bonus_stars = 200 * self.current_zone

        self.zones_cleared = max(self.zones_cleared, self.current_zone)
        self.hero.tier = max(self.hero.tier, new_tier)
        self.hero.gold += bonus_gold
        self.hero.star_points += bonus_stars
        self.hero.hp = self.hero.max_hp

        # Zone 3 narrative milestone: Earns the legendary Holy Sword!
        if self.current_zone == 3 and self.hero.sword_level < 3:
            self.hero.sword_level = 3
            self.hero.sword_name = "Legendary Holy Sword"

        if self.current_zone < self.max_zones:
            dialogues = [
                f"Stage {self.current_zone} Complete! {info['milestone']}",
                f"From the high tower of Demon Castle, Princess Aria sends a beam of starlight!",
                f"You received '{info['gift_name']}' and ascended to tier: {info['unlocked_tier_name']}!",
                f"Bonus Reward: +{bonus_stars} Star Points, +{bonus_gold} Gold, and Full HP Restoration!",
            ]
        else:
            dialogues = [
                "The Demon King's Three-Number Shield has been shattered forever!",
                "Princess Aria steps down from the crystal tower as peace returns to Numeria!",
                f"You received '{info['gift_name']}' and achieved the ultimate rank: {info['unlocked_tier_name']}!",
                f"Final Bonus: +{bonus_stars} Star Points and +{bonus_gold} Gold!",
            ]

        self.active_cutscene = CutsceneData(
            zone_completed=self.current_zone,
            title=f"Princess Tower Cutscene - {info['name']} Cleared!",
            princess_dialogue=dialogues,
            gift_item_name=info["gift_name"],
            new_hero_tier_name=info["unlocked_tier_name"],
            new_tier_index=new_tier,
            bonus_gold=bonus_gold,
            bonus_stars=bonus_stars,
        )
        self._sync_leaderboard()
        self.scene = GameScene.CUTSCENE

    def advance_after_cutscene(self) -> None:
        """Proceed to the next level zone after the Princess cutscene, or to Victory screen."""
        if self.current_zone < self.max_zones:
            self.load_zone(self.current_zone + 1)
            self.active_cutscene = None
            self.scene = GameScene.EXPLORE
        else:
            self.active_cutscene = None
            self.scene = GameScene.VICTORY

    def revive_or_restart(self, full_restart: bool = False) -> None:
        """Allow the player to either retry from the current zone with full HP or restart the game."""
        if full_restart:
            self.__init__()
            self.scene = GameScene.EXPLORE
            return
        self.hero.hp = self.hero.max_hp
        self.active_monster = None
        self.load_zone(self.current_zone)
        self.scene = GameScene.EXPLORE

    def _sync_leaderboard(self) -> None:
        """Update the player's live ranking on the Star Points Leaderboard."""
        self.leaderboard = [e for e in self.leaderboard if not e.is_player]
        self.leaderboard.append(
            LeaderboardEntry(
                name="Hero (You)",
                star_points=self.hero.star_points,
                tier_name=self.hero.tier_title,
                zones_cleared=self.zones_cleared,
                is_player=True,
            )
        )
        self.leaderboard.sort(key=lambda e: e.star_points, reverse=True)
