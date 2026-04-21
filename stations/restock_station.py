"""
restockstation.py
─────────────────
Shop panel. One row per edible item — icon, name, stock, price, BUY button.
Clicking BUY buys one unit via GameData.restock().
"""

import pygame
from ui.group import BaseGroup
from ui.interactive import StaticUI, UIButton
from core.itemdata import ItemData
from stations.station import Station
from core.gamedata import GameData
import ui.theme as theme


def _make_panel(w, h):
    s = pygame.Surface((w, h))
    s.fill(theme.C_BG)
    pygame.draw.rect(s, theme.C_BORDER, s.get_rect(), 2)
    return s


def _make_title(w):
    s = pygame.Surface((w, theme.RESTOCK_TITLE_H), pygame.SRCALPHA)
    pygame.draw.rect(s, theme.C_BG, s.get_rect())
    pygame.draw.line(s, theme.C_BORDER,
                     (0, theme.RESTOCK_TITLE_H - 1),
                     (w, theme.RESTOCK_TITLE_H - 1), 1)
    txt = theme.font(20, bold=True).render("RESTOCK", True, theme.C_TITLE)
    s.blit(txt, txt.get_rect(center=(w // 2, theme.RESTOCK_TITLE_H // 2)))
    return s


def _make_row(item_id, stock, w):
    s = pygame.Surface((w, theme.RESTOCK_ROW_H), pygame.SRCALPHA)
    pygame.draw.rect(s, theme.C_BG, s.get_rect())
    pygame.draw.line(s, theme.C_BORDER,
                     (0, theme.RESTOCK_ROW_H - 1),
                     (w, theme.RESTOCK_ROW_H - 1), 1)

    # Icon
    data = ItemData.get_item(item_id)
    if data:
        img_name = data["state_imgs"].get("default",
                        next(iter(data["state_imgs"].values())))
        img      = ItemData.load_img(img_name, data["type"])
        img      = pygame.transform.smoothscale(img, (48, 48))
        s.blit(img, (12, (theme.RESTOCK_ROW_H - 48) // 2))

    # Name + stock/price
    name  = ItemData.get_prop(item_id, "display_name", item_id)
    price = ItemData.get_prop(item_id, "buy_price", 0)
    s.blit(theme.font(17, bold=True).render(name, True, theme.C_TEXT), (72, 10))
    s.blit(theme.font(14).render(f"x {stock}      ${price}", True, theme.C_SUBTEXT),
           (72, 36))
    return s


# ── RestockStation ────────────────────────────────────────────────────────────

class RestockStation(Station):
    def __init__(self, screen, bg_image_path, gamedata: GameData):
        super().__init__(screen, bg_image_path)

        self._gamedata = gamedata
        self._group    = BaseGroup()
        self._rows     = {}

        ox, oy  = theme.POS_RESTOCK
        w       = theme.RESTOCK_W
        row_h   = theme.RESTOCK_ROW_H
        title_h = theme.RESTOCK_TITLE_H
        items   = ItemData.get_all_edible()
        panel_h = title_h + row_h * len(items) + 16

        self._group.add(StaticUI(_make_panel(w, panel_h), (ox, oy), layer=1))
        self._group.add(StaticUI(_make_title(w),          (ox, oy), layer=2))

        for i, item_id in enumerate(items):
            row_y = oy + title_h + i * row_h

            row = StaticUI(_make_row(item_id, gamedata.get_stock(item_id), w),
                           (ox, row_y), layer=2)
            self._rows[item_id] = row
            self._group.add(row)

            self._group.add(UIButton(
                f"buy_{item_id}",
                theme.button_surface("BUY",
                                     w=theme.RESTOCK_BTN_W,
                                     h=theme.RESTOCK_BTN_H,
                                     color=theme.C_BTN_ACCEPT,
                                     font_size=16),
                (ox + w - theme.RESTOCK_BTN_W - 12,
                 row_y + (row_h - theme.RESTOCK_BTN_H) // 2),
                lambda iid=item_id: self._buy(iid),
                anchor="topleft", layer=3,
            ))

        self.register_group(self._group)

    def _buy(self, item_id):
        if self._gamedata.restock(item_id, 1):
            self._gamedata.save()
        self._rows[item_id].set_surface(
            _make_row(item_id, self._gamedata.get_stock(item_id), theme.RESTOCK_W)
        )