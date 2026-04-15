from settings import *

# ── Base interactive object — knows nothing about groups ────────────────────

class InteractiveObject(pygame.sprite.Sprite):
    def __init__(self, name, image_path, pos, tags=None):
        super().__init__()
        self._layer  = LAYER_FOOD
        self.name    = name
        self.tags    = set(tags or ["clickable"])

        self.image   = pygame.image.load(image_path).convert_alpha()
        self.rect    = self.image.get_rect(topleft=pos)

    def has_tag(self, tag):
        return tag in self.tags

    def on_click(self):    pass
    def on_drag(self, pos): pass
    def on_place(self):    pass
    def update(self): pass

class UIButton(InteractiveObject):
    def __init__(self, name, image_path, pos, callback, tags=None):
        
        # 1. Call the Parent (InteractiveObject) constructor
        # We pass "button" as the name and ensure it has the "clickable" tag
        super().__init__(name, image_path, pos, tags)
        
        # 2. Set the specific UI layer and store callback
        self._layer = LAYER_UI
        self.callback = callback

    # Overriding the parent method
    def on_click(self):
        self.callback()

class InteractiveIngredient(InteractiveObject):
    def __init__(self, name, image_path, pos, tags=None):
        tags = set(tags or ["draggable", "clickable"])
        super().__init__(name, image_path, pos, tags)

    def dropped_on_grill(self, grill):
        grill.place_patty(self)

    def dropped_on_tray(self, tray):
        tray.burger_stack.add(self)

class InteractiveGrillable(InteractiveIngredient):
    def __init__(self, name, image_path, pos, all_sprites, tags=None):
        # Auto-inject "grillable" tag
        tags = set(tags or ["draggable", "clickable"]) | {"grillable"}
        super().__init__(name, image_path, pos, all_sprites, tags)
    
class StationBlock(pygame.sprite.Sprite):
    """The visual station tile — just a sprite, no group logic here."""
    def __init__(self, name, image_path, pos):
        super().__init__()
        self._layer = LAYER_STATION
        self.name   = name
        self.image  = pygame.image.load(image_path).convert_alpha()
        self.rect   = self.image.get_rect(topleft=pos)

class BaseGroup(pygame.sprite.Group):
    def handle_click(self, sprite):
        # guaranteed: player clicked this sprite
        if sprite.has_tag("clickable"):
            sprite.on_click()

    def handle_drag(self, sprite, pos):
        # guaranteed: this sprite is being dragged
        if sprite.has_tag("draggable"):
            sprite.on_drag()

    def handle_drop(self, sprite, target):
        # guaranteed: sprite was dropped on target
        target.on_drop(sprite)

class StationGroup(BaseGroup):
    """Owns the station sprite + everything placed on it."""
    def __init__(self, name, image_path, pos):
        super().__init__()
        
        # The station tile is just another sprite in this group
        self.station = StationBlock(name, image_path, pos)
        self.add(self.station)
        
        self.stack_offset = 5   # pixels per stacked item

    # ── placement ────────────────────────────────────────────────────────────

    def place(self, item):
        """Snap item onto the station and track it in the group."""
        stack_index = len(self.placed_items())
        
        item.rect.centerx = self.station.rect.centerx
        item.rect.centery = self.station.rect.centery - (stack_index * self.stack_offset)
        
        self.add(item)          # group tracks it — no separate list needed

    def placed_items(self):
        """Everything on this station except the station tile itself."""
        return [s for s in self.sprites() if s is not self.station]

    def clear_station(self):
        for item in self.placed_items():
            item.kill()

    # ── input ─────────────────────────────────────────────────────────────────

    def is_draggable(self, sprite):
        return sprite is not self.station   # can't drag the station itself

    # def handle_drop(self, sprite, target):
    #     if isinstance(target, DroppableTarget):
    #         target.accept_drop(sprite)