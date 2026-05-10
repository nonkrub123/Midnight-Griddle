import pygame

# ── Screen / game surface ─────────────────────────────────────────────────────

SCREEN_W, SCREEN_H = 1920, 1080

# ── Scale helpers ─────────────────────────────────────────────────────────────

def sw(ratio: float) -> int:
    """Fraction of screen width."""
    return int(SCREEN_W * ratio)

def sh(ratio: float) -> int:
    """Fraction of screen height."""
    return int(SCREEN_H * ratio)

# ── Order panel (right side) ──────────────────────────────────────────────────

ORDER_PANEL_X  = sw(0.833)          # ~1600 at 1920
ORDER_PANEL_Y  = 0
ORDER_PANEL_W  = SCREEN_W - ORDER_PANEL_X
ORDER_ROW_H    = sh(0.074)          # ~80  at 1080
ORDER_TOP_H    = sh(0.259)          # ~280 at 1080
ORDER_FOOTER_H = sh(0.065)          # ~70  at 1080
ORDER_ROWS     = 10

# ── HUD bar ───────────────────────────────────────────────────────────────────

HUD_BAR_W = ORDER_PANEL_X
HUD_BAR_H = sh(0.052)               # ~56 at 1080

# ── Accept and Submit Button  ───────────────────────────────────────────────────────────────────

BTN_W = sw(0.167)   # ~320px at 1920
BTN_H = sh(0.074)   # ~80px  at 1080
# ── Station positions ─────────────────────────────────────────────────────────

POS_PLATE = (925, 700)
POS_GRILL = (500, 500)
POS_TRAY  = (220, 800)

POS_DISPENSER = {
    "meat":     (250,  600),
    "lettuce":  (1450, 480),
    "tomato":   (1458, 304),
    "onion":    (1439, 726),
    "pickle":   (50,   580),
    "down_bun": (1470, 890),
    "top_bun":  (1457, 159),
    "cheese":   (1459, 610),
}

POS_ORDER_CUSTOMER  = (860,  500)
POS_ORDER_ACCEPT    = (730,  324)
ORDER_CUSTOMER_SIZE = (120,  120)

POS_GRILL_LIST = [
    # Row 1 (Anchor)
    (676, 274), (1000, 274), (1325, 274),
    # Row 2 (y - 2)
    (676, 433), (1000, 433), (1325, 433),
    # Row 3 (y - 4)
    (676, 592), (1000, 592), (1325, 592),
    # Row 4 (y - 6)
    (676, 751), (1000, 751), (1325, 751),
]

POS_TRASH      = (250,  400)
POS_SUBMIT_BTN = (749,  820)
POS_FEEDBACK   = (800,  680)

POS_ORDER_SUMMARY  = (20,  80)
ORDER_SUMMARY_W    = 260
ORDER_SUMMARY_ROWS = 8

POS_RESTOCK     = (40,   80)
RESTOCK_W       = 600
RESTOCK_ROW_H   = 100
RESTOCK_TITLE_H = 60
RESTOCK_BTN_W   = 130
RESTOCK_BTN_H   = 56

POS_NAV = {
    "order":    (0,    980),
    "grill":    (480,  980),
    "assemble": (960,  980),
    "restock":  (1440, 980),
}

# ── Palette ───────────────────────────────────────────────────────────────────

C_BG       = (35,  30,  25)
C_BG_ALPHA = (20,  18,  15, 200)
C_BORDER   = (90,  75,  50)

C_TEXT    = (230, 215, 180)
C_SUBTEXT = (140, 125,  95)
C_TITLE   = (180, 155, 100)

C_BAR_BG   = (55,  50,  40)
C_BAR_OK   = (80,  200,  80)
C_BAR_WARN = (220, 175,  40)
C_BAR_LOW  = (220,  55,  40)

C_BTN        = (70,  45,  15)
C_BTN_TEXT   = (255, 215, 100)
C_BTN_ACCEPT = (60,  120,  60)
C_BTN_SUBMIT = (30,   80, 160)
C_BTN_LABEL  = (220, 255, 200)

C_GOLD  = (255, 210,  60)
C_GREEN = (100, 220, 100)

C_FLASH_OK   = (60,  180,  60)
C_FLASH_WARN = (200,  60,  60)

C_GAME_BG = (30, 30, 30)

# ── Fonts ─────────────────────────────────────────────────────────────────────

FONT_FAMILY = "serif"

_FONT_BASE = sh(0.024)  

def font(size: int = 20, bold: bool = False):
    pygame.font.init()
    scaled = int(size * (_FONT_BASE / 20))
    return pygame.font.SysFont(FONT_FAMILY, max(scaled, 10), bold=bold)

# ── Button surface builder ────────────────────────────────────────────────────

def button_surface(label: str,
                   w: int  = None,
                   h: int  = None,
                   color      = None,
                   text_color = None,
                   font_size: int  = 22,
                   bold: bool = True) -> pygame.Surface:
    if w          is None: w          = sw(0.104)   # ~200px at 1920
    if h          is None: h          = sh(0.056)   # ~60px  at 1080
    if color      is None: color      = C_BTN_ACCEPT
    if text_color is None: text_color = C_BTN_LABEL

    s = pygame.Surface((w, h))
    s.fill(color)
    pygame.draw.rect(s, C_BORDER, s.get_rect(), 2)
    txt = font(font_size, bold=bold).render(label, True, text_color)
    s.blit(txt, txt.get_rect(center=(w // 2, h // 2)))
    return s