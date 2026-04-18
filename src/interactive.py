from settings import *
import pygame
import copy
from itemdata import ItemData


class InteractiveObject(pygame.sprite.Sprite):
    def __init__(self, name, pos, image):
        super().__init__()
        self.name = name

        self.image = image["default"] if isinstance(image, dict) else image
        self.rect  = self.image.get_rect(center=pos)

        # Which group "owns" this sprite — set by handle_drag / handle_drop
        self.current_group = None
        self.is_locked     = False

        # Draw layer — used by InputHandler to lift sprite while dragging
        self._layer = LAYER_FOOD

        # Smooth movement
        self.target_pos    = None
        self.start_pos     = pygame.Vector2(pos)
        self.move_timer    = 0
        self.move_duration = 0

    # ── Movement ──────────────────────────────────────────────────────────────

    def set_target(self, pos, duration=0.2):
        self.target_pos    = pygame.Vector2(pos)
        self.start_pos     = pygame.Vector2(self.rect.center)
        self.move_timer    = 0
        self.move_duration = duration

    def update(self, dt=0):
        if self.target_pos:
            self._move(dt)

    def _move(self, dt):
        self.move_timer += dt
        t = self.move_timer / self.move_duration if self.move_duration > 0 else 1.0
        if t >= 1.0:
            self.rect.center = (int(self.target_pos.x), int(self.target_pos.y))
            self.target_pos  = None
        else:
            new_pos = self.start_pos.lerp(self.target_pos, t)
            self.rect.center = (int(new_pos.x), int(new_pos.y))

    # ── Tag lookup ────────────────────────────────────────────────────────────

    def has_tag(self, tag):
        """
        'locked' is a live attribute, not a DB property — check it directly.
        Everything else is looked up in ItemData.
        """
        if tag == "locked":
            return self.is_locked
        return ItemData.get_prop(self.name, tag, False)

    # ── Clone ─────────────────────────────────────────────────────────────────

    def clone(self, pos):
        """Return a fresh copy of this sprite placed at *pos*."""
        new = copy.copy(self)
        new.rect          = self.image.get_rect(center=pos)
        new.start_pos     = pygame.Vector2(pos)
        new.target_pos    = None
        new.move_timer    = 0
        new.is_locked     = False
        new.current_group = None
        # Re-init the sprite so it has no group memberships
        pygame.sprite.Sprite.__init__(new)
        new.image = self.image
        new.rect  = self.image.get_rect(center=pos)
        new._layer = self._layer
        return new

    # ── Input callbacks ───────────────────────────────────────────────────────

    def on_click(self):       pass
    def on_drag(self, pos):   self.rect.center = pos
    def on_place(self):       pass
    def on_snapback(self):    pass


# ── UI Button ─────────────────────────────────────────────────────────────────

class UIButton(InteractiveObject):
    def __init__(self, name, image_path, pos, callback):
        img = pygame.image.load(image_path).convert_alpha()
        super().__init__(name, pos, {"default": img})
        self._layer = LAYER_UI
        self.callback = callback

    def has_tag(self, tag):
        # UIButton is not in ItemData — answer directly without a DB lookup
        if tag == "clickable":  return True
        if tag == "draggable":  return False
        if tag == "locked":     return self.is_locked
        return False

    def on_click(self):
        self.callback()


# ── Grillable Item ────────────────────────────────────────────────────────────

class GrillableItem(InteractiveObject):
    STATES           = ("raw", "cooked", "burnt")
    COOKED_THRESHOLD = 0.50
    BURNT_THRESHOLD  = 1.50

    def __init__(self, name, pos, images: dict):
        self.max_cook_time  = ItemData.get_prop(name, "max_cook_time", 10.0)
        self._cook_state    = "raw"
        self._time_on_grill = 0.0
        self.state_images   = images
        super().__init__(name, pos, images)

    @property
    def cook_state(self):
        return self._cook_state

    @cook_state.setter
    def cook_state(self, value):
        assert value in self.STATES, f"Invalid cook state: {value}"
        if value != self._cook_state:
            self._cook_state = value
            self.image = self.state_images[value]

    def on_cook(self, dt):
        if self._cook_state == "burnt":
            return
        self._time_on_grill += dt
        new_state = self._evaluate_cook_state()
        self.cook_state = new_state
        self.image = self.state_images[self._cook_state]  # always sync

    def _evaluate_cook_state(self):
        ratio = self._time_on_grill / self.max_cook_time
        if   ratio >= self.BURNT_THRESHOLD:  return "burnt"
        elif ratio >= self.COOKED_THRESHOLD: return "cooked"
        else:                                return "raw"

    def cook_progress(self):
        return min(self._time_on_grill / (self.max_cook_time * self.BURNT_THRESHOLD), 1.0)


# ── Ingredient Item ───────────────────────────────────────────────────────────

class IngredientItem(InteractiveObject):
    def __init__(self, name, pos, image):
        # image may arrive as a Surface (from factory) or a dict — normalise to dict
        if isinstance(image, pygame.Surface):
            image = {"default": image}
        super().__init__(name, pos, image)


# ── Base Plate ────────────────────────────────────────────────────────────────

class BasePlate(InteractiveObject):
    """
    Drop-zone anchor built from ItemData("base_plate").
    If state_imgs["default"] is None, an invisible transparent surface is used.
    Always reports draggable=False and clickable=False.
    """

    def __init__(self, name, pos, image):
        super().__init__(name, pos, image)

    def has_tag(self, tag):
        if tag == "draggable": return False
        if tag == "clickable": return False
        return super().has_tag(tag)