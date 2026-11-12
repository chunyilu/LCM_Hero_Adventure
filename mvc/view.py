"""
View Layer: Pygame Render Layer, Procedural Pixel/Vector Sprites, Animations, and Chiptune Audio.

Decoupled from arithmetic generation logic; reads state from `GameStateModel`
and exposes UI hit-boxes for mouse interaction alongside full keyboard navigation.
"""

from __future__ import annotations

import array
import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

import pygame

from mvc.model import (
    GameScene,
    GameStateModel,
    HeroModel,
    LCMProblem,
    MonsterEntity,
    ProblemType,
    TileType,
    ZoneConfig,
)

SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 720


@dataclass
class Particle:
    """Visual particle for shield shattering, magic spells, and starlight cutscenes."""
    x: float
    y: float
    vx: float
    vy: float
    color: Tuple[int, int, int]
    size: float
    life: float
    max_life: float


class RetroSoundEngine:
    """
    Synthesizes retro JRPG sound effects purely in memory using sine/square waves.
    Gracefully becomes a no-op if audio hardware is unavailable (e.g. headless CI).
    """

    def __init__(self) -> None:
        self.enabled = False
        self.sounds: Dict[str, pygame.mixer.Sound] = {}
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init(frequency=22050, size=-16, channels=1, buffer=512)
            self.enabled = True
            self._build_sounds()
        except Exception:
            self.enabled = False

    def _make_tone(self, freqs: List[ Tuple[float, float] ], wave_type: str = "square", volume: float = 0.25) -> Optional[pygame.mixer.Sound]:
        if not self.enabled:
            return None
        sample_rate = 22050
        buf = array.array("h")
        for freq, duration in freqs:
            num_samples = int(sample_rate * duration)
            for i in range(num_samples):
                t = i / sample_rate
                envelope = max(0.0, 1.0 - (i / max(1, num_samples)) * 0.6)
                if freq <= 0:
                    val = 0.0
                elif wave_type == "square":
                    val = 1.0 if math.sin(2.0 * math.pi * freq * t) >= 0 else -1.0
                else:
                    val = math.sin(2.0 * math.pi * freq * t)
                sample = int(val * volume * envelope * 32767)
                buf.append(max(-32768, min(32767, sample)))
        try:
            return pygame.mixer.Sound(buffer=buf)
        except Exception:
            return None

    def _build_sounds(self) -> None:
        self.sounds["step"] = self._make_tone([(240, 0.03)], "sine", 0.12)
        self.sounds["encounter"] = self._make_tone(
            [(330, 0.06), (440, 0.06), (554, 0.08), (660, 0.12)], "square", 0.2
        )
        self.sounds["win"] = self._make_tone(
            [(523.25, 0.08), (659.25, 0.08), (783.99, 0.08), (1046.5, 0.22)], "square", 0.22
        )
        self.sounds["deflect"] = self._make_tone(
            [(300, 0.08), (180, 0.12), (120, 0.18)], "square", 0.25
        )
        self.sounds["fairy"] = self._make_tone(
            [(587.33, 0.07), (783.99, 0.07), (987.77, 0.09), (1174.66, 0.18)], "sine", 0.22
        )
        self.sounds["buy"] = self._make_tone(
            [(660, 0.06), (880, 0.12)], "sine", 0.22
        )
        self.sounds["cutscene"] = self._make_tone(
            [(440, 0.10), (554.37, 0.10), (659.25, 0.10), (880, 0.28)], "sine", 0.22
        )

    def play(self, name: str) -> None:
        if not self.enabled:
            return
        snd = self.sounds.get(name)
        if snd is not None:
            try:
                snd.play()
            except Exception:
                pass


class GameView:
    """
    Main Pygame Render Layer & UI Manager.
    Draws all game scenes, custom sprites, animations, and interactive buttons.
    """

    ZONE_THEMES = {
        1: {
            "floor_a": (46, 98, 58),
            "floor_b": (40, 88, 52),
            "wall": (28, 56, 36),
            "decor": (68, 138, 72),
            "sky_top": (28, 62, 48),
            "sky_bot": (62, 118, 78),
            "arena": (54, 108, 64),
            "accent": (120, 235, 140),
        },
        2: {
            "floor_a": (48, 52, 82),
            "floor_b": (42, 46, 74),
            "wall": (26, 28, 48),
            "decor": (118, 84, 188),
            "sky_top": (20, 22, 44),
            "sky_bot": (52, 48, 92),
            "arena": (60, 62, 98),
            "accent": (170, 140, 255),
        },
        3: {
            "floor_a": (92, 74, 58),
            "floor_b": (82, 66, 52),
            "wall": (52, 40, 34),
            "decor": (175, 145, 95),
            "sky_top": (58, 42, 68),
            "sky_bot": (128, 96, 78),
            "arena": (106, 86, 66),
            "accent": (255, 215, 110),
        },
        4: {
            "floor_a": (68, 34, 46),
            "floor_b": (58, 28, 40),
            "wall": (36, 16, 24),
            "decor": (185, 52, 62),
            "sky_top": (32, 12, 22),
            "sky_bot": (88, 26, 38),
            "arena": (78, 36, 48),
            "accent": (255, 95, 105),
        },
    }

    def __init__(self, screen: pygame.Surface) -> None:
        self.screen = screen
        self.sound = RetroSoundEngine()
        pygame.font.init()

        # Load clean fallback fonts supporting math symbols
        self.font_xs = pygame.font.SysFont("dejavusans,arial,sans-serif", 14)
        self.font_sm = pygame.font.SysFont("dejavusans,arial,sans-serif", 17)
        self.font_md = pygame.font.SysFont("dejavusans,arial,sans-serif", 20, bold=True)
        self.font_lg = pygame.font.SysFont("dejavusans,arial,sans-serif", 26, bold=True)
        self.font_xl = pygame.font.SysFont("dejavusans,arial,sans-serif", 36, bold=True)
        self.font_xxl = pygame.font.SysFont("dejavusans,arial,sans-serif", 46, bold=True)

        self.anim_time: float = 0.0
        self.combat_anim_timer: float = 0.0
        self.particles: List[Particle] = []

        # Interactive clickable rectangles registered during each frame's render
        self.clickable_rects: Dict[str, pygame.Rect] = {}
        self.spell_card_rects: List[pygame.Rect] = []
        self.shop_buy_rects: List[pygame.Rect] = []

    def update_animations(self, dt: float) -> None:
        """Advance visual timers and particle physics."""
        self.anim_time += dt
        if self.combat_anim_timer > 0.0:
            self.combat_anim_timer = max(0.0, self.combat_anim_timer - dt)

        alive: List[Particle] = []
        for p in self.particles:
            p.x += p.vx * dt
            p.y += p.vy * dt
            p.vy += 180.0 * dt
            p.life -= dt
            if p.life > 0:
                alive.append(p)
        self.particles = alive

    def spawn_burst(
        self, x: float, y: float, color: Tuple[int, int, int], count: int = 28
    ) -> None:
        """Spawn a celebratory or impact particle burst."""
        for i in range(count):
            angle = (2 * math.pi * i) / max(1, count) + (i % 3) * 0.2
            speed = 90.0 + (i % 5) * 45.0
            self.particles.append(
                Particle(
                    x=x,
                    y=y,
                    vx=math.cos(angle) * speed,
                    vy=math.sin(angle) * speed - 60.0,
                    color=color,
                    size=4 + (i % 4),
                    life=0.65 + (i % 3) * 0.15,
                    max_life=0.9,
                )
            )

    def render(self, model: GameStateModel) -> None:
        """Render the current scene and top HUD bar."""
        self.clickable_rects.clear()
        self.spell_card_rects.clear()
        self.shop_buy_rects.clear()
        self.screen.fill((18, 22, 34))

        if model.scene == GameScene.TITLE:
            self._render_title_screen(model)
            self._render_particles()
            return

        # Permanent Top Progress & Status HUD for all in-game scenes
        self._render_top_hud(model)

        if model.scene == GameScene.EXPLORE:
            self._render_explore(model)
            self._render_particles()
        elif model.scene == GameScene.COMBAT:
            self._render_combat(model)
            self._render_particles()
        elif model.scene == GameScene.FAIRY_TUTORIAL:
            self._render_combat(model, dim_bg=True)
            self._render_fairy_tutorial(model)
        elif model.scene == GameScene.SHOP:
            self._render_explore(model)
            self._render_shop_overlay(model)
        elif model.scene == GameScene.CUTSCENE:
            self._render_cutscene(model)
            self._render_particles()
        elif model.scene == GameScene.AI_DASHBOARD:
            self._render_explore(model)
            self._render_ai_dashboard(model)
        elif model.scene == GameScene.LEADERBOARD:
            self._render_explore(model)
            self._render_leaderboard_overlay(model)
        elif model.scene == GameScene.VICTORY:
            self._render_victory_screen(model)
            self._render_particles()
        elif model.scene == GameScene.GAME_OVER:
            self._render_game_over_screen(model)

    # ------------------------------------------------------------------
    # Top HUD & Princess Rescue Progress Bar
    # ------------------------------------------------------------------
    def _render_top_hud(self, model: GameStateModel) -> None:
        hud_rect = pygame.Rect(0, 0, SCREEN_WIDTH, 96)
        pygame.draw.rect(self.screen, (20, 24, 38), hud_rect)
        pygame.draw.line(self.screen, (90, 110, 160), (0, 95), (SCREEN_WIDTH, 95), 2)

        # 1. Princess Rescue Progress Bar (Top row of HUD)
        bar_x, bar_y, bar_w, bar_h = 190, 14, 520, 22
        lbl = self.font_sm.render("Princess Rescue:", True, (255, 220, 130))
        self.screen.blit(lbl, (16, 14))

        # Progress bar background
        pygame.draw.rect(self.screen, (40, 46, 70), (bar_x, bar_y, bar_w, bar_h), border_radius=11)
        progress = model.princess_rescue_progress
        fill_w = int(bar_w * max(0.03, progress))
        pygame.draw.rect(
            self.screen, (90, 205, 130), (bar_x, bar_y, fill_w, bar_h), border_radius=11
        )
        pygame.draw.rect(
            self.screen, (180, 210, 255), (bar_x, bar_y, bar_w, bar_h), 2, border_radius=11
        )

        # Zone dividers (25%, 50%, 75%)
        for z in range(1, 4):
            zx = bar_x + int(bar_w * (z / 4.0))
            pygame.draw.line(self.screen, (110, 130, 175), (zx, bar_y + 2), (zx, bar_y + bar_h - 2), 2)

        # Left Icon: Hero Sword Icon
        self._draw_mini_sword_icon(bar_x - 18, bar_y + 11)
        # Moving Hero Head Marker along progress bar
        marker_x = bar_x + fill_w
        pygame.draw.circle(self.screen, (255, 235, 90), (marker_x, bar_y + bar_h // 2), 11)
        pygame.draw.circle(self.screen, (40, 80, 180), (marker_x, bar_y + bar_h // 2), 8)

        # Right Icon: Captured Princess Crown Icon
        self._draw_mini_crown_icon(bar_x + bar_w + 18, bar_y + 11)

        pct_txt = self.font_xs.render(f"{int(progress * 100)}%", True, (255, 255, 255))
        self.screen.blit(pct_txt, (bar_x + bar_w // 2 - 14, bar_y + 3))

        # Quick Navigation Buttons on Top-Right
        btn_specs = [
            ("shop_btn", "[B] Shop", (745, 10, 85, 30), (75, 130, 95)),
            ("ai_btn", "[I] Edge AI", (836, 10, 92, 30), (80, 105, 165)),
            ("leader_btn", "[L] Ranks", (934, 10, 80, 30), (145, 95, 155)),
        ]
        for key, text, rect_tuple, col in btn_specs:
            r = pygame.Rect(*rect_tuple)
            self.clickable_rects[key] = r
            pygame.draw.rect(self.screen, col, r, border_radius=6)
            pygame.draw.rect(self.screen, (220, 230, 255), r, 1, border_radius=6)
            t_surf = self.font_xs.render(text, True, (255, 255, 255))
            self.screen.blit(
                t_surf,
                (r.centerx - t_surf.get_width() // 2, r.centery - t_surf.get_height() // 2),
            )

        # 2. Second Row of HUD: HP, Star Points, Gold, Hero Tier & Gear
        hero = model.hero
        hp_label = self.font_md.render(f"HP: {hero.hp}/{hero.max_hp}", True, (255, 110, 120))
        self.screen.blit(hp_label, (16, 54))
        for i in range(hero.max_hp):
            hx = 115 + i * 20
            hy = 64
            color = (240, 65, 85) if i < hero.hp else (75, 55, 65)
            pygame.draw.circle(self.screen, color, (hx - 4, hy - 2), 5)
            pygame.draw.circle(self.screen, color, (hx + 4, hy - 2), 5)
            pygame.draw.polygon(self.screen, color, [(hx - 9, hy), (hx + 9, hy), (hx, hy + 9)])

        # Star Points & Gold Coins
        star_x = 125 + hero.max_hp * 20 + 16
        star_txt = self.font_md.render(f"Stars: {hero.star_points}", True, (255, 225, 80))
        self.screen.blit(star_txt, (star_x, 54))

        gold_x = star_x + star_txt.get_width() + 24
        gold_txt = self.font_md.render(f"Gold: {hero.gold}G", True, (255, 195, 55))
        self.screen.blit(gold_txt, (gold_x, 54))

        # Tier & Equipment Summary
        gear_x = gold_x + gold_txt.get_width() + 24
        tier_str = f"Tier {hero.tier}: {hero.tier_title} | {hero.sword_name} | {hero.shield_name}"
        gear_txt = self.font_xs.render(tier_str, True, (185, 220, 255))
        self.screen.blit(gear_txt, (gear_x, 58))

    # ------------------------------------------------------------------
    # Title Screen
    # ------------------------------------------------------------------
    def _render_title_screen(self, model: GameStateModel) -> None:
        # Starry JRPG night gradient
        for y in range(SCREEN_HEIGHT):
            ratio = y / SCREEN_HEIGHT
            r = int(18 + ratio * 28)
            g = int(24 + ratio * 48)
            b = int(52 + ratio * 72)
            pygame.draw.line(self.screen, (r, g, b), (0, y), (SCREEN_WIDTH, y))

        # Title Banner Card
        card = pygame.Rect(112, 48, 800, 175)
        pygame.draw.rect(self.screen, (28, 36, 64), card, border_radius=16)
        pygame.draw.rect(self.screen, (255, 215, 90), card, 3, border_radius=16)

        title = self.font_xxl.render("LCM HERO ADVENTURE", True, (255, 225, 95))
        sub = self.font_md.render(
            "A 2D Educational Math JRPG — Break Monster Shields with Least Common Multiples!",
            True,
            (190, 230, 255),
        )
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 72))
        self.screen.blit(sub, (SCREEN_WIDTH // 2 - sub.get_width() // 2, 135))

        concept_tag = self.font_sm.render(
            "Featuring: 4 Math Zones  |  Short Division Fairy Tutor  |  Adaptive Edge AI",
            True,
            (140, 240, 175),
        )
        self.screen.blit(concept_tag, (SCREEN_WIDTH // 2 - concept_tag.get_width() // 2, 176))

        # Center Stage Preview: Hero vs Monster with [4, 6] LCM Shield
        stage = pygame.Rect(152, 248, 720, 260)
        pygame.draw.rect(self.screen, (34, 58, 52), stage, border_radius=14)
        pygame.draw.rect(self.screen, (110, 190, 145), stage, 2, border_radius=14)

        self._draw_hero_sprite(310, 415, model.hero, scale=1.4)
        self._draw_shield_badge(680, 305, (4, 6), pulse=True)
        self._draw_monster_sprite(680, 420, "slime", is_boss=False, scale=1.4)

        vs_txt = self.font_xl.render("LCM(4, 6) = 12 !", True, (255, 235, 110))
        self.screen.blit(vs_txt, (SCREEN_WIDTH // 2 - vs_txt.get_width() // 2, 365))

        # Start Button
        start_btn = pygame.Rect(SCREEN_WIDTH // 2 - 170, 538, 340, 62)
        self.clickable_rects["start_game"] = start_btn
        pulse = int(abs(math.sin(self.anim_time * 3.0)) * 35)
        pygame.draw.rect(self.screen, (55 + pulse, 155 + pulse, 85), start_btn, border_radius=12)
        pygame.draw.rect(self.screen, (255, 240, 150), start_btn, 3, border_radius=12)
        btn_lbl = self.font_lg.render("START ADVENTURE (Enter)", True, (255, 255, 255))
        self.screen.blit(
            btn_lbl,
            (start_btn.centerx - btn_lbl.get_width() // 2, start_btn.centery - btn_lbl.get_height() // 2),
        )

        # Controls footer
        footer = self.font_sm.render(
            "Controls: Arrow Keys / WASD to Move  |  1-4 or Click to Cast Spell Cards  |  H for Fairy Tutor  |  B for Shop",
            True,
            (200, 215, 240),
        )
        self.screen.blit(footer, (SCREEN_WIDTH // 2 - footer.get_width() // 2, 640))

    # ------------------------------------------------------------------
    # Exploration View (2D Tile Map)
    # ------------------------------------------------------------------
    def _render_explore(self, model: GameStateModel) -> None:
        theme = self.ZONE_THEMES.get(model.current_zone, self.ZONE_THEMES[1])
        info = ZoneConfig.ZONE_INFO[model.current_zone]

        # Zone Header Banner below HUD
        banner_rect = pygame.Rect(0, 96, SCREEN_WIDTH, 42)
        pygame.draw.rect(self.screen, (30, 36, 54), banner_rect)
        z_title = self.font_sm.render(
            f"{info['name']} — {info['shield_type_label']}", True, theme["accent"]
        )
        self.screen.blit(z_title, (20, 108))

        milestone_txt = self.font_xs.render(info["concept_desc"], True, (215, 225, 245))
        self.screen.blit(milestone_txt, (SCREEN_WIDTH - milestone_txt.get_width() - 20, 110))

        # Tile Map Grid (16x10)
        tile_w = 56
        tile_h = 50
        map_offset_x = (SCREEN_WIDTH - model.MAP_COLS * tile_w) // 2
        map_offset_y = 148

        for r in range(model.MAP_ROWS):
            for c in range(model.MAP_COLS):
                tx = map_offset_x + c * tile_w
                ty = map_offset_y + r * tile_h
                rect = pygame.Rect(tx, ty, tile_w, tile_h)
                tile = model.grid[r][c]

                floor_col = theme["floor_a"] if (r + c) % 2 == 0 else theme["floor_b"]
                pygame.draw.rect(self.screen, floor_col, rect)

                if tile == TileType.WALL:
                    pygame.draw.rect(self.screen, theme["wall"], rect)
                    pygame.draw.rect(self.screen, (18, 20, 30), rect, 1)
                elif tile == TileType.DECOR:
                    pygame.draw.rect(
                        self.screen, theme["decor"], rect.inflate(-12, -12), border_radius=8
                    )
                elif tile == TileType.SHOP:
                    self._draw_shop_tile(rect)
                elif tile == TileType.SIGN:
                    self._draw_sign_tile(rect)
                elif tile == TileType.PORTAL:
                    self._draw_portal_tile(rect, unlocked=model.all_zone_monsters_defeated())

        # Draw Undefeated Monsters with floating LCM Shield previews
        for monster in model.monsters:
            if monster.defeated:
                continue
            mx = map_offset_x + monster.grid_x * tile_w + tile_w // 2
            my = map_offset_y + monster.grid_y * tile_h + tile_h // 2 + 6
            bob = int(math.sin(self.anim_time * 4.0 + monster.id) * 3)
            self._draw_monster_sprite(
                mx, my + bob, monster.species, is_boss=monster.is_boss, scale=0.72
            )
            if monster.problem:
                self._draw_mini_map_shield(mx, my - 30 + bob, monster.problem.numbers)

        # Draw Hero on Map
        hx = map_offset_x + model.hero.grid_x * tile_w + tile_w // 2
        hy = map_offset_y + model.hero.grid_y * tile_h + tile_h // 2 + 6
        self._draw_hero_sprite(hx, hy, model.hero, scale=0.82)

        # Bottom Status Bar
        footer_rect = pygame.Rect(0, SCREEN_HEIGHT - 64, SCREEN_WIDTH, 64)
        pygame.draw.rect(self.screen, (20, 24, 38), footer_rect)
        pygame.draw.line(
            self.screen, (90, 110, 160), (0, SCREEN_HEIGHT - 64), (SCREEN_WIDTH, SCREEN_HEIGHT - 64), 2
        )
        status_surf = self.font_md.render(model.status_banner, True, (255, 235, 145))
        self.screen.blit(status_surf, (24, SCREEN_HEIGHT - 52))

        help_surf = self.font_xs.render(
            "Move: Arrow Keys / WASD  |  Step onto a Monster to Battle  |  Step onto SHOP (top-left) or press B to buy upgrades",
            True,
            (175, 195, 225),
        )
        self.screen.blit(help_surf, (24, SCREEN_HEIGHT - 24))

    # ------------------------------------------------------------------
    # Combat View (Turn-Based LCM Shield System)
    # ------------------------------------------------------------------
    def _render_combat(self, model: GameStateModel, dim_bg: bool = False) -> None:
        theme = self.ZONE_THEMES.get(model.current_zone, self.ZONE_THEMES[1])
        monster = model.active_monster
        if monster is None or monster.problem is None:
            return
        problem = monster.problem

        # Sky & Arena backdrop
        combat_area = pygame.Rect(0, 96, SCREEN_WIDTH, SCREEN_HEIGHT - 96)
        pygame.draw.rect(self.screen, theme["sky_top"], combat_area)
        pygame.draw.rect(
            self.screen, theme["sky_bot"], pygame.Rect(0, 210, SCREEN_WIDTH, 220)
        )
        pygame.draw.rect(
            self.screen, theme["arena"], pygame.Rect(0, 380, SCREEN_WIDTH, 340)
        )

        # Zone & Concept Banner
        info = ZoneConfig.ZONE_INFO[model.current_zone]
        concept_lbl = self.font_sm.render(
            f"{info['name']}  |  Concept: {problem.problem_type.value.replace('_', ' ').title()}",
            True,
            theme["accent"],
        )
        self.screen.blit(concept_lbl, (24, 113))

        # Adaptive Latency Timer Display + Fairy Tutor Help Button
        timer_color = (
            (130, 235, 160)
            if model.question_timer_sec <= 15.0
            else (255, 165, 90)
        )
        timer_lbl = self.font_xs.render(
            f"Response Time: {model.question_timer_sec:.1f}s (AI Target < 15s)",
            True,
            timer_color,
        )
        self.screen.blit(timer_lbl, (520, 115))

        if not dim_bg:
            fairy_btn = pygame.Rect(815, 106, 185, 34)
            self.clickable_rects["fairy_help"] = fairy_btn
            pygame.draw.rect(self.screen, (135, 80, 185), fairy_btn, border_radius=8)
            pygame.draw.rect(self.screen, (245, 200, 255), fairy_btn, 2, border_radius=8)
            f_txt = self.font_sm.render("[H] Fairy Tutor", True, (255, 255, 255))
            self.screen.blit(
                f_txt,
                (fairy_btn.centerx - f_txt.get_width() // 2, fairy_btn.centery - f_txt.get_height() // 2),
            )

        # Platforms
        pygame.draw.ellipse(self.screen, (35, 45, 55), (160, 395, 220, 55))
        pygame.draw.ellipse(self.screen, (35, 45, 55), (620, 395, 240, 55))

        # Calculate attack / deflect animation offsets
        hero_x, hero_y = 270, 375
        mon_x, mon_y = 740, 375
        if model.combat_result_state == "hit_anim" and self.combat_anim_timer > 0:
            hero_x += int(math.sin(self.combat_anim_timer * math.pi) * 90)
        elif model.combat_result_state == "deflect_anim" and self.combat_anim_timer > 0:
            mon_x -= int(math.sin(self.combat_anim_timer * math.pi) * 85)

        # Draw Hero on left
        self._draw_hero_sprite(hero_x, hero_y, model.hero, scale=1.55)

        # Draw Monster & Mathematical Shield on right
        if not monster.defeated:
            self._draw_shield_badge(mon_x, mon_y - 145, problem.numbers, pulse=True)
            self._draw_monster_sprite(
                mon_x, mon_y, monster.species, is_boss=monster.is_boss, scale=1.55
            )
        else:
            defeated_txt = self.font_xl.render("SHIELD SHATTERED!", True, (120, 255, 160))
            self.screen.blit(defeated_txt, (mon_x - defeated_txt.get_width() // 2, mon_y - 90))

        # Monster Name Plate
        m_plate = self.font_md.render(
            f"{monster.name} {'(BOSS)' if monster.is_boss else ''}",
            True,
            (255, 220, 220),
        )
        self.screen.blit(m_plate, (mon_x - m_plate.get_width() // 2, 432))

        # Combat Dialogue & Feedback Box
        msg_box = pygame.Rect(36, 466, SCREEN_WIDTH - 72, 68)
        pygame.draw.rect(self.screen, (22, 28, 46), msg_box, border_radius=10)
        pygame.draw.rect(self.screen, (120, 155, 220), msg_box, 2, border_radius=10)
        self._draw_wrapped_text(
            model.combat_feedback,
            self.font_md,
            (255, 245, 190),
            msg_box.inflate(-24, -14),
        )

        # Spell Cards Panel (Bottom)
        if monster.defeated:
            cont_btn = pygame.Rect(SCREEN_WIDTH // 2 - 160, 568, 320, 64)
            if not dim_bg:
                self.clickable_rects["combat_continue"] = cont_btn
            pygame.draw.rect(self.screen, (55, 165, 95), cont_btn, border_radius=12)
            pygame.draw.rect(self.screen, (230, 255, 220), cont_btn, 3, border_radius=12)
            c_txt = self.font_lg.render("VICTORY! Continue (Enter)", True, (255, 255, 255))
            self.screen.blit(
                c_txt,
                (cont_btn.centerx - c_txt.get_width() // 2, cont_btn.centery - c_txt.get_height() // 2),
            )
        else:
            prompt_lbl = self.font_sm.render(
                "Select the Least Common Multiple (LCM) Spell Card (Keys 1-4, Arrows+Enter, or Click):",
                True,
                (200, 225, 255),
            )
            self.screen.blit(prompt_lbl, (42, 542))

            card_w = 212
            card_h = 112
            gap = 26
            total_w = 4 * card_w + 3 * gap
            start_x = (SCREEN_WIDTH - total_w) // 2
            card_y = 572

            for idx, val in enumerate(problem.spell_cards):
                rect = pygame.Rect(start_x + idx * (card_w + gap), card_y, card_w, card_h)
                if not dim_bg:
                    self.spell_card_rects.append(rect)
                is_selected = idx == model.selected_card_index
                bg_col = (58, 86, 158) if is_selected else (36, 48, 84)
                border_col = (255, 225, 90) if is_selected else (115, 145, 205)

                pygame.draw.rect(self.screen, bg_col, rect, border_radius=12)
                pygame.draw.rect(self.screen, border_col, rect, 3 if is_selected else 2, border_radius=12)

                key_badge = self.font_xs.render(f"Card [{idx + 1}]", True, (185, 210, 255))
                self.screen.blit(key_badge, (rect.x + 12, rect.y + 10))

                spell_tag = self.font_xs.render("LCM Spell", True, (255, 210, 120))
                self.screen.blit(spell_tag, (rect.right - spell_tag.get_width() - 12, rect.y + 10))

                num_surf = self.font_xxl.render(str(val), True, (255, 255, 255))
                self.screen.blit(
                    num_surf,
                    (rect.centerx - num_surf.get_width() // 2, rect.centery - num_surf.get_height() // 2 + 10),
                )

        if dim_bg:
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((10, 12, 24, 185))
            self.screen.blit(overlay, (0, 0))

    # ------------------------------------------------------------------
    # Short Division (短除法) Tutorial Fairy Overlay
    # ------------------------------------------------------------------
    def _render_fairy_tutorial(self, model: GameStateModel) -> None:
        if model.active_monster is None or model.active_monster.problem is None:
            return
        problem = model.active_monster.problem

        panel = pygame.Rect(72, 110, SCREEN_WIDTH - 144, 565)
        pygame.draw.rect(self.screen, (28, 24, 52), panel, border_radius=16)
        pygame.draw.rect(self.screen, (235, 175, 255), panel, 3, border_radius=16)

        # Draw Fairy Character on Top-Left of Panel
        self._draw_fairy_sprite(panel.x + 68, panel.y + 72)

        header = self.font_lg.render(
            "Short Division Tutorial Fairy — Step-by-Step Guide", True, (255, 215, 255)
        )
        self.screen.blit(header, (panel.x + 135, panel.y + 18))

        trigger_reason = (
            "Triggered automatically after 2 consecutive mistakes — let's solve it step-by-step!"
            if model.fairy_auto_triggered
            else "Fairy Hint: Here is the step-by-step breakdown for this Mathematical Shield!"
        )
        sub_txt = self.font_xs.render(trigger_reason, True, (205, 235, 255))
        self.screen.blit(sub_txt, (panel.x + 135, panel.y + 50))

        self._draw_wrapped_text(
            problem.concept_hint,
            self.font_xs,
            (255, 235, 130),
            pygame.Rect(panel.x + 135, panel.y + 72, panel.width - 160, 36),
        )

        # Mode Switch Tabs: [1] Short Division vs [2] Multiples List
        tab1 = pygame.Rect(panel.x + 135, panel.y + 112, 260, 34)
        tab2 = pygame.Rect(panel.x + 410, panel.y + 112, 260, 34)
        self.clickable_rects["fairy_tab_sd"] = tab1
        self.clickable_rects["fairy_tab_mult"] = tab2

        sd_active = model.fairy_tab == "short_division"
        pygame.draw.rect(
            self.screen, (115, 70, 175) if sd_active else (50, 42, 82), tab1, border_radius=8
        )
        pygame.draw.rect(self.screen, (230, 190, 255), tab1, 2 if sd_active else 1, border_radius=8)
        t1_lbl = self.font_sm.render("Method 1: Short Division", True, (255, 255, 255))
        self.screen.blit(t1_lbl, (tab1.centerx - t1_lbl.get_width() // 2, tab1.y + 7))

        pygame.draw.rect(
            self.screen, (115, 70, 175) if not sd_active else (50, 42, 82), tab2, border_radius=8
        )
        pygame.draw.rect(self.screen, (230, 190, 255), tab2, 2 if not sd_active else 1, border_radius=8)
        t2_lbl = self.font_sm.render("Method 2: Listing Multiples", True, (255, 255, 255))
        self.screen.blit(t2_lbl, (tab2.centerx - t2_lbl.get_width() // 2, tab2.y + 7))

        # Inner Canvas for Math Steps
        canvas = pygame.Rect(panel.x + 32, panel.y + 158, panel.width - 64, 330)
        pygame.draw.rect(self.screen, (18, 18, 36), canvas, border_radius=12)
        pygame.draw.rect(self.screen, (110, 120, 175), canvas, 2, border_radius=12)

        if sd_active:
            self._render_short_division_diagram(canvas, problem)
        else:
            self._render_multiples_diagram(canvas, problem)

        # Close / Return to Battle Button
        close_btn = pygame.Rect(panel.centerx - 160, panel.bottom - 62, 320, 46)
        self.clickable_rects["fairy_close"] = close_btn
        pygame.draw.rect(self.screen, (65, 165, 105), close_btn, border_radius=10)
        pygame.draw.rect(self.screen, (220, 255, 225), close_btn, 2, border_radius=10)
        c_lbl = self.font_md.render(
            f"Got It! Cast {problem.lcm} in Battle (Enter / Esc)", True, (255, 255, 255)
        )
        self.screen.blit(
            c_lbl,
            (close_btn.centerx - c_lbl.get_width() // 2, close_btn.centery - c_lbl.get_height() // 2),
        )

    def _render_short_division_diagram(self, canvas: pygame.Rect, problem: LCMProblem) -> None:
        """Render the visual Short Division (短除法) L-bracket step-by-step table."""
        bx = canvas.x + 70
        by = canvas.y + 28
        col_w = 78
        row_h = 48
        num_cols = len(problem.numbers)

        steps = problem.short_division_steps
        if not steps:
            # Coprime numbers: no shared prime divisor > 1
            row_y = by + 15
            div_txt = self.font_lg.render("1", True, (255, 140, 140))
            self.screen.blit(div_txt, (bx - 36, row_y))
            # Draw L-bracket
            pygame.draw.line(
                self.screen, (220, 230, 255), (bx - 8, row_y - 4), (bx - 8, row_y + row_h - 8), 3
            )
            pygame.draw.line(
                self.screen,
                (220, 230, 255),
                (bx - 8, row_y + row_h - 8),
                (bx + num_cols * col_w, row_y + row_h - 8),
                3,
            )
            for c_idx, n in enumerate(problem.numbers):
                nt = self.font_lg.render(str(n), True, (255, 255, 255))
                self.screen.blit(nt, (bx + 20 + c_idx * col_w, row_y))
                rt = self.font_lg.render(str(n), True, (130, 245, 170))
                self.screen.blit(rt, (bx + 20 + c_idx * col_w, row_y + row_h))

            note = self.font_md.render(
                f"Step 1: {list(problem.numbers)} share NO common prime factor > 1 (Coprime!).",
                True,
                (255, 225, 140),
            )
            self.screen.blit(note, (bx + 260, by + 24))
        else:
            for s_idx, step in enumerate(steps):
                row_y = by + s_idx * row_h
                # Prime divisor on the left of the L-bracket
                div_surf = self.font_lg.render(str(step.divisor), True, (255, 130, 145))
                self.screen.blit(div_surf, (bx - 38, row_y + 6))

                # L-bracket lines
                pygame.draw.line(
                    self.screen,
                    (220, 230, 255),
                    (bx - 8, row_y + 2),
                    (bx - 8, row_y + row_h),
                    3,
                )
                pygame.draw.line(
                    self.screen,
                    (220, 230, 255),
                    (bx - 8, row_y + row_h),
                    (bx + num_cols * col_w, row_y + row_h),
                    3,
                )

                # Input numbers for this row
                for c_idx, val in enumerate(step.input_numbers):
                    v_surf = self.font_lg.render(str(val), True, (255, 255, 255))
                    self.screen.blit(v_surf, (bx + 20 + c_idx * col_w, row_y + 6))

                # Explanation on the right
                exp_surf = self.font_sm.render(
                    f"Step {s_idx + 1}: {step.explanation}", True, (195, 225, 255)
                )
                self.screen.blit(exp_surf, (bx + num_cols * col_w + 30, row_y + 12))

            # Final bottom remainders row
            final_y = by + len(steps) * row_h + 8
            for c_idx, rem in enumerate(problem.final_remainders):
                r_surf = self.font_lg.render(str(rem), True, (130, 245, 170))
                self.screen.blit(r_surf, (bx + 20 + c_idx * col_w, final_y))

            rem_note = self.font_sm.render(
                f"Bottom quotients {list(problem.final_remainders)} share no more factors!",
                True,
                (130, 245, 170),
            )
            self.screen.blit(rem_note, (bx + num_cols * col_w + 30, final_y + 4))

        # Bottom Formula Banner: Multiply the L-shape numbers!
        formula_box = pygame.Rect(canvas.x + 24, canvas.bottom - 74, canvas.width - 48, 56)
        pygame.draw.rect(self.screen, (38, 52, 86), formula_box, border_radius=10)
        pygame.draw.rect(self.screen, (255, 220, 95), formula_box, 2, border_radius=10)

        factors_str = " × ".join(str(f) for f in problem.all_factors_for_lcm)
        nums_str = ", ".join(str(n) for n in problem.numbers)
        formula_txt = self.font_lg.render(
            f"Multiply outer L-shape:  LCM({nums_str}) = {factors_str} = {problem.lcm}",
            True,
            (255, 235, 105),
        )
        self.screen.blit(
            formula_txt,
            (
                formula_box.centerx - formula_txt.get_width() // 2,
                formula_box.centery - formula_txt.get_height() // 2,
            ),
        )

    def _render_multiples_diagram(self, canvas: pygame.Rect, problem: LCMProblem) -> None:
        """Render the side-by-side multiples list highlighting the Least Common Multiple."""
        title = self.font_md.render(
            "List the multiples of each shield number until you find the FIRST shared number:",
            True,
            (215, 230, 255),
        )
        self.screen.blit(title, (canvas.x + 28, canvas.y + 20))

        for idx, (num, mults) in enumerate(problem.multiples_dict.items()):
            ry = canvas.y + 68 + idx * 64
            lbl = self.font_lg.render(f"Multiples of {num}:", True, (255, 215, 120))
            self.screen.blit(lbl, (canvas.x + 28, ry + 6))

            mx = canvas.x + 235
            for m in mults[:9]:
                is_lcm = m == problem.lcm
                is_other_common = m > problem.lcm and all(m % n == 0 for n in problem.numbers)
                pill = pygame.Rect(mx, ry, 54, 40)
                if is_lcm:
                    pygame.draw.rect(self.screen, (55, 185, 100), pill, border_radius=8)
                    pygame.draw.rect(self.screen, (255, 240, 120), pill, 3, border_radius=8)
                elif is_other_common:
                    pygame.draw.rect(self.screen, (115, 85, 45), pill, border_radius=8)
                    pygame.draw.rect(self.screen, (220, 165, 90), pill, 2, border_radius=8)
                else:
                    pygame.draw.rect(self.screen, (38, 46, 76), pill, border_radius=8)

                m_surf = self.font_md.render(str(m), True, (255, 255, 255))
                self.screen.blit(
                    m_surf,
                    (pill.centerx - m_surf.get_width() // 2, pill.centery - m_surf.get_height() // 2),
                )
                mx += 62

        summary = self.font_lg.render(
            f"The smallest (LEAST) multiple shared by all rows is {problem.lcm}!",
            True,
            (130, 255, 165),
        )
        self.screen.blit(summary, (canvas.x + 28, canvas.bottom - 52))

    # ------------------------------------------------------------------
    # Village Equipment Shop Overlay
    # ------------------------------------------------------------------
    def _render_shop_overlay(self, model: GameStateModel) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 14, 26, 200))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(80, 108, SCREEN_WIDTH - 160, 570)
        pygame.draw.rect(self.screen, (26, 34, 56), panel, border_radius=16)
        pygame.draw.rect(self.screen, (255, 205, 95), panel, 3, border_radius=16)

        title = self.font_xl.render("VILLAGE EQUIPMENT SHOP", True, (255, 220, 95))
        self.screen.blit(title, (panel.x + 28, panel.y + 18))

        gold_lbl = self.font_lg.render(f"Your Gold: {model.hero.gold}G", True, (255, 200, 60))
        self.screen.blit(gold_lbl, (panel.right - gold_lbl.get_width() - 32, panel.y + 24))

        sub = self.font_sm.render(
            "Upgrade your Multiplier Sword (visuals & bonus points) and Prime Number Shield (extra Max HP)!",
            True,
            (195, 220, 250),
        )
        self.screen.blit(sub, (panel.x + 28, panel.y + 62))

        # Item rows
        for idx, item in enumerate(model.shop_items):
            ry = panel.y + 98 + idx * 66
            row_rect = pygame.Rect(panel.x + 24, ry, panel.width - 48, 58)
            pygame.draw.rect(self.screen, (38, 48, 78), row_rect, border_radius=10)
            pygame.draw.rect(self.screen, (95, 120, 175), row_rect, 1, border_radius=10)

            name_col = (150, 240, 170) if item.purchased else (255, 235, 150)
            n_surf = self.font_md.render(f"[{idx + 1}] {item.name}", True, name_col)
            self.screen.blit(n_surf, (row_rect.x + 16, row_rect.y + 8))

            d_surf = self.font_xs.render(item.description, True, (205, 215, 235))
            self.screen.blit(d_surf, (row_rect.x + 16, row_rect.y + 34))

            buy_btn = pygame.Rect(row_rect.right - 138, row_rect.y + 10, 124, 38)
            self.shop_buy_rects.append(buy_btn)
            if item.purchased and item.category != "consumable":
                pygame.draw.rect(self.screen, (60, 85, 70), buy_btn, border_radius=8)
                b_txt = self.font_sm.render("OWNED", True, (170, 235, 185))
            else:
                can_afford = model.hero.gold >= item.cost
                btn_col = (60, 155, 95) if can_afford else (95, 65, 75)
                pygame.draw.rect(self.screen, btn_col, buy_btn, border_radius=8)
                pygame.draw.rect(self.screen, (230, 235, 255), buy_btn, 1, border_radius=8)
                b_txt = self.font_sm.render(f"Buy ({item.cost}G)", True, (255, 255, 255))
            self.screen.blit(
                b_txt,
                (buy_btn.centerx - b_txt.get_width() // 2, buy_btn.centery - b_txt.get_height() // 2),
            )

        close_btn = pygame.Rect(panel.centerx - 120, panel.bottom - 56, 240, 42)
        self.clickable_rects["close_overlay"] = close_btn
        pygame.draw.rect(self.screen, (85, 105, 160), close_btn, border_radius=8)
        c_txt = self.font_md.render("Return to Map (Esc / B)", True, (255, 255, 255))
        self.screen.blit(
            c_txt,
            (close_btn.centerx - c_txt.get_width() // 2, close_btn.centery - c_txt.get_height() // 2),
        )

    # ------------------------------------------------------------------
    # Stage-End Princess Reward Cutscene
    # ------------------------------------------------------------------
    def _render_cutscene(self, model: GameStateModel) -> None:
        cs = model.active_cutscene
        if cs is None:
            return

        # Starlight night backdrop
        pygame.draw.rect(self.screen, (22, 18, 48), pygame.Rect(0, 96, SCREEN_WIDTH, SCREEN_HEIGHT - 96))

        # Princess Tower on the right
        tower_rect = pygame.Rect(680, 165, 160, 285)
        pygame.draw.rect(self.screen, (72, 68, 105), tower_rect)
        pygame.draw.polygon(self.screen, (145, 70, 125), [(665, 165), (855, 165), (760, 108)])
        # Tower balcony window
        pygame.draw.rect(self.screen, (255, 235, 150), (732, 185, 56, 68), border_radius=20)
        self._draw_princess_sprite(760, 232)

        # Hero receiving the magical gift on the left
        self._draw_hero_sprite(260, 390, model.hero, scale=1.55)

        # Animated Magical Item descending along a starlight beam from Princess's tower to Hero
        t = (math.sin(self.anim_time * 2.5) + 1.0) * 0.5
        gift_x = int(740 - t * 420)
        gift_y = int(225 + t * 130)
        pygame.draw.line(self.screen, (255, 235, 130), (745, 225), (275, 365), 3)
        pygame.draw.circle(self.screen, (255, 240, 120), (gift_x, gift_y), 18)
        pygame.draw.circle(self.screen, (255, 255, 255), (gift_x, gift_y), 10)

        # Cutscene Narrative Box
        box = pygame.Rect(72, 465, SCREEN_WIDTH - 144, 215)
        pygame.draw.rect(self.screen, (28, 32, 62), box, border_radius=14)
        pygame.draw.rect(self.screen, (255, 215, 105), box, 3, border_radius=14)

        t_surf = self.font_lg.render(cs.title, True, (255, 220, 100))
        self.screen.blit(t_surf, (box.x + 24, box.y + 16))

        for i, line in enumerate(cs.princess_dialogue):
            l_surf = self.font_md.render(line, True, (225, 235, 255))
            self.screen.blit(l_surf, (box.x + 24, box.y + 54 + i * 28))

        next_btn = pygame.Rect(box.centerx - 160, box.bottom - 52, 320, 42)
        self.clickable_rects["cutscene_next"] = next_btn
        pygame.draw.rect(self.screen, (65, 165, 105), next_btn, border_radius=8)
        n_txt = self.font_md.render("Continue Adventure (Enter)", True, (255, 255, 255))
        self.screen.blit(
            n_txt,
            (next_btn.centerx - n_txt.get_width() // 2, next_btn.centery - n_txt.get_height() // 2),
        )

    # ------------------------------------------------------------------
    # Adaptive Edge AI Dashboard & Leaderboard Overlays
    # ------------------------------------------------------------------
    def _render_ai_dashboard(self, model: GameStateModel) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 14, 26, 205))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(76, 110, SCREEN_WIDTH - 152, 560)
        pygame.draw.rect(self.screen, (22, 32, 54), panel, border_radius=16)
        pygame.draw.rect(self.screen, (110, 210, 255), panel, 3, border_radius=16)

        title = self.font_lg.render(
            "ADAPTIVE EDGE AI — OFFLINE PERFORMANCE MODEL", True, (125, 225, 255)
        )
        self.screen.blit(title, (panel.x + 28, panel.y + 22))

        desc = self.font_sm.render(
            "Tracks response latency (>15s threshold) & accuracy per shield category to dynamically adjust monster spawn rates.",
            True,
            (200, 220, 245),
        )
        self.screen.blit(desc, (panel.x + 28, panel.y + 62))

        headers = ["Mathematical Concept", "Attempts", "Accuracy", "Avg Latency", "Slow (>15s)", "AI Spawn Weight"]
        hx_positions = [panel.x + 28, panel.x + 300, panel.x + 410, panel.x + 530, panel.x + 660, panel.x + 765]
        for h_txt, hx in zip(headers, hx_positions):
            hs = self.font_sm.render(h_txt, True, (255, 220, 120))
            self.screen.blit(hs, (hx, panel.y + 104))

        for idx, pt in enumerate(ProblemType):
            rec = model.ai.records[pt]
            ry = panel.y + 138 + idx * 48
            row_r = pygame.Rect(panel.x + 22, ry, panel.width - 44, 40)
            pygame.draw.rect(self.screen, (32, 46, 74), row_r, border_radius=8)

            vals = [
                pt.value.replace("_", " ").title(),
                str(rec.attempts),
                f"{int(rec.accuracy * 100)}%",
                f"{rec.avg_latency:.1f}s",
                str(rec.slow_responses),
                f"{rec.spawn_weight:.2f}x {'(BOOSTED)' if rec.spawn_weight > 1.2 else '(Normal)'}",
            ]
            for v_idx, (val, vx) in enumerate(zip(vals, hx_positions)):
                col = (255, 150, 120) if (v_idx == 5 and rec.spawn_weight > 1.2) else (235, 245, 255)
                vs = self.font_sm.render(val, True, col)
                self.screen.blit(vs, (vx, ry + 10))

        # Recent AI Adaptation Logs
        log_title = self.font_md.render("Recent Edge AI Telemetry Events:", True, (165, 235, 190))
        self.screen.blit(log_title, (panel.x + 28, panel.y + 345))
        for i, entry in enumerate(model.ai.event_log[:5]):
            es = self.font_xs.render(f"• {entry}", True, (205, 225, 245))
            self.screen.blit(es, (panel.x + 36, panel.y + 378 + i * 24))

        close_btn = pygame.Rect(panel.centerx - 120, panel.bottom - 54, 240, 40)
        self.clickable_rects["close_overlay"] = close_btn
        pygame.draw.rect(self.screen, (75, 125, 175), close_btn, border_radius=8)
        c_txt = self.font_md.render("Close Dashboard (Esc / I)", True, (255, 255, 255))
        self.screen.blit(
            c_txt,
            (close_btn.centerx - c_txt.get_width() // 2, close_btn.centery - c_txt.get_height() // 2),
        )

    def _render_leaderboard_overlay(self, model: GameStateModel) -> None:
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((10, 14, 26, 205))
        self.screen.blit(overlay, (0, 0))

        panel = pygame.Rect(140, 120, SCREEN_WIDTH - 280, 520)
        pygame.draw.rect(self.screen, (32, 26, 54), panel, border_radius=16)
        pygame.draw.rect(self.screen, (255, 215, 95), panel, 3, border_radius=16)

        title = self.font_lg.render("HALL OF FAME — STAR POINTS LEADERBOARD", True, (255, 225, 95))
        self.screen.blit(title, (panel.centerx - title.get_width() // 2, panel.y + 22))

        model._sync_leaderboard()
        for idx, entry in enumerate(model.leaderboard[:6]):
            ry = panel.y + 88 + idx * 56
            row = pygame.Rect(panel.x + 32, ry, panel.width - 64, 46)
            bg = (75, 95, 55) if entry.is_player else (44, 38, 72)
            pygame.draw.rect(self.screen, bg, row, border_radius=8)
            if entry.is_player:
                pygame.draw.rect(self.screen, (255, 235, 110), row, 2, border_radius=8)

            rank_txt = self.font_md.render(f"#{idx + 1}  {entry.name}", True, (255, 255, 255))
            tier_txt = self.font_sm.render(entry.tier_name, True, (195, 220, 255))
            pts_txt = self.font_lg.render(f"{entry.star_points} PTS", True, (255, 225, 85))

            self.screen.blit(rank_txt, (row.x + 18, row.y + 11))
            self.screen.blit(tier_txt, (row.x + 280, row.y + 13))
            self.screen.blit(pts_txt, (row.right - pts_txt.get_width() - 20, row.y + 8))

        close_btn = pygame.Rect(panel.centerx - 120, panel.bottom - 56, 240, 42)
        self.clickable_rects["close_overlay"] = close_btn
        pygame.draw.rect(self.screen, (115, 85, 155), close_btn, border_radius=8)
        c_txt = self.font_md.render("Close Ranks (Esc / L)", True, (255, 255, 255))
        self.screen.blit(
            c_txt,
            (close_btn.centerx - c_txt.get_width() // 2, close_btn.centery - c_txt.get_height() // 2),
        )

    # ------------------------------------------------------------------
    # Victory & Game Over Screens
    # ------------------------------------------------------------------
    def _render_victory_screen(self, model: GameStateModel) -> None:
        pygame.draw.rect(self.screen, (24, 38, 62), pygame.Rect(0, 96, SCREEN_WIDTH, SCREEN_HEIGHT - 96))
        card = pygame.Rect(110, 140, SCREEN_WIDTH - 220, 510)
        pygame.draw.rect(self.screen, (32, 48, 82), card, border_radius=18)
        pygame.draw.rect(self.screen, (255, 225, 95), card, 4, border_radius=18)

        title = self.font_xxl.render("PRINCESS ARIA RESCUED!", True, (255, 230, 95))
        self.screen.blit(title, (card.centerx - title.get_width() // 2, card.y + 28))

        sub = self.font_lg.render(
            f"Congratulations, {model.hero.tier_title}! You mastered all 4 LCM Zones!",
            True,
            (165, 245, 195),
        )
        self.screen.blit(sub, (card.centerx - sub.get_width() // 2, card.y + 88))

        self._draw_hero_sprite(card.centerx - 90, card.y + 250, model.hero, scale=1.6)
        self._draw_princess_sprite(card.centerx + 90, card.y + 240)

        stats_lines = [
            f"Final Star Points: {model.hero.star_points}   |   Gold Collected: {model.hero.gold}G",
            f"Monsters Defeated: {model.hero.monsters_defeated}   |   Math Accuracy: "
            f"{int(100 * model.hero.correct_answers / max(1, model.hero.correct_answers + model.hero.wrong_answers))}%",
            f"Final Equipment: {model.hero.sword_name} & {model.hero.shield_name}",
        ]
        for i, line in enumerate(stats_lines):
            ls = self.font_md.render(line, True, (235, 240, 255))
            self.screen.blit(ls, (card.centerx - ls.get_width() // 2, card.y + 320 + i * 32))

        btn = pygame.Rect(card.centerx - 150, card.bottom - 68, 300, 48)
        self.clickable_rects["play_again"] = btn
        pygame.draw.rect(self.screen, (60, 165, 95), btn, border_radius=10)
        b_txt = self.font_lg.render("Play Again (Enter)", True, (255, 255, 255))
        self.screen.blit(
            b_txt, (btn.centerx - b_txt.get_width() // 2, btn.centery - b_txt.get_height() // 2)
        )

    def _render_game_over_screen(self, model: GameStateModel) -> None:
        pygame.draw.rect(self.screen, (36, 18, 28), pygame.Rect(0, 96, SCREEN_WIDTH, SCREEN_HEIGHT - 96))
        card = pygame.Rect(160, 180, SCREEN_WIDTH - 320, 400)
        pygame.draw.rect(self.screen, (48, 24, 38), card, border_radius=16)
        pygame.draw.rect(self.screen, (235, 95, 110), card, 3, border_radius=16)

        title = self.font_xxl.render("SHIELD OVERWHELMED...", True, (255, 120, 130))
        self.screen.blit(title, (card.centerx - title.get_width() // 2, card.y + 38))

        sub = self.font_md.render(
            "Don't give up! Every mistake trains your Least Common Multiple intuition.",
            True,
            (235, 215, 225),
        )
        self.screen.blit(sub, (card.centerx - sub.get_width() // 2, card.y + 110))

        retry_btn = pygame.Rect(card.centerx - 160, card.y + 210, 320, 52)
        self.clickable_rects["retry_zone"] = retry_btn
        pygame.draw.rect(self.screen, (65, 155, 95), retry_btn, border_radius=10)
        r_txt = self.font_lg.render("Retry Current Zone (Enter)", True, (255, 255, 255))
        self.screen.blit(
            r_txt,
            (retry_btn.centerx - r_txt.get_width() // 2, retry_btn.centery - r_txt.get_height() // 2),
        )

    # ------------------------------------------------------------------
    # Procedural Pixel / Vector Sprite Renderers
    # ------------------------------------------------------------------
    def _draw_hero_sprite(self, cx: int, cy: int, hero: HeroModel, scale: float = 1.0) -> None:
        """Draw the Hero with dynamic visuals reflecting Character Tier, Sword, and Shield."""
        s = scale
        # Cape unlocked at Tier >= 2
        if hero.tier >= 2:
            cape_colors = {
                2: (65, 125, 235),
                3: (155, 85, 235),
                4: (235, 195, 65),
                5: (255, 85, 95),
            }
            cape_col = cape_colors.get(hero.tier, (65, 125, 235))
            pygame.draw.polygon(
                self.screen,
                cape_col,
                [
                    (int(cx - 10 * s), int(cy - 22 * s)),
                    (int(cx - 24 * s), int(cy + 14 * s)),
                    (int(cx + 8 * s), int(cy + 14 * s)),
                ],
            )

        # Body tunic
        armor_col = (60, 130, 215) if hero.tier == 1 else (90, 165, 245)
        pygame.draw.rect(
            self.screen,
            armor_col,
            (int(cx - 12 * s), int(cy - 18 * s), int(24 * s), int(28 * s)),
            border_radius=int(5 * s),
        )

        # Head
        pygame.draw.circle(self.screen, (255, 220, 185), (cx, int(cy - 28 * s)), int(11 * s))
        # Eyes
        pygame.draw.circle(self.screen, (30, 35, 50), (int(cx + 4 * s), int(cy - 29 * s)), max(1, int(2 * s)))

        # Helmet / Crown based on Tier
        if hero.tier >= 4:
            pygame.draw.polygon(
                self.screen,
                (255, 215, 70),
                [
                    (int(cx - 11 * s), int(cy - 36 * s)),
                    (int(cx - 6 * s), int(cy - 45 * s)),
                    (cx, int(cy - 39 * s)),
                    (int(cx + 6 * s), int(cy - 45 * s)),
                    (int(cx + 11 * s), int(cy - 36 * s)),
                ],
            )
        else:
            pygame.draw.arc(
                self.screen,
                (190, 205, 230),
                (int(cx - 12 * s), int(cy - 41 * s), int(24 * s), int(18 * s)),
                0,
                math.pi,
                max(2, int(4 * s)),
            )

        # Shield Visuals (Left hand) — changes when Prime Number Shield is bought
        sh_x = int(cx - 16 * s)
        sh_y = int(cy - 6 * s)
        if hero.shield_level == 0:
            pygame.draw.circle(self.screen, (150, 110, 75), (sh_x, sh_y), int(9 * s))
            pygame.draw.circle(self.screen, (210, 175, 125), (sh_x, sh_y), int(9 * s), max(1, int(2 * s)))
        elif hero.shield_level == 1:
            # The Prime Number Shield (Emerald shield with golden rim)
            pygame.draw.polygon(
                self.screen,
                (45, 205, 125),
                [
                    (sh_x - int(10 * s), sh_y - int(10 * s)),
                    (sh_x + int(10 * s), sh_y - int(10 * s)),
                    (sh_x + int(8 * s), sh_y + int(4 * s)),
                    (sh_x, sh_y + int(13 * s)),
                    (sh_x - int(8 * s), sh_y + int(4 * s)),
                ],
            )
            pygame.draw.circle(self.screen, (255, 235, 110), (sh_x, sh_y - int(2 * s)), int(4 * s))
        else:
            # Aegis of Eratosthenes
            pygame.draw.circle(self.screen, (125, 235, 255), (sh_x, sh_y), int(12 * s))
            pygame.draw.circle(self.screen, (255, 225, 90), (sh_x, sh_y), int(12 * s), max(2, int(3 * s)))

        # Sword Visuals (Right hand) — changes with Multiplier Sword / Holy Sword
        sw_x = int(cx + 15 * s)
        sw_y = int(cy - 4 * s)
        if hero.sword_level == 0:
            blade_col = (185, 150, 105)
        elif hero.sword_level == 1:
            blade_col = (255, 215, 75)  # The Multiplier Sword
        elif hero.sword_level == 2:
            blade_col = (95, 240, 255)  # Arcane Multiplier Greatsword
        else:
            blade_col = (255, 250, 160)  # Legendary Holy Sword

        if hero.sword_level >= 1:
            # Glowing aura around upgraded Multiplier / Holy sword
            pygame.draw.line(
                self.screen,
                (255, 235, 120),
                (sw_x, sw_y),
                (int(sw_x + 16 * s), int(sw_y - 28 * s)),
                max(4, int(7 * s)),
            )
        pygame.draw.line(
            self.screen,
            blade_col,
            (sw_x, sw_y),
            (int(sw_x + 16 * s), int(sw_y - 28 * s)),
            max(2, int(4 * s)),
        )

    def _draw_monster_sprite(
        self, cx: int, cy: int, species: str, is_boss: bool = False, scale: float = 1.0
    ) -> None:
        s = scale * (1.22 if is_boss else 1.0)
        if species == "slime":
            col = (70, 215, 120) if not is_boss else (55, 235, 165)
            rect = pygame.Rect(int(cx - 22 * s), int(cy - 24 * s), int(44 * s), int(34 * s))
            pygame.draw.ellipse(self.screen, col, rect)
            pygame.draw.ellipse(self.screen, (220, 255, 230), rect, max(1, int(2 * s)))
        elif species == "bat":
            pygame.draw.polygon(
                self.screen,
                (135, 85, 195),
                [
                    (cx, int(cy - 12 * s)),
                    (int(cx - 32 * s), int(cy - 28 * s)),
                    (int(cx - 18 * s), int(cy + 4 * s)),
                ],
            )
            pygame.draw.polygon(
                self.screen,
                (135, 85, 195),
                [
                    (cx, int(cy - 12 * s)),
                    (int(cx + 32 * s), int(cy - 28 * s)),
                    (int(cx + 18 * s), int(cy + 4 * s)),
                ],
            )
            pygame.draw.circle(self.screen, (95, 55, 155), (cx, int(cy - 10 * s)), int(14 * s))
        elif species == "golem":
            rect = pygame.Rect(int(cx - 22 * s), int(cy - 34 * s), int(44 * s), int(44 * s))
            pygame.draw.rect(self.screen, (125, 145, 185), rect, border_radius=int(8 * s))
            pygame.draw.rect(self.screen, (195, 220, 255), rect, max(2, int(3 * s)), border_radius=int(8 * s))
        elif species == "knight":
            rect = pygame.Rect(int(cx - 20 * s), int(cy - 36 * s), int(40 * s), int(46 * s))
            pygame.draw.rect(self.screen, (175, 135, 85), rect, border_radius=int(6 * s))
            pygame.draw.polygon(
                self.screen,
                (235, 195, 110),
                [(int(cx - 14 * s), int(cy - 36 * s)), (int(cx + 14 * s), int(cy - 36 * s)), (cx, int(cy - 50 * s))],
            )
        else:
            # Demon King Malphas
            rect = pygame.Rect(int(cx - 26 * s), int(cy - 42 * s), int(52 * s), int(52 * s))
            pygame.draw.rect(self.screen, (165, 35, 55), rect, border_radius=int(10 * s))
            # Horns
            pygame.draw.polygon(
                self.screen,
                (255, 215, 80),
                [(int(cx - 20 * s), int(cy - 40 * s)), (int(cx - 32 * s), int(cy - 62 * s)), (int(cx - 8 * s), int(cy - 42 * s))],
            )
            pygame.draw.polygon(
                self.screen,
                (255, 215, 80),
                [(int(cx + 20 * s), int(cy - 40 * s)), (int(cx + 32 * s), int(cy - 62 * s)), (int(cx + 8 * s), int(cy - 42 * s))],
            )

        # Eyes
        pygame.draw.circle(self.screen, (255, 240, 90), (int(cx - 8 * s), int(cy - 14 * s)), max(2, int(4 * s)))
        pygame.draw.circle(self.screen, (255, 240, 90), (int(cx + 8 * s), int(cy - 14 * s)), max(2, int(4 * s)))

    def _draw_shield_badge(
        self, cx: int, cy: int, numbers: Tuple[int, ...], pulse: bool = False
    ) -> None:
        """Draw the Monster's Mathematical Shield above its head containing 2 or 3 numbers."""
        offset_y = int(math.sin(self.anim_time * 3.5) * 4) if pulse else 0
        sy = cy + offset_y
        w = 136 if len(numbers) == 2 else 172
        h = 64

        pts = [
            (cx - w // 2, sy - h // 2),
            (cx + w // 2, sy - h // 2),
            (cx + w // 2 - 8, sy + 10),
            (cx, sy + h // 2 + 12),
            (cx - w // 2 + 8, sy + 10),
        ]
        pygame.draw.polygon(self.screen, (34, 62, 118), pts)
        pygame.draw.polygon(self.screen, (120, 215, 255), pts, 3)

        tag = self.font_xs.render("MATH SHIELD", True, (185, 235, 255))
        self.screen.blit(tag, (cx - tag.get_width() // 2, sy - h // 2 + 5))

        nums_str = "[" + ", ".join(str(n) for n in numbers) + "]"
        n_surf = self.font_xl.render(nums_str, True, (255, 240, 110))
        self.screen.blit(n_surf, (cx - n_surf.get_width() // 2, sy - 8))

    def _draw_mini_map_shield(self, cx: int, cy: int, numbers: Tuple[int, ...]) -> None:
        nums_str = "[" + ",".join(str(n) for n in numbers) + "]"
        surf = self.font_xs.render(nums_str, True, (255, 245, 130))
        pad_rect = pygame.Rect(
            cx - surf.get_width() // 2 - 5, cy - 10, surf.get_width() + 10, 20
        )
        pygame.draw.rect(self.screen, (25, 42, 82), pad_rect, border_radius=5)
        pygame.draw.rect(self.screen, (130, 210, 255), pad_rect, 1, border_radius=5)
        self.screen.blit(surf, (cx - surf.get_width() // 2, cy - 8))

    def _draw_fairy_sprite(self, cx: int, cy: int) -> None:
        wing_flap = int(math.sin(self.anim_time * 8.0) * 5)
        pygame.draw.ellipse(
            self.screen, (210, 235, 255), (cx - 34, cy - 22 + wing_flap, 28, 18)
        )
        pygame.draw.ellipse(
            self.screen, (210, 235, 255), (cx + 6, cy - 22 + wing_flap, 28, 18)
        )
        pygame.draw.circle(self.screen, (255, 185, 245), (cx, cy), 16)
        pygame.draw.circle(self.screen, (255, 240, 150), (cx, cy - 18), 10)
        # Magic wand
        pygame.draw.line(self.screen, (255, 230, 110), (cx + 12, cy + 4), (cx + 28, cy - 16), 3)
        pygame.draw.circle(self.screen, (255, 250, 140), (cx + 28, cy - 16), 5)

    def _draw_princess_sprite(self, cx: int, cy: int) -> None:
        # Gown
        pygame.draw.polygon(
            self.screen,
            (245, 135, 195),
            [(cx, cy - 18), (cx - 22, cy + 22), (cx + 22, cy + 22)],
        )
        # Head
        pygame.draw.circle(self.screen, (255, 225, 195), (cx, cy - 24), 11)
        # Crown
        self._draw_mini_crown_icon(cx, cy - 38)

    def _draw_shop_tile(self, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, (125, 85, 52), rect.inflate(-6, -6), border_radius=4)
        pygame.draw.polygon(
            self.screen,
            (215, 75, 65),
            [(rect.x + 2, rect.y + 16), (rect.right - 2, rect.y + 16), (rect.centerx, rect.y + 3)],
        )
        lbl = self.font_xs.render("SHOP", True, (255, 240, 150))
        self.screen.blit(lbl, (rect.centerx - lbl.get_width() // 2, rect.bottom - 18))

    def _draw_sign_tile(self, rect: pygame.Rect) -> None:
        pygame.draw.rect(self.screen, (130, 95, 55), (rect.centerx - 3, rect.centery, 6, 18))
        board = pygame.Rect(rect.x + 10, rect.y + 10, rect.width - 20, 20)
        pygame.draw.rect(self.screen, (195, 155, 95), board, border_radius=3)
        lbl = self.font_xs.render("?", True, (45, 30, 15))
        self.screen.blit(lbl, (board.centerx - lbl.get_width() // 2, board.y + 1))

    def _draw_portal_tile(self, rect: pygame.Rect, unlocked: bool) -> None:
        col = (95, 235, 195) if unlocked else (120, 110, 135)
        pygame.draw.ellipse(self.screen, col, rect.inflate(-8, -4), 4)
        lbl = self.font_xs.render("GATE" if unlocked else "LOCK", True, col)
        self.screen.blit(lbl, (rect.centerx - lbl.get_width() // 2, rect.centery - 7))

    def _draw_mini_sword_icon(self, cx: int, cy: int) -> None:
        pygame.draw.line(self.screen, (220, 235, 255), (cx - 6, cy + 6), (cx + 6, cy - 6), 3)
        pygame.draw.line(self.screen, (255, 205, 80), (cx - 5, cy + 1), (cx - 1, cy + 5), 3)

    def _draw_mini_crown_icon(self, cx: int, cy: int) -> None:
        pygame.draw.polygon(
            self.screen,
            (255, 215, 70),
            [
                (cx - 9, cy + 5),
                (cx - 9, cy - 4),
                (cx - 4, cy + 1),
                (cx, cy - 6),
                (cx + 4, cy + 1),
                (cx + 9, cy - 4),
                (cx + 9, cy + 5),
            ],
        )

    def _draw_wrapped_text(
        self,
        text: str,
        font: pygame.font.Font,
        color: Tuple[int, int, int],
        rect: pygame.Rect,
    ) -> None:
        words = text.split(" ")
        lines: List[str] = []
        current = ""
        for w in words:
            test = f"{current} {w}".strip()
            if font.size(test)[0] <= rect.width:
                current = test
            else:
                if current:
                    lines.append(current)
                current = w
        if current:
            lines.append(current)

        for i, line in enumerate(lines[:2]):
            surf = font.render(line, True, color)
            self.screen.blit(surf, (rect.x, rect.y + i * (font.get_linesize() + 2)))

    def _render_particles(self) -> None:
        for p in self.particles:
            pygame.draw.circle(
                self.screen, p.color, (int(p.x), int(p.y)), max(1, int(p.size))
            )
