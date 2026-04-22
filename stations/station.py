from core.settings import *
from core.gamedata import GameData
from ui.interactive import *
from ui.group import *
from ui.factory import ItemFactory
from ui.orderui import OrderUI
from stations.customermanager import CustomerManager
from core.stattracker import GameHour, StatTracker
from core.itemdata import ItemData
import ui.theme as theme


# ─────────────────────────────────────────────────────────────────────────────
# Base Station
# ─────────────────────────────────────────────────────────────────────────────
class Station:
    def __init__(self, screen, bg_image_path):
        self.screen     = screen
        self.background = pygame.image.load(bg_image_path).convert()
        self.all_groups: list[BaseGroup] = []

    def register_group(self, group: BaseGroup):
        self.all_groups.append(group)

    def get_all_groups(self):
        return list(self.all_groups)

    def update(self, dt):
        for group in self.all_groups:
            group.update(dt)

    def draw_background(self):
        self.screen.blit(self.background, (0, 0))


# ─────────────────────────────────────────────────────────────────────────────
# Order Station
# ─────────────────────────────────────────────────────────────────────────────
class OrderStation(Station):
    def __init__(self, screen, bg_image_path,
                 customer_manager: CustomerManager, order_ui: OrderUI):
        super().__init__(screen, bg_image_path)
        self._cm       = customer_manager
        self._order_ui = order_ui
        self._group    = BaseGroup()

        # ACCEPT button — UIButton built from a theme surface, topleft-anchored
        self._group.add(UIButton(
            "btn_accept_order",
            theme.button_surface("ACCEPT ORDER"),
            theme.POS_ORDER_ACCEPT,
            self._accept,
            anchor="topleft",
        ))

        self._customer_spr = None
        self._shown        = None

        self.register_group(self._group)
        self.register_group(self._order_ui)

    def update(self, dt):
        super().update(dt)

        front = self._cm.on_ordering[0] if self._cm.on_ordering else None
        if front is not self._shown:
            self._shown = front
            self._refresh_customer(front)

    def _refresh_customer(self, customer):
        if self._customer_spr:
            self._customer_spr.kill()
            self._customer_spr = None
        if customer is None:
            return
        surf = pygame.transform.smoothscale(customer.image, theme.ORDER_CUSTOMER_SIZE)
        self._customer_spr = StaticUI(surf, theme.POS_ORDER_CUSTOMER,
                                      layer=LAYER_FOOD, anchor="center",
                                      name="customer_display")
        self._group.add(self._customer_spr)

    def _accept(self):
        self._cm.take_order()


# ─────────────────────────────────────────────────────────────────────────────
# Grill Station
# ─────────────────────────────────────────────────────────────────────────────
class GrillStation(Station):
    def __init__(self, screen, bg_image_path, gamedata: GameData, tray: TrayGroup,
                 order_ui: OrderUI):
        super().__init__(screen, bg_image_path)
        factory = ItemFactory()
        
        self.grill_list = []
        self.grill_list_pos = theme.POS_GRILL_LIST
        for i in range(12):
            self.grill_list.append(GrillGroup(
            "grill", self.grill_list_pos[i], max_capacity=1,
            base_plate=None, plate_size=(324,174)),
        )
            # theme.POS_GRILL
        
        self.meat_dispenser = DispenserGroup(
            name          = "meat_dispenser",
            pos           = theme.POS_DISPENSER["meat"],
            template_item = factory.create("meat", theme.POS_DISPENSER["meat"]),
            gamedata      = gamedata,
            base_plate    = factory.create_base_plate("base_plate",
                                                      theme.POS_DISPENSER["meat"]),
        )

        self.trash = TrashGroup("trash", theme.POS_TRASH, 1, factory.create_base_plate("trash", theme.POS_TRASH))
        self.tray = tray

        for i in range(12):
            self.register_group(self.grill_list[i])
        self.register_group(self.meat_dispenser)
        self.register_group(self.tray)
        self.register_group(self.trash)
        self.register_group(order_ui)
        

# ─────────────────────────────────────────────────────────────────────────────
# Order Summary Group  (used inside AssembleStation)
# Small read-only panel showing the current order's items.
# Every sprite here is a StaticUI — no ad-hoc locked-sprite helpers.
# ─────────────────────────────────────────────────────────────────────────────
class OrderSummaryGroup(BaseGroup):
    """
    Displays the currently selected order from OrderUI as a vertical item list.
    Lives in AssembleStation so the player never has to switch tabs to check.
    Clears automatically when there is no active order.
    """

    _ITEM_H = 56

    def __init__(self, x: int | None = None, y: int | None = None,
                 max_rows: int | None = None):
        super().__init__()
        self._x        = theme.POS_ORDER_SUMMARY[0] if x        is None else x
        self._y        = theme.POS_ORDER_SUMMARY[1] if y        is None else y
        self._panel_w  = theme.ORDER_SUMMARY_W
        self._max_rows = theme.ORDER_SUMMARY_ROWS   if max_rows is None else max_rows
        self._shown_items = None

        # Title is a StaticUI that we re-skin in _rebuild()
        self._title_spr = StaticUI(self._make_title("No active order"),
                                   (self._x, self._y),
                                   layer=5, name="order_summary_title")
        self.add(self._title_spr)
        self._item_sprs: list[StaticUI] = []

    # ── Called every frame from AssembleStation.update() ──────────────────────

    def sync(self, order_entry):
        """Pass the result of order_ui.peek_current() each frame."""
        items = order_entry.items if order_entry else None
        if items == self._shown_items:
            return
        self._shown_items = items
        self._rebuild(items)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _rebuild(self, items):
        for spr in self._item_sprs:
            spr.kill()
        self._item_sprs.clear()

        if not items:
            self._title_spr.set_surface(self._make_title("No active order"))
            return

        self._title_spr.set_surface(self._make_title("Current Order"))
        title_h = self._title_spr.rect.height + 6
        display = list(reversed(items))

        for i, item_id in enumerate(display[:self._max_rows]):
            ry   = self._y + title_h + i * self._ITEM_H
            surf = self._make_row(item_id)
            spr  = StaticUI(surf, (self._x, ry), layer=5,
                            name=f"order_summary_row_{i}")
            self._item_sprs.append(spr)
            self.add(spr)

    def _make_title(self, text: str) -> pygame.Surface:
        lbl  = theme.font(17, bold=True).render(text, True, theme.C_TITLE)
        surf = pygame.Surface((self._panel_w, lbl.get_height() + 12), pygame.SRCALPHA)
        pygame.draw.rect(surf, theme.C_BG,     surf.get_rect(), border_radius=6)
        pygame.draw.rect(surf, theme.C_BORDER, surf.get_rect(), 1, border_radius=6)
        surf.blit(lbl, lbl.get_rect(center=(self._panel_w//2,
                                             (lbl.get_height()+12)//2)))
        return surf

    def _make_row(self, item_id: str) -> pygame.Surface:
        surf = pygame.Surface((self._panel_w, self._ITEM_H), pygame.SRCALPHA)
        pygame.draw.rect(surf, theme.C_BG,     surf.get_rect())
        pygame.draw.rect(surf, theme.C_BORDER, surf.get_rect(), 1)

        data = ItemData.get_item(item_id)
        if data:
            img_name = data["state_imgs"].get("default",
                            next(iter(data["state_imgs"].values())))
            img      = ItemData.load_img(img_name, data["type"])
            img      = pygame.transform.smoothscale(img, (40, 40))
            surf.blit(img, (8, (self._ITEM_H - 40) // 2))

        name = ItemData.get_prop(item_id, "display_name", item_id)
        txt  = theme.font(16).render(name, True, theme.C_TEXT)
        surf.blit(txt, (56, (self._ITEM_H - txt.get_height()) // 2))
        return surf


# ─────────────────────────────────────────────────────────────────────────────
# Assemble Station
# ─────────────────────────────────────────────────────────────────────────────
class AssembleStation(Station):
    def __init__(self, screen, bg_image_path,
                 gamedata: GameData,
                 tray: TrayGroup,
                 order_ui: OrderUI,
                 customer_manager: CustomerManager,
                 stat_tracker: StatTracker):
        super().__init__(screen, bg_image_path)
        self._gamedata         = gamedata
        self._order_ui         = order_ui
        self._customer_manager = customer_manager
        self._stat_tracker     = stat_tracker
        factory = ItemFactory()

        # ── Plate ─────────────────────────────────────────────────────────────
        self.plate = PlateGroup(
            "plate", theme.POS_PLATE, max_capacity=10,
            base_plate=factory.create("redplate", pos=theme.POS_PLATE),
        )

        # ── Ingredient dispensers ─────────────────────────────────────────────
        def _make_dispenser(item_id: str) -> DispenserGroup:
            pos = theme.POS_DISPENSER[item_id]
            return DispenserGroup(
                f"dispenser_{item_id}", pos,
                factory.create(item_id, pos), gamedata,
                factory.create_base_plate("base_plate", pos),
            )

        # List of all ingredient IDs to generate
        ingredient_ids = ItemData.get_ingredients()
        
        # Create and Register Dispensers
        self.dispensers = {}
        for i_id in ingredient_ids:
            dispenser = _make_dispenser(i_id)
            self.dispensers[i_id] = dispenser
            self.register_group(dispenser)

        # ── Order summary (left side, always visible) ─────────────────────────
        self.order_summary = OrderSummaryGroup()

        # ── Submit button ─────────────────────────────────────────────────────
        self._btn_group = BaseGroup()
        self._btn_group.add(UIButton(
            "btn_submit_order",
            theme.button_surface("SUBMIT ORDER",
                                 w=240, h=70, color=theme.C_BTN_SUBMIT),
            theme.POS_SUBMIT_BTN,
            self._submit,
            anchor="topleft",
        ))

        # ── Feedback flash ────────────────────────────────────────────────────
        self._feedback_spr   = None
        self._feedback_timer = 0.0
        
        self.tray = tray
        self.register_group(self.tray)
        self.register_group(self.plate)
        self.register_group(self.order_summary)
        self.register_group(self._order_ui)
        self.register_group(self._btn_group)

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt):
        super().update(dt)

        self.order_summary.sync(self._order_ui.peek_current())

        if self._feedback_spr and self._feedback_timer > 0:
            self._feedback_timer -= dt
            if self._feedback_timer <= 0:
                self._feedback_spr.kill()
                self._feedback_spr = None

    # ── Submit ────────────────────────────────────────────────────────────────

    def _submit(self):
        entry = self._order_ui.peek_current()
        if entry is None:
            self._flash("No active order!", color=theme.C_FLASH_WARN)
            return

        plate_items = self.plate.get_items_with_state()      # [{name, cook_state}]
        plate_names = [p["name"] for p in plate_items]
        order_items = entry.items

        # ── Stats ─────────────────────────────────────────────────────────────
        ordering_ratio = entry.ordering_ratio                 # snapshot at accept
        waiting_ratio  = entry.ratio                          # live, now = waiting
        accuracy_pct   = self._stat_tracker.log_accuracy(plate_items, order_items)
        rating         = StatTracker.compute_rating(ordering_ratio, accuracy_pct, waiting_ratio)
        revenue        = sum(ItemData.get_prop(i, "sell_price", 0) for i in plate_names)

        self._stat_tracker.log_revenue(revenue)
        self._stat_tracker.log_satisfaction(rating)
        self._stat_tracker.log_ingredients(plate_names)
        self._gamedata.add_money(revenue)
        self._gamedata.save()

        stars = "*" * rating + "-" * (5 - rating)
        self._flash(f"Served!  {stars}  ({accuracy_pct:.0f}%)", color=theme.C_FLASH_OK)

        self._order_ui.pop_current()   # ← this now removes from CustomerManager too
        self.plate.clear()

    # ── Feedback flash helper ─────────────────────────────────────────────────

    def _flash(self, message: str, color=None, duration=2.0):
        if color is None:
            color = theme.C_FLASH_OK
        if self._feedback_spr:
            self._feedback_spr.kill()

        # Build the banner surface
        txt  = theme.font(28, bold=True).render(message, True, (255, 255, 255))
        w, h = txt.get_width() + 40, txt.get_height() + 20
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*color, 210), (0, 0, w, h), border_radius=10)
        surf.blit(txt, txt.get_rect(center=(w//2, h//2)))

        # Wrap it in a StaticUI — centered on the feedback anchor point
        self._feedback_spr = StaticUI(surf, theme.POS_FEEDBACK,
                                      layer=10, anchor="center",
                                      name="feedback_flash")
        self._feedback_timer = duration
        self._btn_group.add(self._feedback_spr)