"""
orderui.py
──────────
OrderUI extends BaseGroup so it plugs straight into the existing render pipeline.
Every element is either a StaticUI (locked display) or a UIButton (clickable).

State model
───────────
The OrderUI keeps **no list of its own**. It reads directly from
`customer_manager.on_waiting` every frame. Accept/timeout/submit all happen
on CustomerManager; the UI renders whatever the manager currently says is
waiting. This means the two literally cannot desync.

Navigation state is tracked by customer identity (not by index), so the
current selection survives list mutations — e.g. someone three slots ahead
timing out won't jump your view to a different order.

Accept flow
───────────
    station calls customer_manager.take_order()
    → UI picks up the new waiting customer automatically on the next frame

Submit flow
───────────
    entry = order_ui.pop_current()   # internally calls finish_order(customer)
    → uses identity matching, so the correct customer is removed
      regardless of which index is currently shown

Timeout flow
────────────
    CustomerManager.update_waiting(dt) evicts expired customers
    → UI picks up the shorter list automatically on the next frame
"""

from __future__ import annotations
import pygame
from ui.group import BaseGroup
from core.itemdata import ItemData
from ui.interactive import StaticUI, UIButton
import ui.theme as theme


# ── Constants pulled from theme ───────────────────────────────────────────────

PANEL_W  = theme.ORDER_PANEL_W
ROW_H    = theme.ORDER_ROW_H
TOP_H    = theme.ORDER_TOP_H
FOOTER_H = theme.ORDER_FOOTER_H


# ── Surface builders (domain-specific) ────────────────────────────────────────

def _make_panel(w: int, h: int) -> pygame.Surface:
    s = pygame.Surface((w, h))
    s.fill(theme.C_BG)
    pygame.draw.rect(s, theme.C_BORDER, s.get_rect(), 2)
    return s


def _make_avatar(image: pygame.Surface, size=(80, 80)) -> pygame.Surface:
    s   = pygame.transform.smoothscale(image, size)
    out = pygame.Surface(size, pygame.SRCALPHA)
    out.blit(s, (0, 0))
    pygame.draw.circle(out, theme.C_BORDER, (size[0]//2, size[1]//2), size[0]//2, 3)
    return out


def _make_nav_label(index: int, total: int, w: int) -> pygame.Surface:
    s   = pygame.Surface((w, 40), pygame.SRCALPHA)
    txt = theme.font(20, bold=True).render(f"{index+1}  /  {total}", True, theme.C_TEXT)
    s.blit(txt, txt.get_rect(center=(w//2, 20)))
    return s


def _make_arrow(direction: int, active: bool) -> pygame.Surface:
    """direction: -1=left, +1=right"""
    s   = pygame.Surface((40, 40), pygame.SRCALPHA)
    col = theme.C_TEXT if active else theme.C_SUBTEXT
    pts = [(32, 8), (8, 20), (32, 32)] if direction == -1 else [(8, 8), (32, 20), (8, 32)]
    pygame.draw.polygon(s, col, pts)
    return s


def _make_patience_bar(ratio: float, w: int, phase: str, secs: int) -> pygame.Surface:
    h = 40
    s = pygame.Surface((w, h), pygame.SRCALPHA)
    if   ratio > 0.5:  col = theme.C_BAR_OK
    elif ratio > 0.25: col = theme.C_BAR_WARN
    else:              col = theme.C_BAR_LOW

    bx, by, bw, bh = 0, 20, w, 14
    pygame.draw.rect(s, theme.C_BAR_BG, (bx, by, bw, bh), border_radius=6)
    fill = max(0, int(bw * ratio))
    if fill:
        pygame.draw.rect(s, col, (bx, by, fill, bh), border_radius=6)
    pygame.draw.rect(s, theme.C_BORDER, (bx, by, bw, bh), 1, border_radius=6)
    label = theme.font(13).render(f"{phase}  {secs}s", True, theme.C_SUBTEXT)
    s.blit(label, (0, 2))
    return s


def _make_row(item_id: str | None, w: int) -> pygame.Surface:
    s = pygame.Surface((w, ROW_H), pygame.SRCALPHA)
    if item_id is None:
        return s
    data = ItemData.get_item(item_id)
    if data:
        img_name  = data["state_imgs"].get("default", next(iter(data["state_imgs"].values())))
        item_surf = ItemData.load_img(img_name, data["type"])
        item_surf = pygame.transform.smoothscale(item_surf, (48, 48))
        s.blit(item_surf, (10, (ROW_H - 48) // 2))
    name = ItemData.get_prop(item_id, "display_name", item_id)
    txt  = theme.font(16).render(name, True, theme.C_TEXT)
    s.blit(txt, (68, (ROW_H - txt.get_height()) // 2))
    return s


# ── _OrderEntry ───────────────────────────────────────────────────────────────

class _OrderEntry:
    """
    Thin view onto a Customer — the UI creates these on demand when it needs
    to hand something off to a station (e.g. AssembleStation._submit). All
    mutable state lives on the Customer itself.
    """

    def __init__(self, customer):
        self.customer = customer

    @property
    def image(self):
        return self.customer.image

    @property
    def items(self) -> list[str]:
        return self.customer.order

    @property
    def ordering_ratio(self) -> float:
        """Snapshot captured by CustomerManager.take_order() at accept-time."""
        return getattr(self.customer, "ordering_ratio_at_accept", 0.0) or 0.0

    @property
    def ratio(self) -> float:
        c = self.customer
        if c.phase == "ordering":
            return c.ordering_ratio
        return c.waiting_ratio

    @property
    def secs(self) -> int:
        c = self.customer
        return int(c.patience_ordering if c.phase == "ordering" else c.patience_waiting)

    @property
    def phase(self) -> str:
        return "Ordering" if self.customer.phase == "ordering" else "Waiting"


# ── OrderUI ───────────────────────────────────────────────────────────────────

class OrderUI(BaseGroup):
    """
    A BaseGroup whose sprites represent every element of the order panel.
    Register it with your station and it renders automatically.

    Parameters default to theme values — pass explicit ones to override.
    """

    def __init__(self,
                 customer_manager,
                 x: int | None = None,
                 y: int | None = None,
                 rows: int | None = None):
        super().__init__()
        self._cm    = customer_manager
        self._ox    = theme.ORDER_PANEL_X if x    is None else x
        self._oy    = theme.ORDER_PANEL_Y if y    is None else y
        self._rows  = theme.ORDER_ROWS    if rows is None else rows

        # Navigation is tracked by customer identity, not by index.
        # This makes selection survive list mutations (timeouts, submits
        # from other stations, etc.).
        self._current_customer     = None
        self._last_customer_ids    = []   # sentinel: detect list changes frame-to-frame
        self._last_phase           = None

        panel_h = TOP_H + self._rows * ROW_H + FOOTER_H
        blank   = pygame.Surface((1, 1), pygame.SRCALPHA)

        # ── Static background ─────────────────────────────────────────────────
        self._bg = StaticUI(_make_panel(PANEL_W, panel_h),
                            (self._ox, self._oy), layer=1, name="order_bg")
        self.add(self._bg)

        # ── Row dividers (static) ─────────────────────────────────────────────
        for i in range(self._rows):
            surf = pygame.Surface((PANEL_W, 1))
            surf.fill(theme.C_BORDER)
            ry   = self._oy + TOP_H + i * ROW_H
            self.add(StaticUI(surf, (self._ox, ry), layer=1, name="divider"))

        # ── Dynamic display slots (swapped on _refresh / update_ui) ───────────
        cx = self._ox + PANEL_W // 2

        # Nav label uses topleft so its rect aligns with the panel left edge
        self._nav_lbl = StaticUI(blank, (self._ox, self._oy + 8),
                                 layer=3, name="nav_lbl")
        # Avatar is centered at a point within the header
        self._avatar  = StaticUI(blank, (cx, self._oy + 110),
                                 layer=3, anchor="center", name="avatar")
        # Patience bar sits in a known topleft slot just above the rows
        self._pat_bar = StaticUI(blank, (self._ox + 16, self._oy + TOP_H - 46),
                                 layer=3, name="patience_bar")
        self.add(self._nav_lbl, self._avatar, self._pat_bar)

        # ── Row sprites ────────────────────────────────────────────────────────
        self._row_sprs: list[StaticUI] = []
        for i in range(self._rows):
            spr = StaticUI(pygame.Surface((PANEL_W, ROW_H), pygame.SRCALPHA),
                           (self._ox, self._oy + TOP_H + i * ROW_H),
                           layer=3, name=f"row_{i}")
            self._row_sprs.append(spr)
            self.add(spr)

        # ── Buttons (all topleft-anchored inside the panel) ──────────────────
        self._btn_left = UIButton(
            "order_nav_left",  _make_arrow(-1, False),
            (self._ox + 10, self._oy + 8),
            self._go_left, anchor="topleft", layer=4,
        )
        self._btn_right = UIButton(
            "order_nav_right", _make_arrow(+1, False),
            (self._ox + PANEL_W - 50, self._oy + 8),
            self._go_right, anchor="topleft", layer=4,
        )
        self.add(self._btn_left, self._btn_right)

        self._refresh()

    # ── Internal: single source of truth ──────────────────────────────────────

    @property
    def _customers(self) -> list:
        """Live view of the manager's waiting queue."""
        return self._cm.on_waiting

    # ── Public API ────────────────────────────────────────────────────────────

    def is_empty(self) -> bool:
        return not self._customers

    def peek_current(self):
        """Read current order without removing it (returns _OrderEntry or None)."""
        customers = self._customers
        if not customers:
            self._current_customer = None
            return None
        # Repair selection if the currently-shown customer is gone (e.g. timeout).
        if self._current_customer not in customers:
            self._current_customer = customers[0]
        return _OrderEntry(self._current_customer)

    def pop_current(self):
        """
        Finish the current order — removes from CustomerManager by identity.
        Returns the _OrderEntry (for stats), or None if nothing is shown.

        Identity-matched removal fixes the old FIFO desync: whichever order
        the player is viewing is the one that gets finished.
        """
        entry = self.peek_current()
        if entry is None:
            return None
        self._cm.finish_order(entry.customer)
        # _refresh will run on the next update_ui via the list-change check,
        # but do it immediately so the UI is consistent within this frame.
        self._current_customer = None
        self._refresh()
        return entry

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt=0):
        # Deliberately empty — stations each call group.update and we don't
        # want the display ticked N times. StationManager calls update_ui.
        pass

    def update_ui(self, dt):
        """
        Call exactly once per frame from StationManager.

        Detects three kinds of change:
          1. List mutation (accept / submit / timeout) → full refresh.
          2. Phase flip on the currently-shown order   → full refresh.
          3. Normal tick                                → patience bar only.
        """
        customers = self._customers
        cur_ids   = [id(c) for c in customers]

        # (1) List changed — accept / submit / timeout
        if cur_ids != self._last_customer_ids:
            self._last_customer_ids = cur_ids
            self._refresh()
            return

        if not customers:
            return

        entry = self.peek_current()
        if entry is None:
            return

        # (2) Phase flipped on the shown order
        if self._last_phase != entry.phase:
            self._refresh()
            return

        # (3) Normal frame — redraw the bar surface only
        self._pat_bar.set_surface(
            _make_patience_bar(entry.ratio, PANEL_W - 32, entry.phase, entry.secs)
        )

    # ── Refresh (rebuild dynamic sprites when state changes) ──────────────────

    def _refresh(self):
        blank     = pygame.Surface((1, 1), pygame.SRCALPHA)
        customers = self._customers

        # Keep the "last seen list" sentinel in sync so update_ui doesn't
        # trigger a redundant refresh right after this one.
        self._last_customer_ids = [id(c) for c in customers]

        if not customers:
            self._current_customer = None
            self._nav_lbl.set_surface(blank)
            self._avatar.set_surface(blank)
            self._pat_bar.set_surface(blank)
            for spr in self._row_sprs:
                spr.set_surface(pygame.Surface((PANEL_W, ROW_H), pygame.SRCALPHA))
            self._btn_left.image  = _make_arrow(-1, False)
            self._btn_right.image = _make_arrow(+1, False)
            self._last_phase = None
            return

        # Repair selection if needed (customer was removed while we were looking at them).
        if self._current_customer not in customers:
            self._current_customer = customers[0]

        idx   = customers.index(self._current_customer)
        total = len(customers)
        e     = _OrderEntry(self._current_customer)

        # Nav label, avatar, patience bar — each is a StaticUI we just re-skin.
        self._nav_lbl.set_surface(_make_nav_label(idx, total, PANEL_W))
        self._avatar.set_surface(_make_avatar(e.image))
        self._pat_bar.set_surface(
            _make_patience_bar(e.ratio, PANEL_W - 32, e.phase, e.secs)
        )

        # Arrow buttons (dim when at edge) — UIButton exposes .image directly.
        self._btn_left.image  = _make_arrow(-1, idx > 0)
        self._btn_right.image = _make_arrow(+1, idx < total - 1)

        # Rows — items stored bottom→top, displayed top→bottom
        display = list(reversed(e.items))
        for i, spr in enumerate(self._row_sprs):
            item_id = display[i] if i < len(display) else None
            spr.set_surface(_make_row(item_id, PANEL_W))

        self._last_phase = e.phase

    # ── Navigation ────────────────────────────────────────────────────────────

    def _go_left(self):
        customers = self._customers
        if not customers or self._current_customer not in customers:
            return
        idx = customers.index(self._current_customer)
        if idx > 0:
            self._current_customer = customers[idx - 1]
            self._refresh()

    def _go_right(self):
        customers = self._customers
        if not customers or self._current_customer not in customers:
            return
        idx = customers.index(self._current_customer)
        if idx < len(customers) - 1:
            self._current_customer = customers[idx + 1]
            self._refresh()

    # ── handle_click forwarded from InputHandler ──────────────────────────────

    def handle_click(self, sprite):
        if hasattr(sprite, "on_click"):
            sprite.on_click()