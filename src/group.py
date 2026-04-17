from settings import *
from interactive import *
class BaseGroup(pygame.sprite.Group):
    """Base class for handling"""
    def handle_click(self, sprite):
        # guaranteed: player clicked this sprite
        if sprite.has_tag("clickable"):
            sprite.on_click()
            print("Base Group handle clicking")

    def handle_drag(self, sprite, pos):
        # guaranteed: this sprite is being dragged
        if sprite.has_tag("draggable"):
            sprite.on_drag(pos)
            # print("Base group handle dragging")

    def handle_drop(self, sprite, target):
        # guaranteed: sprite was dropped on target
        # target.on_drop(sprite)
        print("Base group handle drop")
    
    def handle_remove(self, sprite):
        self.remove(sprite)
        print("Base group handle remove")

    def handle_snapback(self, sprite):
        print("Base group handle snapback")
        print(f"Sprite snapback groups: {sprite.groups()}")

class StackGroup(BaseGroup):
    def __init__(self, name, image_path, pos, max_capacity):
        super().__init__()
        self.station_block = InteractiveObject(name, image_path, pos)
        self.add(self.station_block)
        self.max_capacity = max_capacity
        self.STACK_OVERLAP = 4

    # ── helpers ───────────────────────────────────────────────────────────────

    def placed_items(self):
        return [s for s in self.sprites() if s is not self.station_block]

    def is_full(self):
        return len(self.placed_items()) >= self.max_capacity

    def top_item(self):
        items = self.placed_items()
        return items[-1] if items else None

    def _lock_all_except_top(self):
        """Lock every placed item, then unlock only the top."""
        for item in self.placed_items():
            item.tags.add("locked")
        top = self.top_item()
        if top:
            top.tags.discard("locked")

    # ── restack ───────────────────────────────────────────────────────────────

    # def _restack_all(self):
    #     base_x    = self.station_block.rect.centerx
    #     current_y = self.station_block.rect.bottom

    #     for item in self.placed_items():
    #         current_y -= item.rect.height - self.STACK_OVERLAP
    #         item.rect.centerx = base_x
    #         item.rect.top     = current_y

    #     self._lock_all_except_top()   # always re-evaluate locks after any change

    # ── input callbacks ───────────────────────────────────────────────────────

    def handle_click(self, sprite):
        sprite.on_click()             # locked check already handled in _find_sprite_and_group

    def handle_drag(self, sprite, pos):
        sprite.on_drag(pos)           # same — locked items are never returned by hit-test

    def handle_drop(self, sprite, target):
        print(f"[DROP] {sprite.name} onto {target.name} | can_accept={self.can_accept(sprite)} | full={self.is_full()} | placed={len(self.placed_items())}")
        if self.can_accept(sprite):
            print(f"[DROP] Adding {sprite.name} to {self.__class__.__name__}")
            self.add(sprite)
            print(f"[DROP] Added. Sprites now: {[s.name for s in self.sprites()]}")
            self._restack_all()
            print(f"[DROP] Restack done")
            sprite.on_place()
            print(f"[DROP] on_place done")
            return True
        else:
            print(f"[DROP] REJECTED: {self.__class__.__name__} is full or invalid.")
            return False

    def handle_remove(self, sprite):
        print(f"[REMOVE] {sprite.name} from {self.__class__.__name__} | currently in group: {sprite in self.sprites()}")
        self.remove(sprite)
        print(f"[REMOVE] Removed. Restacking...")
        self._restack_all()
        print(f"[REMOVE] Restack done")

    def handle_snapback(self, sprite):
        print(f"[SNAPBACK] {sprite.name} | already in group: {sprite in self.sprites()}")
        if sprite not in self.sprites():
            self.add(sprite)
        self._restack_all()
        print(f"[SNAPBACK] done")

    def _restack_all(self):
        items = self.placed_items()
        print(f"[RESTACK] {self.__class__.__name__} has {len(items)} placed items: {[s.name for s in items]}")
        base_x    = self.station_block.rect.centerx
        current_y = self.station_block.rect.bottom

        for item in items:
            current_y -= item.rect.height - self.STACK_OVERLAP
            item.rect.centerx = base_x
            item.rect.top     = current_y
            print(f"[RESTACK]   placed {item.name} at y={current_y}")

        self._lock_all_except_top()
        print(f"[RESTACK] lock pass done. top={self.top_item().name if self.top_item() else None}")

    # ── acceptance ────────────────────────────────────────────────────────────

    def can_accept(self, sprite) -> bool:
        return not self.is_full()
                # sprite.rect.centery = self.station_block.rect.centery
    # def _stack(self, sprite):
    #     """Snap sprite onto the top of the current stack."""
    #     items = self.placed_items()
        
    #     if items:
    #         top_sprite = items[-1]             # the current top of the stack
    #         sprite.rect.centerx = top_sprite.rect.centerx
    #         sprite.rect.centerx  = top_sprite.rect.centerx     # sit exactly on top
    #     else:
    #         # nothing on the station yet — land on the station tile itself
    #         sprite.rect.centerx = self.station_block.rect.centerx
    #         sprite.rect.centerx  = self.station_block.rect.centerx
            
    # def _stack(self, sprite):
    #     """Snap sprite onto the top of the current stack."""
    #     stack_index = len(self.placed_items())
    #     sprite.rect.centerx = self.station_block.rect.centerx
    #     sprite.rect.centery = self.station_block.rect.centery - (stack_index * self.stack_offset)
    #     self.add(sprite)

class GrillGroup(StackGroup):
    """Only accepts grillable items. Click flips the patty."""

    # def __init__(self, name, image_path, pos, max_capacity):
    #     super().__init__(name, image_path, pos, max_capacity)


    def can_accept(self, sprite) -> bool:
        return sprite.has_tag("grillable") and not self.is_full()

    def handle_click(self, sprite):
        if sprite is not self.station_block and sprite.has_tag("grillable"):
            sprite.flip()                  # grill-specific: flip on click

    # def handle_remove(self, sprite):
    #     self.remove(sprite)
    #     print("Grill group handle remove")

class PlateGroup(StackGroup):
    """Accepts any ingredient. No special click behavior."""

    def can_accept(self, sprite) -> bool:
        return sprite.has_tag("ingredient") and not self.is_full()
    
class StationGroup(BaseGroup):
    """Owns the station_block sprite + everything placed on it."""
    def __init__(self, name, image_path, pos):
        super().__init__()
        
        # The station_block tile is just another sprite in this group
        self.station_block = InteractiveObject(name, image_path, pos)
        self.add(self.station_block)
        
        self.stack_offset = 5   # pixels per stacked item

    # ── placement ────────────────────────────────────────────────────────────

    def place(self, item):
        """Snap item onto the station_block and track it in the group."""
        stack_index = len(self.placed_items())
        
        item.rect.centerx = self.station_block.rect.centerx
        item.rect.centery = self.station_block.rect.centery - (stack_index * self.stack_offset)
        
        self.add(item)          # group tracks it — no separate list needed

    def placed_items(self):
        """Everything on this station_block except the station_block tile itself."""
        return [s for s in self.sprites() if s is not self.station_block]

    def clear_station(self):
        for item in self.placed_items():
            item.kill()

    # ── input ─────────────────────────────────────────────────────────────────

    def is_draggable(self, sprite):
        return sprite is not self.station_block   # can't drag the station_block itself

    # def handle_drop(self, sprite, target):
    #     if isinstance(target, DroppableTarget):
    #         target.accept_drop(sprite)