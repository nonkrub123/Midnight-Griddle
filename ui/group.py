from core.settings import *
from ui.interactive import *
from ui.factory import ItemFactory

import ui.theme as theme

def _load_surface(image_path):
    return pygame.image.load(image_path).convert_alpha()


# ─────────────────────────────────────────────────────────────────────────────
# BaseGroup
# ─────────────────────────────────────────────────────────────────────────────
class BaseGroup(pygame.sprite.LayeredUpdates):
    def update(self, dt=0):
        for sprite in self.sprites():
            sprite.update(dt)

    def handle_click(self, sprite):
        sprite.on_click()

    def handle_drag(self, sprite, pos):
        sprite.current_group = self   # remember home for snapback
        sprite.kill()                 # was: self.remove(sprite) — now removes from ALL groups

    def handle_drop(self, sprite, target):
        return False

    def handle_remove(self, sprite):
        self.remove(sprite)

    def handle_snapback(self, sprite):
        home = sprite.current_group
        if home is not None:
            home.add(sprite)
            home._on_snapback(sprite)
        sprite.current_group = None

    def _on_snapback(self, sprite):
        sprite.on_snapback()


# ─────────────────────────────────────────────────────────────────────────────
# StackGroup
# ─────────────────────────────────────────────────────────────────────────────
class StackGroup(BaseGroup):
    def __init__(self, name, pos, max_capacity, base_plate=None, plate_size=(64, 64)):
        super().__init__()
        self.name         = name
        self.max_capacity = max_capacity

        self.__factory = ItemFactory()
        if base_plate is not None:
            self.station_block = base_plate
        else:
            self.station_block = self.__factory.create_invisible_plate("invisible plate", pos, plate_size)

        self.station_block._layer      = LAYER_STATION
        self.station_block.rect.center = pos
        self.add(self.station_block, layer=LAYER_STATION)

    def placed_items(self):
        return [s for s in self.sprites()
                if s is not self.station_block
                and isinstance(s, InteractiveObject)]   # excludes StaticUI / _StockLabel

    def is_full(self):
        return len(self.placed_items()) >= self.max_capacity

    def top_item(self):
        items = self.placed_items()
        return items[-1] if items else None

    def _lock_all_except_top(self):
        for item in self.placed_items():
            item.is_locked = True
        top = self.top_item()
        if top:
            top.is_locked = False

    def _restack_all(self):
        base_x   = self.station_block.rect.centerx
        center_y = self.station_block.rect.centery
        for item in self.placed_items():
            pixel_height = ItemData.get_prop(item.name, "pixel_height", item.rect.height)
            item.set_target((base_x, center_y), 0.15)
            center_y -= pixel_height
        self._lock_all_except_top()

    def handle_click(self, sprite):
        if sprite is not self.station_block:
            sprite.on_click()

    def handle_drag(self, sprite, pos):
        if sprite is not self.station_block:
            super().handle_drag(sprite, pos)
            self._restack_all()

    def handle_drop(self, sprite, target):
        if not self.can_accept(sprite):
            return False
        self.add(sprite)
        self._restack_all()
        sprite.current_group = self
        return True

    def handle_remove(self, sprite):
        self.remove(sprite)
        self._restack_all()

    def handle_snapback(self, sprite):
        self.add(sprite)
        sprite.current_group = self
        self._restack_all()

    def can_accept(self, sprite) -> bool:
        return not self.is_full()


# ─────────────────────────────────────────────────────────────────────────────
# GrillGroup
# ─────────────────────────────────────────────────────────────────────────────
class GrillGroup(StackGroup):
    def __init__(self, name, pos, max_capacity, base_plate=None, plate_size=(64, 64)):
        super().__init__(name, pos, max_capacity, base_plate, plate_size)

    def can_accept(self, sprite) -> bool:
        return sprite.has_tag("grillable") and not self.is_full()

    def update(self, dt=0):
        super().update(dt)
        for item in self.placed_items():
            if item.has_tag("grillable"):
                item.on_cook(dt)


# ─────────────────────────────────────────────────────────────────────────────
# PlateGroup
# ─────────────────────────────────────────────────────────────────────────────
class PlateGroup(StackGroup):
    """StackGroup that only accepts ingredients."""
    def can_accept(self, sprite) -> bool:
        return sprite.has_tag("ingredient") and not self.is_full()

    def get_item_names(self) -> list[str]:
        """Return item names bottom → top (matches order format)."""
        return [s.name for s in self.placed_items()]

    def get_items_with_state(self) -> list[dict]:
        """
        Return item info bottom → top.
        Each dict: {"name": str, "cook_state": str | None}
        cook_state is only set for GrillableItems (e.g. "raw", "cooked", "burnt").
        """
        result = []
        for s in self.placed_items():
            result.append({
                "name":       s.name,
                "cook_state": getattr(s, "_cook_state", None),
            })
        return result

    def clear(self):
        for item in self.placed_items():
            item.kill()


# ─────────────────────────────────────────────────────────────────────────────
# TrayGroup
# Shared between GrillStation and AssembleStation.
# Accepts any ingredient (including grillables that have ingredient=True).
# ─────────────────────────────────────────────────────────────────────────────
class TrayGroup(StackGroup):
    """Tray that carries items from the grill to the assembly station."""
    def can_accept(self, sprite) -> bool:
        return sprite.has_tag("ingredient") and not self.is_full()


# ─────────────────────────────────────────────────────────────────────────────
# _StockLabel
# Small numeric badge above each dispenser. Inherits from StaticUI so
# construction / rect handling / has_tag all come for free.
# ─────────────────────────────────────────────────────────────────────────────
class _StockLabel(StaticUI):
    def __init__(self, pos):
        # Start with a 1×1 blank — real content set by first set_stock() call.
        super().__init__(
            pygame.Surface((1, 1), pygame.SRCALPHA),
            pos, layer=LAYER_UI, anchor="center", name="stock_label",
        )
        self.is_locked = True
        self._font = theme.font(18, bold=True)

    def set_stock(self, count: int):
        txt  = self._font.render(str(count), True, (255, 255, 255))
        w, h = txt.get_width() + 14, txt.get_height() + 8
        surf = pygame.Surface((w, h), pygame.SRCALPHA)
        col  = (60, 160, 60) if count > 0 else (180, 50, 50)
        pygame.draw.rect(surf, col,             (0, 0, w, h), border_radius=6)
        pygame.draw.rect(surf, (255, 255, 255), (0, 0, w, h), 1, border_radius=6)
        surf.blit(txt, (7, 4))
        self.set_surface(surf)   # StaticUI re-anchors on its stored center


# ─────────────────────────────────────────────────────────────────────────────
# DispenserGroup
# ─────────────────────────────────────────────────────────────────────────────
class DispenserGroup(StackGroup):
    def __init__(self, name, pos, template_item, gamedata: GameData,
                 base_plate=None, plate_size=(64, 64)):
        super().__init__(name, pos, max_capacity=0, base_plate=base_plate, plate_size=plate_size)
        self._factory  = ItemFactory()
        self._gamedata = gamedata
        self._item_id  = template_item.name

        self._template             = template_item
        self._template.is_locked   = False
        self._template.rect.center = self.station_block.rect.center
        self.add(self._template)

        label_pos = (self.station_block.rect.centerx,
                     self.station_block.rect.top - 16)
        self._stock_label = _StockLabel(label_pos)
        self.add(self._stock_label)
        self._update_label()

    def _update_label(self):
        stock = self._gamedata.get_stock(self._item_id)
        self._stock_label.set_stock(stock)
        self._template.is_locked = stock <= 0

    def handle_drag(self, sprite, pos):
        if sprite is not self._template:
            return
        if not self._gamedata.has_stock(self._item_id):
            return
        self._gamedata.use_stock(self._item_id)

        super().handle_drag(sprite, pos)   # ← ADD THIS: kills old template, sets current_group = self

        # Spawn a fresh template in the dispenser
        new_template = self._factory.create(self._item_id, self.station_block.rect.center)
        self._template = new_template
        self.add(self._template)
        self._update_label()

    def handle_snapback(self, sprite):
        sprite.kill()
        self._gamedata.add_stock(self._item_id, 1)
        self._template.set_target(self.station_block.rect.center)
        self._update_label()

    def handle_drop(self, sprite, target):
        return False

    def update(self, dt=0):
        super().update(dt)
        self._update_label()


# ─────────────────────────────────────────────────────────────────────────────
# TrashGroup
# ─────────────────────────────────────────────────────────────────────────────
class TrashGroup(StackGroup):
    def handle_drop(self, sprite, target):
        if not sprite.has_tag("undeletable"):
            sprite.kill()
            return True
        return False


# ─────────────────────────────────────────────────────────────────────────────
# StationGroup
# ─────────────────────────────────────────────────────────────────────────────
# class StationGroup(BaseGroup):
#     def __init__(self, name, image_path, pos):
#         super().__init__()
#         surf = _load_surface(image_path)
#         self.station_block = InteractiveObject(name, pos, {"default": surf})
#         self.station_block._layer    = LAYER_STATION
#         self.station_block.is_locked = True
#         self.add(self.station_block, layer=LAYER_STATION)
#         self.stack_offset = 5

#     def placed_items(self):
#         return [s for s in self.sprites() if s is not self.station_block]

#     def place(self, item):
#         idx = len(self.placed_items())
#         item.rect.centerx = self.station_block.rect.centerx
#         item.rect.centery = self.station_block.rect.centery - (idx * self.stack_offset)
#         self.add(item)

#     def clear_station(self):
#         for item in self.placed_items():
#             item.kill()