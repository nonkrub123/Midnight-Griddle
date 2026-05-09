from core.settings import *
from core.gamedata import GameData
from ui.interactive import *
from ui.group import *
from ui.factory import ItemFactory
from ui.group_orderui import OrderUI
from stations.customermanager import CustomerManager
from core.stattracker import StatTracker
from core.itemdata import ItemData
import ui.theme as theme


# ─────────────────────────────────────────────────────────────────────────────
# Base Station
# ─────────────────────────────────────────────────────────────────────────────
class Station:
    def __init__(self, screen, bg_image_path):
        self.screen     = screen
        self.background = pygame.image.load(bg_image_path).convert()
        self.__all_groups: list[BaseGroup] = []

    def register_group(self, group: BaseGroup):
        self.__all_groups.append(group)

    def get_all_groups(self):
        return list(self.__all_groups)

    def update(self, dt):
        for group in self.__all_groups:
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
        self._group    = UIGroup()

        self._group.add(UIButton(
            "btn_accept_order",
            theme.button_surface("ACCEPT ORDER", w=theme.BTN_W, h=theme.BTN_H),
            theme.POS_ORDER_ACCEPT,
            self._accept,
            anchor="topleft",
        ))

        self.__customer_spr = None
        self.__shown        = None

        self.register_group(self._group)
        self.register_group(self._order_ui)

    def update(self, dt):
        super().update(dt)

        front = self._cm.on_ordering[0] if self._cm.on_ordering else None
        if front is not self.__shown:
            self.__shown = front
            self._refresh_customer(front)

    def _refresh_customer(self, customer):
        if self.__customer_spr:
            self.__customer_spr.kill()
            self.__customer_spr = None
        if customer is None:
            return
        surf = pygame.transform.smoothscale(customer.image, theme.ORDER_CUSTOMER_SIZE)
        self.__customer_spr = StaticUI(surf, theme.POS_ORDER_CUSTOMER,
                                       layer=LAYER_FOOD, anchor="center",
                                       name="customer_display")
        self._group.add(self.__customer_spr)

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

        grill_positions = theme.POS_GRILL_LIST     # local — not stored as attribute

        self.__grill_list = [
            GrillGroup("grill", grill_positions[i], max_capacity=1,
                       base_plate=None, plate_size=(324, 174))
            for i in range(12)
        ]

        self.meat_dispenser = DispenserGroup(
            name          = "meat_dispenser",
            pos           = theme.POS_DISPENSER["meat"],
            template_item = factory.create("meat", theme.POS_DISPENSER["meat"]),
            gamedata      = gamedata,
            base_plate    = factory.create_base_plate("base_plate",
                                                      theme.POS_DISPENSER["meat"]),
        )

        self.trash = TrashGroup(
            "trash", theme.POS_TRASH, 1,
            factory.create_base_plate("trash", theme.POS_TRASH),
        )
        self.tray = tray

        for grill in self.__grill_list:
            self.register_group(grill)
        self.register_group(self.meat_dispenser)
        self.register_group(self.tray)
        self.register_group(self.trash)
        self.register_group(order_ui)


# ─────────────────────────────────────────────────────────────────────────────
# Order Summary Group  (used inside AssembleStation)
# Small read-only panel showing the current order's items.
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
        self.__x        = theme.POS_ORDER_SUMMARY[0] if x        is None else x
        self.__y        = theme.POS_ORDER_SUMMARY[1] if y        is None else y
        self.__panel_w  = theme.ORDER_SUMMARY_W
        self.__max_rows = theme.ORDER_SUMMARY_ROWS   if max_rows is None else max_rows
        self.__shown_items = None

        self.__title_spr = StaticUI(self._make_title("No active order"),
                                    (self.__x, self.__y),
                                    layer=5, name="order_summary_title")
        self.add(self.__title_spr)
        self.__item_sprs: list[StaticUI] = []

    # ── Public API ────────────────────────────────────────────────────────────

    def sync(self, order_entry):
        """Pass the result of order_ui.peek_current() each frame."""
        items = order_entry.items if order_entry else None
        if items == self.__shown_items:
            return
        self.__shown_items = items
        self._rebuild(items)

    # ── Private ───────────────────────────────────────────────────────────────

    def _rebuild(self, items):
        for spr in self.__item_sprs:
            spr.kill()
        self.__item_sprs.clear()

        if not items:
            self.__title_spr.set_surface(self._make_title("No active order"))
            return

        self.__title_spr.set_surface(self._make_title("Current Order"))
        title_h = self.__title_spr.rect.height + 6
        display = list(reversed(items))

        for i, item_id in enumerate(display[:self.__max_rows]):
            ry   = self.__y + title_h + i * self._ITEM_H
            surf = self._make_row(item_id)
            spr  = StaticUI(surf, (self.__x, ry), layer=5,
                            name=f"order_summary_row_{i}")
            self.__item_sprs.append(spr)
            self.add(spr)

    def _make_title(self, text: str) -> pygame.Surface:
        lbl  = theme.font(17, bold=True).render(text, True, theme.C_TITLE)
        surf = pygame.Surface((self.__panel_w, lbl.get_height() + 12), pygame.SRCALPHA)
        pygame.draw.rect(surf, theme.C_BG,     surf.get_rect(), border_radius=6)
        pygame.draw.rect(surf, theme.C_BORDER, surf.get_rect(), 1, border_radius=6)
        surf.blit(lbl, lbl.get_rect(center=(self.__panel_w // 2,
                                             (lbl.get_height() + 12) // 2)))
        return surf

    def _make_row(self, item_id: str) -> pygame.Surface:
        surf = pygame.Surface((self.__panel_w, self._ITEM_H), pygame.SRCALPHA)
        pygame.draw.rect(surf, theme.C_BG,     surf.get_rect())
        pygame.draw.rect(surf, theme.C_BORDER, surf.get_rect(), 1)

        data = ItemData.get_item(item_id)
        if data:
            img_name = data["state_imgs"].get("default",
                            next(iter(data["state_imgs"].values())))
            img = pygame.transform.smoothscale(
                ItemData.load_img(img_name, data["type"]), (40, 40))
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
        self.__gamedata         = gamedata
        self.__order_ui         = order_ui
        self.__stat_tracker     = stat_tracker
        self.__audio_manager = AudioManager()
        factory = ItemFactory()

        # ── Plate ─────────────────────────────────────────────────────────────
        self.__plate = PlateGroup(
            "plate", theme.POS_PLATE, max_capacity=10,
            base_plate=factory.create("redplate", pos=theme.POS_PLATE),
            hitbox_size=(250, 1200),
        )

        # ── Ingredient __dispenser ─────────────────────────────────────────────
        def _make_dispenser(item_id: str) -> DispenserGroup:
            pos = theme.POS_DISPENSER[item_id]
            return DispenserGroup(
                f"dispenser_{item_id}", pos,
                factory.create(item_id, pos), gamedata,
                factory.create_base_plate("base_plate", pos),
            )

        self.__dispenser = {i_id: _make_dispenser(i_id)
                           for i_id in ItemData.get_ingredients()}
        for dispenser in self.__dispenser.values():
            self.register_group(dispenser)

        # ── Order summary ─────────────────────────────────────────────────────
        self.__order_summary = OrderSummaryGroup()

        # ── Submit button ─────────────────────────────────────────────────────
        self.__btn_group = UIGroup()
        self.__btn_group.add(UIButton(
            "btn_submit_order",
            theme.button_surface("SUBMIT ORDER",
                                 w=theme.BTN_W, h=theme.BTN_H,
                                 color=theme.C_BTN_SUBMIT),
            theme.POS_SUBMIT_BTN,
            self._submit,
            anchor="topleft",
        ))

        # ── Feedback flash ────────────────────────────────────────────────────
        self.__feedback_spr   = None
        self.__feedback_timer = 0.0

        self.tray = tray
        self.register_group(self.tray)
        self.register_group(self.__plate)
        self.register_group(self.__order_summary)
        self.register_group(self.__order_ui)
        self.register_group(self.__btn_group)

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt):
        super().update(dt)

        self.__order_summary.sync(self.__order_ui.peek_current())

        if self.__feedback_spr and self.__feedback_timer > 0:
            self.__feedback_timer -= dt
            if self.__feedback_timer <= 0:
                self.__feedback_spr.kill()
                self.__feedback_spr = None

    # ── Private ───────────────────────────────────────────────────────────────

    def _submit(self):
        entry = self.__order_ui.peek_current()
        if entry is None:
            self._flash("No active order!", color=theme.C_FLASH_WARN)
            return

        plate_items = self.__plate.get_items_with_state()
        plate_names = [p["name"] for p in plate_items]
        order_items = entry.items

        ordering_ratio = entry.ordering_ratio
        waiting_ratio  = entry.ratio
        accuracy_pct   = self.__stat_tracker.log_accuracy(plate_items, order_items)
        rating         = StatTracker.compute_rating(ordering_ratio, accuracy_pct, waiting_ratio)
        revenue        = sum(ItemData.get_prop(i, "sell_price", 0) for i in plate_names)

        self.__stat_tracker.log_satisfaction(rating)
        self.__stat_tracker.log_ingredients(plate_names)
        self.__gamedata.add_money(revenue)
        self.__stat_tracker.log_revenue(self.__gamedata.money)
        self.__gamedata.save()

        stars = "*" * rating + "-" * (5 - rating)
        self._flash(f"Served!  {stars}  ({accuracy_pct:.0f}%)", color=theme.C_FLASH_OK)

        self.__order_ui.pop_current()
        self.__plate.clear()

        self.__audio_manager.play_sound("ghost_submit")

    def _flash(self, message: str, color=None, duration=2.0):
        if color is None:
            color = theme.C_FLASH_OK
        if self.__feedback_spr:
            self.__feedback_spr.kill()

        txt  = theme.font(28, bold=True).render(message, True, (255, 255, 255))
        w, h = txt.get_width() + 40, txt.get_height() + 20
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(surf, (*color, 210), (0, 0, w, h), border_radius=10)
        surf.blit(txt, txt.get_rect(center=(w // 2, h // 2)))

        self.__feedback_spr = StaticUI(surf, theme.POS_FEEDBACK,
                                       layer=10, anchor="center",
                                       name="feedback_flash")
        self.__feedback_timer = duration
        self.__btn_group.add(self.__feedback_spr)