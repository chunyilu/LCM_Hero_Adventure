"""
Controller Layer: Main Pygame Event Loop & Input Coordinator.

Bridges `GameStateModel` (Arithmetic State Engine & Game State) and `GameView` (Render Layer).
"""

from __future__ import annotations

from typing import Optional

import pygame

from mvc.model import GameScene, GameStateModel
from mvc.view import SCREEN_HEIGHT, SCREEN_WIDTH, GameView


class GameController:
    """
    Coordinates user input (Keyboard + Mouse), delta-time updates,
    combat response latency tracking, and view rendering.
    """

    def __init__(
        self,
        model: Optional[GameStateModel] = None,
        view: Optional[GameView] = None,
        headless: bool = False,
    ) -> None:
        if not pygame.get_init():
            pygame.init()

        flags = pygame.HIDDEN if headless else 0
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT), flags)
        pygame.display.set_caption("LCM Hero Adventure — 2D Educational Math JRPG")

        self.model = model or GameStateModel()
        self.view = view or GameView(self.screen)
        self.clock = pygame.time.Clock()
        self.running = True

    def run(self, max_frames: Optional[int] = None) -> None:
        """Execute the main Pygame loop."""
        frames = 0
        while self.running:
            dt = self.clock.tick(60) / 1000.0
            self.step(dt)
            frames += 1
            if max_frames is not None and frames >= max_frames:
                break
        pygame.quit()

    def step(self, dt: float) -> None:
        """Process one frame of events, state updates, and rendering."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.handle_keydown(event.key)
            elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.handle_mouse_click(event.pos)

        # Update combat response latency timer when waiting for player's spell choice
        if (
            self.model.scene == GameScene.COMBAT
            and self.model.active_monster is not None
            and not self.model.active_monster.defeated
        ):
            self.model.question_timer_sec += dt

        self.view.update_animations(dt)
        self.view.render(self.model)
        pygame.display.flip()

    def handle_keydown(self, key: int) -> None:
        """Dispatch keyboard input according to the active GameScene."""
        scene = self.model.scene

        if scene == GameScene.TITLE:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.model.scene = GameScene.EXPLORE
                self.view.sound.play("cutscene")
            elif key == pygame.K_ESCAPE:
                self.running = False
            return

        # Global overlay hotkeys when in EXPLORE
        if scene == GameScene.EXPLORE:
            if key == pygame.K_b:
                self.model.previous_scene = GameScene.EXPLORE
                self.model.scene = GameScene.SHOP
                return
            if key == pygame.K_i:
                self.model.previous_scene = GameScene.EXPLORE
                self.model.scene = GameScene.AI_DASHBOARD
                return
            if key == pygame.K_l:
                self.model.previous_scene = GameScene.EXPLORE
                self.model.scene = GameScene.LEADERBOARD
                return

            dx, dy = 0, 0
            if key in (pygame.K_LEFT, pygame.K_a):
                dx = -1
            elif key in (pygame.K_RIGHT, pygame.K_d):
                dx = 1
            elif key in (pygame.K_UP, pygame.K_w):
                dy = -1
            elif key in (pygame.K_DOWN, pygame.K_s):
                dy = 1

            if dx != 0 or dy != 0:
                res = self.model.move_hero(dx, dy)
                if res == "moved":
                    self.view.sound.play("step")
                elif res == "combat":
                    self.view.sound.play("encounter")
                elif res == "cutscene":
                    self.view.sound.play("cutscene")
                    self.view.spawn_burst(512, 280, (255, 235, 110), count=36)
            return

        if scene == GameScene.COMBAT:
            monster = self.model.active_monster
            if monster is not None and monster.defeated:
                if key in (pygame.K_RETURN, pygame.K_SPACE):
                    self.model.finish_combat_victory()
                return

            if key == pygame.K_h:
                self.model.open_fairy_tutorial(auto_triggered=False)
                self.view.sound.play("fairy")
                return

            if key in (pygame.K_LEFT, pygame.K_a):
                self.model.selected_card_index = (self.model.selected_card_index - 1) % 4
            elif key in (pygame.K_RIGHT, pygame.K_d):
                self.model.selected_card_index = (self.model.selected_card_index + 1) % 4
            elif key in (pygame.K_1, pygame.K_KP1):
                self._cast_card(0)
            elif key in (pygame.K_2, pygame.K_KP2):
                self._cast_card(1)
            elif key in (pygame.K_3, pygame.K_KP3):
                self._cast_card(2)
            elif key in (pygame.K_4, pygame.K_KP4):
                self._cast_card(3)
            elif key in (pygame.K_RETURN, pygame.K_SPACE):
                self._cast_card(self.model.selected_card_index)
            return

        if scene == GameScene.FAIRY_TUTORIAL:
            if key == pygame.K_TAB:
                self.model.fairy_tab = (
                    "multiples"
                    if self.model.fairy_tab == "short_division"
                    else "short_division"
                )
            elif key in (pygame.K_RETURN, pygame.K_SPACE, pygame.K_ESCAPE, pygame.K_h):
                self.model.close_fairy_tutorial()
            return

        if scene == GameScene.SHOP:
            if key in (pygame.K_ESCAPE, pygame.K_b, pygame.K_RETURN):
                self.model.scene = GameScene.EXPLORE
                return
            num_keys = [
                pygame.K_1,
                pygame.K_2,
                pygame.K_3,
                pygame.K_4,
                pygame.K_5,
                pygame.K_6,
            ]
            for idx, k in enumerate(num_keys):
                if key == k:
                    self._attempt_buy(idx)
            return

        if scene in (GameScene.AI_DASHBOARD, GameScene.LEADERBOARD):
            if key in (pygame.K_ESCAPE, pygame.K_RETURN, pygame.K_SPACE, pygame.K_i, pygame.K_l):
                self.model.scene = GameScene.EXPLORE
            return

        if scene == GameScene.CUTSCENE:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.model.advance_after_cutscene()
                self.view.sound.play("cutscene")
            return

        if scene == GameScene.VICTORY:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.model.revive_or_restart(full_restart=True)
            return

        if scene == GameScene.GAME_OVER:
            if key in (pygame.K_RETURN, pygame.K_SPACE):
                self.model.revive_or_restart(full_restart=False)
            return

    def handle_mouse_click(self, pos: tuple[int, int]) -> None:
        """Dispatch mouse clicks on registered UI buttons and cards."""
        rects = self.view.clickable_rects

        if "start_game" in rects and rects["start_game"].collidepoint(pos):
            self.model.scene = GameScene.EXPLORE
            self.view.sound.play("cutscene")
            return

        # Top HUD quick buttons
        if self.model.scene in (
            GameScene.EXPLORE,
            GameScene.SHOP,
            GameScene.AI_DASHBOARD,
            GameScene.LEADERBOARD,
        ):
            if "shop_btn" in rects and rects["shop_btn"].collidepoint(pos):
                self.model.scene = (
                    GameScene.EXPLORE
                    if self.model.scene == GameScene.SHOP
                    else GameScene.SHOP
                )
                return
            if "ai_btn" in rects and rects["ai_btn"].collidepoint(pos):
                self.model.scene = (
                    GameScene.EXPLORE
                    if self.model.scene == GameScene.AI_DASHBOARD
                    else GameScene.AI_DASHBOARD
                )
                return
            if "leader_btn" in rects and rects["leader_btn"].collidepoint(pos):
                self.model.scene = (
                    GameScene.EXPLORE
                    if self.model.scene == GameScene.LEADERBOARD
                    else GameScene.LEADERBOARD
                )
                return

        if self.model.scene == GameScene.COMBAT:
            if "fairy_help" in rects and rects["fairy_help"].collidepoint(pos):
                self.model.open_fairy_tutorial(auto_triggered=False)
                self.view.sound.play("fairy")
                return
            if "combat_continue" in rects and rects["combat_continue"].collidepoint(pos):
                self.model.finish_combat_victory()
                return
            for idx, c_rect in enumerate(self.view.spell_card_rects):
                if c_rect.collidepoint(pos):
                    self.model.selected_card_index = idx
                    self._cast_card(idx)
                    return

        if self.model.scene == GameScene.FAIRY_TUTORIAL:
            if "fairy_tab_sd" in rects and rects["fairy_tab_sd"].collidepoint(pos):
                self.model.fairy_tab = "short_division"
                return
            if "fairy_tab_mult" in rects and rects["fairy_tab_mult"].collidepoint(pos):
                self.model.fairy_tab = "multiples"
                return
            if "fairy_close" in rects and rects["fairy_close"].collidepoint(pos):
                self.model.close_fairy_tutorial()
                return

        if self.model.scene == GameScene.SHOP:
            for idx, b_rect in enumerate(self.view.shop_buy_rects):
                if b_rect.collidepoint(pos):
                    self._attempt_buy(idx)
                    return

        if "close_overlay" in rects and rects["close_overlay"].collidepoint(pos):
            self.model.scene = GameScene.EXPLORE
            return

        if "cutscene_next" in rects and rects["cutscene_next"].collidepoint(pos):
            self.model.advance_after_cutscene()
            self.view.sound.play("cutscene")
            return

        if "play_again" in rects and rects["play_again"].collidepoint(pos):
            self.model.revive_or_restart(full_restart=True)
            return

        if "retry_zone" in rects and rects["retry_zone"].collidepoint(pos):
            self.model.revive_or_restart(full_restart=False)
            return

    def _cast_card(self, card_index: int) -> None:
        is_correct, outcome = self.model.submit_spell_card(card_index)
        self.view.combat_anim_timer = 0.55
        if is_correct:
            self.view.sound.play("win")
            self.view.spawn_burst(740, 260, (110, 245, 255), count=35)
            self.view.spawn_burst(740, 360, (255, 230, 95), count=25)
        else:
            if outcome == "fairy_triggered":
                self.view.sound.play("fairy")
            else:
                self.view.sound.play("deflect")
            self.view.spawn_burst(270, 350, (255, 85, 95), count=22)

    def _attempt_buy(self, item_index: int) -> None:
        bought, msg = self.model.buy_shop_item(item_index)
        self.model.status_banner = msg
        if bought:
            self.view.sound.play("buy")
            self.view.spawn_burst(512, 300, (255, 225, 90), count=24)
        else:
            self.view.sound.play("deflect")
