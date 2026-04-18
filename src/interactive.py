from settings import *
 
import pygame
import copy
from settings import *
from itemdata import ItemData  # Make sure this import matches your filename!

class InteractiveObject(pygame.sprite.Sprite):
    def __init__(self, name, pos, image: dict):
        super().__init__()
        self.name = name
        
        # 1. image are passed infrom the Factory
        self.image = image["default"] if isinstance(image, dict) else image
        self.rect = self.image.get_rect(center=pos)
        
        # 3. New Foundation Attributes
        self.current_group = None  # Track which group currently "owns" this object
        self.is_locked = False     # If True, InputHandler ignores this object
        
        # 4. Movement Foundation
        self.target_pos = None     # Where we want to go
        self.start_pos = pygame.Vector2(pos)
        self.move_timer = 0
        self.move_duration = 0

    def set_target(self, pos, duration=0.2):
        """Call this instead of setting rect.center directly."""
        self.target_pos = pygame.Vector2(pos)
        self.start_pos = pygame.Vector2(self.rect.center)
        self.move_timer = 0
        self.move_duration = duration

    def update(self, dt):
        """Standard update called by the Group."""
        if self.target_pos:
            self.move(dt)
 
    def move(self, dt):
        self.move_timer += dt
        
        # Calculate completion (0.0 to 1.0)
        t = self.move_timer / self.move_duration
        if t >= 1.0:
            # We arrived!
            self.rect.center = (self.target_pos.x, self.target_pos.y)
            self.target_pos = None
        else:
            # Move a percentage of the way
            # New Position = Start + (Target - Start) * t
            new_pos = self.start_pos.lerp(self.target_pos, t)
            self.rect.center = (new_pos.x, new_pos.y)
            
    def has_tag(self, tag):
        """
        The Magic Bridge: Instead of storing a set of strings, 
        we instantly look up the boolean value in our database.
        """
        return ItemData.get_prop(self.name, tag, False)

    # ── Unchanged Callbacks ──
    def on_click(self):     pass
    def on_drag(self, pos): self.rect.center = pos
    def on_place(self):     pass
    def on_snapback(self):  pass
 
class UIButton(InteractiveObject):
    def __init__(self, name, image_path, pos, callback):
        # Buttons aren't in the DB — load the image here and wrap in a dict
        img = pygame.image.load(image_path).convert_alpha()
        super().__init__(name, pos, img)
        self._layer = LAYER_UI
        self.callback = callback

    def on_click(self):
        self.callback()
 
 
# ── Grillable Item ────────────────────────────────────────────────────────────

class GrillableItem(InteractiveObject):
    """
    Cook state is driven entirely by time on the grill:
      - raw:    _time_on_grill <  50% of max_cook_time
      - cooked: _time_on_grill >= 50% and < 150%
      - burnt:  _time_on_grill >= 150%
    """

    STATES = ("raw", "cooked", "burnt")
    COOKED_THRESHOLD = 0.50   # 50 %  → becomes cooked
    BURNT_THRESHOLD  = 1.50   # 150 % → becomes burnt

    def __init__(self, name, pos, images: dict):  # ← accept images
        self.max_cook_time  = ItemData.get_prop(name, "max_cook_time", 10.0)
        self._cook_state    = "raw"
        self._time_on_grill = 0.0
        self._is_grilling   = False
        self.state_images   = images  # ← just use what factory gave us
        super().__init__(name, pos, self.state_images)

    # ── Cook state ────────────────────────────────────────────────────────────

    @property
    def cook_state(self):
        return self._cook_state

    @cook_state.setter
    def cook_state(self, value):
        assert value in self.STATES, f"Invalid cook state: {value}"
        if value != self._cook_state:
            self._cook_state = value
            self.image = self.state_images[value]
            print(f"[GRILL] {self.name} → {value}  (t={self._time_on_grill:.2f}s / max={self.max_cook_time}s)")

    def _evaluate_cook_state(self):
        ratio = self._time_on_grill / self.max_cook_time
        if ratio >= self.BURNT_THRESHOLD:
            return "burnt"
        elif ratio >= self.COOKED_THRESHOLD:
            return "cooked"
        else:
            return "raw"

    # ── Lifecycle callbacks ───────────────────────────────────────────────────

    def on_place(self):
        self._is_grilling = True

    def on_snapback(self):
        self._is_grilling = False

    def update(self, dt=0):
        if not self._is_grilling or self._cook_state == "burnt":
            return 
        
        self._time_on_grill += dt
        self.cook_state = self._evaluate_cook_state() 

    def cook_progress(self):
        return min(self._time_on_grill / (self.max_cook_time * self.BURNT_THRESHOLD), 1.0)


# ── Ingredient Item ───────────────────────────────────────────────────────────

class IngredientItem(InteractiveObject):
    def __init__(self, name, pos, images): 
        super().__init__(name, pos, images)


# ── Sauce Bottle ──────────────────────────────────────────────────────────────

# class SauceBottle(InteractiveObject):
#     """A stationary bottle. Click spawns its `contains` ingredient at the bottle pos."""

#     def __init__(self, name, pos, images: dict, contains_id, factory, target_group):
#         super().__init__(name, pos, images)
#         self.contains_id  = contains_id
#         self.factory      = factory
#         self.target_group = target_group

#     def on_click(self):
#         sprite = self.factory.create(self.contains_id, self.rect.topleft)
#         if sprite:
#             self.target_group.add(sprite)