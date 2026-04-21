from ui.interactive import StaticUI, UIButton
from ui.group import BaseGroup
import ui.theme as theme
from core.stat_viewer import show_stat
import pygame
from core.settings import *

class MenuScreen(BaseGroup):
    """Simple centered panel with a title and a vertical list of buttons."""

    def __init__(self, title, buttons):
        """buttons = [(label, callback), ...]"""
        super().__init__()

        # Dim backdrop
        bg = pygame.Surface((GAME_W, GAME_H), pygame.SRCALPHA)
        bg.fill((0, 0, 0, 180))
        self.add(StaticUI(bg, (0, 0), layer=1))

        # Title
        title_surf = theme.font(48, bold=True).render(title, True, theme.C_TITLE)
        self.add(StaticUI(title_surf, (GAME_W // 2, 280),
                          layer=2, anchor="center"))

        # Buttons stacked vertically
        btn_w, btn_h, gap = 360, 60, 20
        start_y = 400
        for i, (label, cb) in enumerate(buttons):
            y = start_y + i * (btn_h + gap)
            self.add(UIButton(
                f"menu_{label}",
                theme.button_surface(label, w=btn_w, h=btn_h),
                (GAME_W // 2, y),
                cb,
                anchor="center", layer=3,
            ))