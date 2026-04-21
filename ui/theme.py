"""
theme.py
────────
Single source of truth for UI layout, colours, and fonts.

Every magic number that used to be scattered across orderui.py / hud.py /
station.py lives here. Move the order panel by changing ORDER_PANEL_X — the
HUD bar auto-shortens, the nav label re-centers, the patience bar re-sizes.
Swap FONT_FAMILY once and the whole game restyles.
"""

import pygame


# ── Screen / game surface ─────────────────────────────────────────────────────

SCREEN_W, SCREEN_H = 1920, 1080


# ── Order panel (right side) ──────────────────────────────────────────────────

ORDER_PANEL_X  = 1600
ORDER_PANEL_Y  = 0
ORDER_PANEL_W  = SCREEN_W - ORDER_PANEL_X   # fills to screen edge automatically
ORDER_ROW_H    = 64
ORDER_TOP_H    = 220                        # avatar + nav + patience bar
ORDER_FOOTER_H = 56                         # finish button
ORDER_ROWS     = 10


# ── HUD bar (top, stops where the order panel starts) ────────────────────────

HUD_BAR_W = ORDER_PANEL_X
HUD_BAR_H = 56


# ── Station positions ─────────────────────────────────────────────────────────

POS_PLATE = (800, 550)
POS_GRILL = (500, 500)
POS_TRAY  = (250, 800)

# POS_DISPENSER = {
#     "meat":     (250, 400),
#     "down_bun": (350, 300),
#     "top_bun":  (550, 300),
#     "cheese":   (750, 300),
# }

POS_DISPENSER = {
    "meat":     (250, 600),
    "lettuce": (1450.0, 480.0),
    "tomato":  (1457.5, 303.75),
    "onion":   (1438.75, 726.25),
    "pickle":  (50, 580),

    "down_bun": (1470.0, 890.0),
    "top_bun":  (1457, 159), # Moving buns to a bottom row or side-by-side
    "cheese":   (1458.75, 610.0),
}

# Order station
POS_ORDER_CUSTOMER  = (860, 500)
POS_ORDER_ACCEPT    = (860, 700)
ORDER_CUSTOMER_SIZE = (120, 120)

# Grill station
POS_GRILL_LIST = [
            (557, 267), (887, 267), (1217, 267), # Row 1
            (557, 422), (887, 422), (1217, 422), # Row 2
            (557, 577), (887, 577), (1217, 577), # Row 3
            (557, 732), (887, 732), (1217, 732)  # Row 4
        ]
POS_TRASH = (250, 400)
# Assemble station
POS_SUBMIT_BTN = (800, 820)
POS_FEEDBACK   = (800, 680)

# Order summary panel (left side of assemble station)
POS_ORDER_SUMMARY  = (20, 80)
ORDER_SUMMARY_W    = 260
ORDER_SUMMARY_ROWS = 8

# Restock panel
POS_RESTOCK      = (40, 80)
RESTOCK_W        = 420
RESTOCK_ROW_H    = 72
RESTOCK_TITLE_H  = 44
RESTOCK_BTN_W    = 90
RESTOCK_BTN_H    = 40

# Nav buttons (bottom-left)
POS_NAV = {
    "order":    (0, 980),
    "grill":    (440, 980),
    "assemble": (960, 980),
    "restock":  (1410, 980),
}


# ── Palette ───────────────────────────────────────────────────────────────────

# Panels / backgrounds
C_BG       = (35,  30,  25)
C_BG_ALPHA = (20,  18,  15, 200)    # semi-transparent HUD background
C_BORDER   = (90,  75,  50)

# Text
C_TEXT     = (230, 215, 180)
C_SUBTEXT  = (140, 125,  95)
C_TITLE    = (180, 155, 100)

# Patience / progress bar
C_BAR_BG   = (55,  50,  40)
C_BAR_OK   = (80,  200,  80)
C_BAR_WARN = (220, 175,  40)
C_BAR_LOW  = (220,  55,  40)

# Buttons
C_BTN        = (70,  45,  15)
C_BTN_TEXT   = (255, 215, 100)
C_BTN_ACCEPT = (60,  120,  60)
C_BTN_SUBMIT = (30,   80, 160)
C_BTN_LABEL  = (220, 255, 200)

# HUD accents
C_GOLD  = (255, 210,  60)
C_GREEN = (100, 220, 100)

# Feedback flashes
C_FLASH_OK   = (60,  180,  60)
C_FLASH_WARN = (200,  60,  60)

# Game background
C_GAME_BG = (30, 30, 30)


# ── Fonts ─────────────────────────────────────────────────────────────────────

FONT_FAMILY = "serif"

def font(size: int = 16, bold: bool = False):
    """Centralized font accessor. Change FONT_FAMILY once, whole UI updates."""
    pygame.font.init()
    return pygame.font.SysFont(FONT_FAMILY, size, bold=bold)


# ── Button surface builder ────────────────────────────────────────────────────

def button_surface(label: str,
                   w: int = 200,
                   h: int = 60,
                   color=None,
                   text_color=None,
                   font_size: int = 18,
                   bold: bool = True) -> pygame.Surface:
    """
    Canonical button surface — flat fill, bordered, centered label.
    Used by ACCEPT/SUBMIT/FINISH/etc. so every button has consistent styling.

    Defaults to the "accept" green with the light-label text; override `color`
    and `text_color` for other variants (e.g. C_BTN_SUBMIT, C_BTN + C_BTN_TEXT).
    """
    if color      is None: color      = C_BTN_ACCEPT
    if text_color is None: text_color = C_BTN_LABEL

    s = pygame.Surface((w, h))
    s.fill(color)
    pygame.draw.rect(s, C_BORDER, s.get_rect(), 2)
    txt = font(font_size, bold=bold).render(label, True, text_color)
    s.blit(txt, txt.get_rect(center=(w // 2, h // 2)))
    return s