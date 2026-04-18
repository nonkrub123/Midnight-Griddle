from settings import *
from interactive import *
from factory import *

def _load_surface(image_path):
    return pygame.image.load(image_path).convert_alpha()



# ─────────────────────────────────────────────────────────────────────────────
# BaseGroup
# Default handle_drop REJECTS. Only subclasses that explicitly want food items
# accept.
# ─────────────────────────────────────────────────────────────────────────────
class BaseGroup(pygame.sprite.LayeredUpdates):
    """
    current_group contract:
    - handle_drag     : removes sprite, sets sprite.current_group = self
    - handle_drop     : REJECTS by default (returns False) — subclasses opt in
    - handle_snapback : re-adds sprite to current_group (home), clears current_group
    """
    def add(self, *sprites, **kwargs):
        super().add(*sprites, **kwargs)
        for s in sprites:
            if hasattr(s, 'current_group'):
                s.current_group = self

    def update(self, dt=0):
        for sprite in self.sprites():
            sprite.update(dt)

    def handle_click(self, sprite):
        sprite.on_click()

    def handle_drag(self, sprite, pos):
        """Lift sprite out; remember this group as its home."""
        sprite.current_group = self
        self.remove(sprite)

    def handle_drop(self, sprite, target):
        """Base rejects all drops. Groups that hold food must override this."""
        return False

    def handle_snapback(self, sprite):
        """Return sprite to its home group."""
        home = sprite.current_group or self
        home.add(sprite)
        sprite.current_group = None
        home._on_snapback(sprite)

    def _on_snapback(self, sprite):
        """Hook for subclasses. Base just fires on_snapback."""
        sprite.on_snapback()

# ─────────────────────────────────────────────────────────────────────────────
# StackGroup
# ─────────────────────────────────────────────────────────────────────────────
class StackGroup(BaseGroup):
    """
    Sprites stack upward from a base plate, using each item's pixel_height
    from ItemData.

    Parameters
    ----------
    name         : str
        Group identifier (also used to name an auto-generated plate).
    pos          : (x, y)
        Centre position of the base plate.
    max_capacity : int
        Maximum number of stacked items allowed (not counting the plate itself).
    base_plate   : pygame.sprite.Sprite | None
        Any sprite to use as the stack anchor.
        Pass a pre-built InteractiveObject, BasePlate, or any other Sprite.
        If None, a transparent invisible sprite is created automatically.
    plate_size   : (w, h)
        Size of the auto-generated invisible plate. Ignored when base_plate
        is supplied explicitly.
    """

    def __init__(self, name, pos, max_capacity,
                 base_plate=None, plate_size=(64, 64)):
        super().__init__()
        self.name         = name
        self.max_capacity = max_capacity
        
        self.__factory = ItemFactory()
        # Accept any sprite as the anchor, or fall back to an invisible one.
        if base_plate is not None:
            self.station_block = base_plate
        else:
            self.station_block = self.__factory.create_invisible_plate("invisible plate", pos, plate_size)

        self.station_block._layer      = LAYER_STATION
        self.station_block.rect.center = pos
        self.add(self.station_block, layer=LAYER_STATION)

    # ── Queries ───────────────────────────────────────────────────────────────

    def placed_items(self):
        return [s for s in self.sprites() if s is not self.station_block]

    def is_full(self):
        return len(self.placed_items()) >= self.max_capacity

    def top_item(self):
        items = self.placed_items()
        return items[-1] if items else None

    # ── Internal helpers ──────────────────────────────────────────────────────

    def _lock_all_except_top(self):
        for item in self.placed_items():
            item.is_locked = True
        top = self.top_item()
        if top:
            top.is_locked = False

    def _restack_all(self):
        base_x         = self.station_block.rect.centerx
        current_bottom = self.station_block.rect.bottom

        for item in self.sprites():
            if item is self.station_block:
                continue
            pixel_height      = ItemData.get_prop(item.name, "pixel_height", item.rect.height)
            item.set_target((base_x, current_bottom), 0.15)
            # item.rect.centerx = base_x
            # item.rect.bottom  = current_bottom
            current_bottom   -= pixel_height

        self._lock_all_except_top()


    # ── Event handlers ────────────────────────────────────────────────────────

    def handle_click(self, sprite):
        if sprite is not self.station_block:
            sprite.on_click()

    def handle_drag(self, sprite, pos):
        if sprite is not self.station_block:
            super().handle_drag(sprite, pos)
            print(f"[STACK] after drag: {[s.name for s in self.placed_items()]}, locked={[s.is_locked for s in self.placed_items()]}")
            self._restack_all()

    def handle_drop(self, sprite, target):
        print(f"[DROP] sprite={sprite.name} target={target.name} can_accept={self.can_accept(sprite)}")
        if not self.can_accept(sprite):
            print(f"[STACK] Rejected {sprite.name} — full={self.is_full()}")
            return False
        self.add(sprite)
        self._restack_all()
        sprite.current_group = self
        print(f"[STACK] after placing: {[s.name for s in self.placed_items()]}, locked={[s.is_locked for s in self.placed_items()]}")
        return True

    def handle_remove(self, sprite):
        self.remove(sprite)
        print(f"[STACK] after remove: {[s.name for s in self.placed_items()]}")
        self._restack_all()

    def handle_snapback(self, sprite):
        """Re-add sprite to this stack and restack."""
        self.add(sprite)
        sprite.current_group = self
        self._restack_all()
        # sprite.on_snapback()


    def can_accept(self, sprite) -> bool:
        print(f"[ACCEPT] placed={len(self.placed_items())} max={self.max_capacity} items={[s.name for s in self.placed_items()]}")
        return not self.is_full()


# ─────────────────────────────────────────────────────────────────────────────
# GrillGroup
# ─────────────────────────────────────────────────────────────────────────────
class GrillGroup(StackGroup):
    def __init__(self, name, pos, max_capacity, base_plate=None, plate_size=(64, 64)):
        super().__init__(name, pos, max_capacity, base_plate, plate_size)

    def can_accept(self, sprite) -> bool:
        return sprite.has_tag("grillable") and not self.is_full()

    # def handle_click(self, sprite):
    #     if sprite is not self.station_block and sprite.has_tag("grillable"):
    #         sprite._is_grilling = not sprite._is_grilling

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


# ─────────────────────────────────────────────────────────────────────────────
# DispenserGroup
# ─────────────────────────────────────────────────────────────────────────────
class DispenserGroup(StackGroup):
    def __init__(self, name, pos, template_item, base_plate=None, plate_size=(64,64)):
        super().__init__(name, pos, max_capacity=0, base_plate=base_plate, plate_size=plate_size)
        self.__factory  = ItemFactory()
        self._template  = template_item
        self._template.is_locked   = False
        self._template.rect.center = self.station_block.rect.center
        self.add(self._template)
        
    def handle_drag(self, sprite, pos):
        if sprite is not self._template:
            return
        # Respawn template from factory
        new_template = self.__factory.create(self._template.name, self.station_block.rect.center)
        new_template.current_group = self
        self._template = new_template
        self.add(self._template)

    def handle_snapback(self, sprite):
        sprite.kill()
        self._template.set_target(self.station_block.rect.center)

    def handle_drop(self, sprite, target):
        return False

# ─────────────────────────────────────────────────────────────────────────────
# TrashGroup
# ─────────────────────────────────────────────────────────────────────────────

class TrashGroup(StackGroup):
    def handle_drop(self, sprite, target):
        sprite.kill()
        return True
# ─────────────────────────────────────────────────────────────────────────────
# StationGroup
# ─────────────────────────────────────────────────────────────────────────────
class StationGroup(BaseGroup):

    def __init__(self, name, image_path, pos):
        super().__init__()
        surf = _load_surface(image_path)
        self.station_block = InteractiveObject(name, pos, {"default": surf})
        self.station_block._layer    = LAYER_STATION
        self.station_block.is_locked = True
        self.add(self.station_block, layer=LAYER_STATION)
        self.stack_offset = 5

    def placed_items(self):
        return [s for s in self.sprites() if s is not self.station_block]

    def place(self, item):
        idx = len(self.placed_items())
        item.rect.centerx = self.station_block.rect.centerx
        item.rect.centery = self.station_block.rect.centery - (idx * self.stack_offset)
        self.add(item)

    def clear_station(self):
        for item in self.placed_items():
            item.kill()