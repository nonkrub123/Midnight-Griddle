from settings import *
from interactive import *


def _load_surface(image_path):
    return pygame.image.load(image_path).convert_alpha()


# ── Base Group ────────────────────────────────────────────────────────────────

class BaseGroup(pygame.sprite.LayeredUpdates):
    """
    All groups inherit from LayeredUpdates so sprites can be lifted to
    LAYER_DRAGGING while being dragged and restored afterwards.

    current_group contract
    ──────────────────────
    • handle_drag  → sets sprite.current_group = self  (sprite is "owned" by us)
    • handle_drop  → winner group takes ownership; loser calls handle_remove
    • handle_snapback → uses sprite.current_group to re-add the sprite
    """

    def update(self, dt=0):
        for sprite in self.sprites():
            sprite.update(dt)

    # ── Input callbacks ───────────────────────────────────────────────────────

    def handle_click(self, sprite):
        if sprite.has_tag("clickable"):
            sprite.on_click()

    def handle_drag(self, sprite, pos):
        """Remove from group while dragging so it doesn't render twice."""
        if sprite.has_tag("draggable") and not sprite.is_locked:
            sprite.current_group = self   # remember home
            self.remove(sprite)           # ← lifted out; InputHandler draws it
            sprite.on_drag(pos)

    def handle_drop(self, sprite, target):
        """Base: always reject — subclasses override."""
        return False

    def handle_remove(self, sprite):
        """Called on the *source* group after a successful drop elsewhere."""
        # Sprite was already removed in handle_drag; nothing extra needed here.
        sprite.current_group = None

    def handle_snapback(self, sprite):
        """Drop was rejected — put the sprite back where it came from."""
        home = sprite.current_group
        if home is not None:
            home.add(sprite)
            home._on_snapback(sprite)
        else:
            # Fallback: just re-add to self
            self.add(sprite)
        sprite.current_group = None

    def _on_snapback(self, sprite):
        """Hook for subclasses (e.g. restack). Base does nothing."""
        sprite.on_snapback()


# ── Stack Group ───────────────────────────────────────────────────────────────

class StackGroup(BaseGroup):
    """
    Sprites stack visually on top of a station_block tile.
    Only the top-most item is unlocked for interaction.
    """

    STACK_OVERLAP = 4   # pixels each item overlaps the one below

    def __init__(self, name, image_path, pos, max_capacity):
        super().__init__()
        surf = _load_surface(image_path)
        self.station_block = InteractiveObject(name, pos, {"default": surf})
        self.station_block._layer = LAYER_STATION
        self.station_block.is_locked = True          # tile itself is never dragged
        self.add(self.station_block, layer=LAYER_STATION)
        self.max_capacity = max_capacity

    # ── Helpers ───────────────────────────────────────────────────────────────

    def placed_items(self):
        return [s for s in self.sprites() if s is not self.station_block]

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
        """Re-position every placed item into a neat visual stack."""
        items     = self.placed_items()
        base_x    = self.station_block.rect.centerx
        # Start from the TOP of the station block and build upward
        current_y = self.station_block.rect.top

        for item in items:
            # Each item sits so its bottom is at current_y + STACK_OVERLAP
            item.rect.centerx = base_x
            item.rect.bottom  = current_y + self.STACK_OVERLAP
            current_y         = item.rect.top    # next item stacks above this one
            self.change_layer(item, LAYER_FOOD)

        self._lock_all_except_top()

    # ── Input callbacks ───────────────────────────────────────────────────────

    def handle_click(self, sprite):
        if sprite is not self.station_block:
            sprite.on_click()

    def handle_drag(self, sprite, pos):
        if sprite is self.station_block:
            return
        super().handle_drag(sprite, pos)

    def handle_drop(self, sprite, target):
        if not self.can_accept(sprite):
            print(f"[STACK DROP] Rejected {sprite.name} — full={self.is_full()}")
            return False
        self.add(sprite, layer=LAYER_FOOD)
        self._restack_all()
        sprite.on_place()
        return True

    def handle_remove(self, sprite):
        """Called after a successful drop into another group."""
        if sprite in self.sprites():
            self.remove(sprite)
        self._restack_all()
        sprite.current_group = None

    def _on_snapback(self, sprite):
        """Re-add (already done by BaseGroup.handle_snapback) then restack."""
        self._restack_all()
        sprite.on_snapback()

    # ── Acceptance ────────────────────────────────────────────────────────────

    def can_accept(self, sprite) -> bool:
        return not self.is_full()


# ── Grill Group ───────────────────────────────────────────────────────────────

class GrillGroup(StackGroup):
    """Accepts only grillable items. Click toggles grilling on/off."""

    def can_accept(self, sprite) -> bool:
        return sprite.has_tag("grillable") and not self.is_full()

    def handle_click(self, sprite):
        if sprite is not self.station_block and sprite.has_tag("grillable"):
            sprite._is_grilling = not sprite._is_grilling
            state = "resumed" if sprite._is_grilling else "paused"
            print(f"[GRILL] {sprite.name} grilling {state}")


# ── Plate Group ───────────────────────────────────────────────────────────────

class PlateGroup(StackGroup):
    """Accepts any ingredient."""

    def can_accept(self, sprite) -> bool:
        return sprite.has_tag("ingredient") and not self.is_full()


# ── Dispenser Group ───────────────────────────────────────────────────────────

class DispenserGroup(BaseGroup):
    """
    Fixed tile that holds a *template* item.
    Dragging the template spawns a fresh clone; the template stays put.
    Stock is deducted from game_data on each dispense.
    """

    def __init__(self, name, image_path, pos,
                 template_item, game_data, item_id,
                 cost=0, out_group=None):
        super().__init__()
        surf = _load_surface(image_path)
        self.station_block = InteractiveObject(name, pos, {"default": surf})
        self.station_block._layer   = LAYER_STATION
        self.station_block.is_locked = True
        self.add(self.station_block, layer=LAYER_STATION)

        self._template  = template_item
        self._game_data = game_data
        self._item_id   = item_id
        self._cost      = cost
        self._out_group = out_group

        self._template.is_locked = False
        self._template.rect.center = self.station_block.rect.center
        self.add(self._template, layer=LAYER_FOOD)

        self._active_copy = None   # the clone currently being dragged

    # ── Stock helpers ─────────────────────────────────────────────────────────

    def can_dispense(self):
        return (self._game_data.has_stock(self._item_id) and
                self._game_data.money >= self._cost)

    def _do_dispense(self, pos):
        if not self.can_dispense():
            print(f"[DISPENSER] Cannot dispense {self._item_id}: "
                  f"stock={self._game_data.get_stock(self._item_id)}, "
                  f"money={self._game_data.money}")
            return None
        self._game_data.use_stock(self._item_id)
        if self._cost > 0:
            self._game_data.spend_money(self._cost)
        clone = self._template.clone(pos)
        clone.is_locked = False
        print(f"[DISPENSER] Dispensed {clone.name} | "
              f"stock left={self._game_data.get_stock(self._item_id)}")
        return clone

    # ── Input callbacks ───────────────────────────────────────────────────────

    def handle_click(self, sprite):
        pass

    def handle_drag(self, sprite, pos):
        if sprite is not self._template:
            super().handle_drag(sprite, pos)
            return

        # First motion — spawn the clone
        if self._active_copy is None:
            clone = self._do_dispense(pos)
            if clone is None:
                return                         # out of stock; template stays put
            self._active_copy = clone
            clone.current_group = self         # home = this dispenser
            if self._out_group is not None:
                self._out_group.add(clone, layer=LAYER_FOOD)

        # Move the clone; keep template pinned to tile
        self._active_copy.rect.center  = pos
        self._template.rect.center     = self.station_block.rect.center

    def handle_drop(self, sprite, target):
        """Dispenser never accepts drops."""
        return False

    def handle_remove(self, sprite):
        """Called after clone was successfully dropped into another group."""
        if sprite is self._active_copy:
            self._active_copy = None
        sprite.current_group = None

    def handle_snapback(self, sprite):
        """Clone was rejected — destroy it and restore the template."""
        if sprite is self._active_copy:
            sprite.kill()
            self._active_copy = None
            print(f"[DISPENSER] Snapback — clone of {self._item_id} destroyed")
        self._template.rect.center = self.station_block.rect.center
        self._template.is_locked   = False

    def stock_count(self):
        return self._game_data.get_stock(self._item_id)


# ── Station Group ─────────────────────────────────────────────────────────────

class StationGroup(BaseGroup):
    """Generic group that owns a station_block + whatever is placed on it."""

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
        self.add(item, layer=LAYER_FOOD)

    def clear_station(self):
        for item in self.placed_items():
            item.kill()