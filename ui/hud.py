"""
hud.py
──────
HUDGroup : Always-visible top bar showing clock, money, and average rating.
StationManager owns it and draws it last so it sits above everything.

Layout  (across top of screen, stops before OrderUI panel)
──────────────────────────────────────────────────────────
  ┌────────────────────────────────────────────────┐
  │  🕐  Hour: 2.5          $  150       ★  3.8   │
  └────────────────────────────────────────────────┘
"""

import pygame
from ui.group import BaseGroup
from ui.interactive import StaticUI
import ui.theme as theme


# ── Surface builders ──────────────────────────────────────────────────────────

def _make_bg():
    surf = pygame.Surface((theme.HUD_BAR_W, theme.HUD_BAR_H), pygame.SRCALPHA)
    surf.fill(theme.C_BG_ALPHA)
    pygame.draw.line(surf, theme.C_BORDER,
                     (0, theme.HUD_BAR_H - 1),
                     (theme.HUD_BAR_W, theme.HUD_BAR_H - 1), 2)
    return surf

def _make_clock(label: str) -> pygame.Surface:
    return theme.font(22, bold=True).render(f"Hour  {label}", True, theme.C_TEXT)

def _make_money(amount: int) -> pygame.Surface:
    return theme.font(22, bold=True).render(f"$  {amount}", True, theme.C_GREEN)

def _make_rating(avg: float) -> pygame.Surface:
    filled = int(avg + 0.5)
    stars  = "*" * filled + "-" * (5 - filled)
    return theme.font(22, bold=True).render(f"{stars}  {avg:.1f}", True, theme.C_GOLD)


# ── HUDGroup ──────────────────────────────────────────────────────────────────

class HUDGroup(BaseGroup):
    """
    Register once in StationManager.
    Call refresh(game_hour, gamedata) every frame.
    """

    def __init__(self):
        super().__init__()

        cy = theme.HUD_BAR_H // 2

        # Background bar (topleft at 0,0 — full width)
        self.add(StaticUI(_make_bg(), (0, 0), layer=9, name="hud_bg"))

        # Three display sprites — centered at 1/6, 3/6, 5/6 of the bar
        self._clock  = StaticUI(_make_clock("0"),
                                (theme.HUD_BAR_W * 1 // 6, cy),
                                layer=10, anchor="center", name="hud_clock")
        self._money  = StaticUI(_make_money(0),
                                (theme.HUD_BAR_W * 3 // 6, cy),
                                layer=10, anchor="center", name="hud_money")
        self._rating = StaticUI(_make_rating(0.0),
                                (theme.HUD_BAR_W * 5 // 6, cy),
                                layer=10, anchor="center", name="hud_rating")
        self.add(self._clock, self._money, self._rating)

    def refresh(self, game_hour, gamedata):
        self._clock.set_surface (_make_clock(game_hour.hour_label))
        self._money.set_surface (_make_money(gamedata.money))
        self._rating.set_surface(_make_rating(gamedata.average_rating))

    # HUD never participates in drag/drop
    def handle_click(self, sprite): pass
    def handle_drag(self, sprite, pos): pass
    def handle_drop(self, sprite, target): return False
    def handle_snapback(self, sprite): pass