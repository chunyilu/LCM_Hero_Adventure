"""
Comprehensive Test Suite for LCM Hero Adventure (Model, View, Controller).
"""

from __future__ import annotations

import os

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")

import pygame
import pytest

from mvc.controller import GameController
from mvc.model import (
    AdaptiveEdgeAI,
    ArithmeticEngine,
    GameScene,
    GameStateModel,
    ProblemType,
    build_short_division,
    compute_lcm,
)


def test_compute_lcm_and_short_division():
    # Zone 1: Prime Pair [3, 5] -> 15
    assert compute_lcm((3, 5)) == 15
    steps_1, rem_1, factors_1 = build_short_division((3, 5))
    assert len(steps_1) == 0
    assert rem_1 == (3, 5)
    assert factors_1 == [3, 5]

    # Zone 2: Overlapping Factors [4, 6] -> 12
    assert compute_lcm((4, 6)) == 12
    steps_2, rem_2, factors_2 = build_short_division((4, 6))
    assert len(steps_2) == 1
    assert steps_2[0].divisor == 2
    assert rem_2 == (2, 3)
    assert factors_2 == [2, 2, 3]

    # Zone 3: Contained Multiples [3, 6] -> 6
    assert compute_lcm((3, 6)) == 6
    steps_3, rem_3, factors_3 = build_short_division((3, 6))
    assert len(steps_3) == 1
    assert steps_3[0].divisor == 3
    assert rem_3 == (1, 2)

    # Zone 4: Three-Number Rush [3, 4, 6] -> 12
    assert compute_lcm((3, 4, 6)) == 12
    steps_4, rem_4, factors_4 = build_short_division((3, 4, 6))
    prod = 1
    for f in factors_4:
        prod *= f
    assert prod == 12


def test_spell_cards_and_non_least_common_multiple_feedback():
    engine = ArithmeticEngine(seed=42)
    prob = engine.generate_problem(specific_numbers=(4, 6))
    assert prob.lcm == 12
    assert len(prob.spell_cards) == 4
    assert 12 in prob.spell_cards
    # 24 is a common multiple of 4 and 6, but not the least
    assert 24 in prob.spell_cards

    ok, msg = prob.evaluate_choice(12)
    assert ok is True
    assert "Least Common Multiple" in msg

    ok_24, msg_24 = prob.evaluate_choice(24)
    assert ok_24 is False
    assert "common multiple" in msg_24.lower()
    assert "not the least" in msg_24.lower()


def test_fairy_tutor_triggers_after_two_consecutive_mistakes():
    model = GameStateModel(seed=7)
    model.scene = GameScene.EXPLORE
    monster = model.monsters[0]
    monster.problem = model.engine.generate_problem(specific_numbers=(4, 6))
    model.start_combat(monster)

    wrong_index = next(
        i for i, v in enumerate(monster.problem.spell_cards) if v != monster.problem.lcm
    )
    initial_hp = model.hero.hp

    # 1st wrong answer -> shield deflects, HP drops by 1, still in COMBAT
    ok1, outcome1 = model.submit_spell_card(wrong_index)
    assert ok1 is False
    assert outcome1 == "shield_deflected"
    assert model.hero.hp == initial_hp - 1
    assert model.scene == GameScene.COMBAT

    # 2nd consecutive wrong answer -> triggers Short Division Tutorial Fairy!
    ok2, outcome2 = model.submit_spell_card(wrong_index)
    assert ok2 is False
    assert outcome2 == "fairy_triggered"
    assert model.scene == GameScene.FAIRY_TUTORIAL
    assert model.fairy_auto_triggered is True


def test_adaptive_edge_ai_latency_and_targeted_spawning():
    ai = AdaptiveEdgeAI()
    base_weight = ai.records[ProblemType.OVERLAPPING_FACTORS].spawn_weight
    assert base_weight == 1.0

    # Child takes >15 seconds (e.g. 18.5s) to solve [6, 8]
    note = ai.record_attempt(
        problem_type=ProblemType.OVERLAPPING_FACTORS,
        shield_numbers=(6, 8),
        is_correct=True,
        latency_sec=18.5,
    )
    assert ">15s" in note
    boosted_weight = ai.records[ProblemType.OVERLAPPING_FACTORS].spawn_weight
    assert boosted_weight > base_weight
    assert (6, 8) in ai.struggle_shields
    assert ai.needs_extra_reinforcement(ProblemType.OVERLAPPING_FACTORS) is True

    # Subsequent fast & accurate responses decay the extra spawn weight
    for _ in range(3):
        ai.record_attempt(
            problem_type=ProblemType.OVERLAPPING_FACTORS,
            shield_numbers=(6, 8),
            is_correct=True,
            latency_sec=4.0,
        )
    assert ai.records[ProblemType.OVERLAPPING_FACTORS].spawn_weight < boosted_weight


def test_equipment_shop_and_princess_progression():
    model = GameStateModel(seed=10)
    model.hero.gold = 300
    initial_max_hp = model.hero.max_hp

    # Buy The Multiplier Sword (index 0)
    bought_sword, _ = model.buy_shop_item(0)
    assert bought_sword is True
    assert model.hero.sword_level == 1
    assert model.hero.sword_name == "The Multiplier Sword"

    # Buy The Prime Number Shield (index 1)
    bought_shield, _ = model.buy_shop_item(1)
    assert bought_shield is True
    assert model.hero.shield_level == 1
    assert model.hero.max_hp == initial_max_hp + 3

    # Defeat all monsters across all 4 zones and verify Princess Rescue Progress & Cutscenes
    for zone in range(1, 5):
        assert model.current_zone == zone
        for m in list(model.monsters):
            model.start_combat(m)
            correct_idx = m.problem.spell_cards.index(m.problem.lcm)
            ok, outcome = model.submit_spell_card(correct_idx)
            assert ok is True
            assert outcome == "monster_defeated"
            model.finish_combat_victory()

        # Boss defeat triggers Stage-End Princess Cutscene
        assert model.scene == GameScene.CUTSCENE
        assert model.active_cutscene is not None
        model.advance_after_cutscene()

    assert model.scene == GameScene.VICTORY
    assert model.princess_rescue_progress == 1.0
    assert model.hero.tier == 5


def test_mvc_controller_and_view_render_all_scenes_headless():
    controller = GameController(headless=True)
    for scene in GameScene:
        controller.model.scene = scene
        if scene in (GameScene.COMBAT, GameScene.FAIRY_TUTORIAL):
            controller.model.start_combat(controller.model.monsters[0])
            controller.model.scene = scene
        elif scene == GameScene.CUTSCENE:
            controller.model.trigger_stage_end_cutscene()
        controller.step(0.016)
    pygame.quit()
