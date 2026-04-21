from core.settings import *
from core.itemdata import ItemData
import pygame
import copy


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


# ── Image resolver (shared by UIButton / StaticUI) ────────────────────────────

def _resolve_image(image) -> pygame.Surface:
    """
    Accepts a file path, a pygame.Surface, or a {"default": Surface} dict
    and returns a Surface. Used by UIButton and any callers that want flexible
    image input.
    """
    if isinstance(image, str):
        return GamePath.load_img(image)
    if isinstance(image, pygame.Surface):
        return image
    if isinstance(image, dict):
        # Prefer "default", otherwise first available surface
        return image.get("default") or next(iter(image.values()))
    raise TypeError(f"Expected path / Surface / dict, got {type(image).__name__}")


# ── StaticUI ──────────────────────────────────────────────────────────────────

class StaticUI(pygame.sprite.Sprite):
    """
    Locked, non-interactive display sprite. The base for every bit of UI that
    just sits there and occasionally swaps its image — panels, dividers,
    labels, badges, feedback banners, HUD text, etc.

    Parameters
    ----------
    image   : Surface | path | {"default": Surface}
    pos     : (x, y)  — interpreted per `anchor`
    layer   : draw layer (default LAYER_UI)
    anchor  : any pygame.Rect keyword — "topleft" (default), "center",
              "midtop", "bottomright", ... the chosen anchor is also used
              when set_surface() swaps the image later.
    name    : optional identifier (no ItemData lookup is performed)

    Examples
    ────────
        panel = StaticUI(panel_surface, (100, 50), layer=1)
        badge = StaticUI(stock_surface, center_pos, anchor="center")

        badge.set_surface(new_stock_surface)   # keeps anchor & pos
    """

    def __init__(self, image, pos,
                 layer: int = LAYER_UI,
                 anchor: str = "topleft",
                 name: str = "static_ui"):
        super().__init__()
        self.name      = name
        self.image     = _resolve_image(image)
        self._pos      = pos
        self._anchor   = anchor
        self.rect      = self.image.get_rect(**{anchor: pos})
        self._layer    = layer
        self.is_locked = True

    def set_surface(self, image, pos=None, anchor=None):
        """Swap image and re-anchor. Keeps the original pos/anchor if not given."""
        if pos    is not None: self._pos    = pos
        if anchor is not None: self._anchor = anchor
        self.image = _resolve_image(image)
        self.rect  = self.image.get_rect(**{self._anchor: self._pos})

    def has_tag(self, tag):
        # StaticUI is always locked and never participates in ItemData lookups.
        return tag == "locked"

    # No-ops so accidental invocation is harmless.
    def on_click(self):    pass
    def on_snapback(self): pass


# ── UI Button ─────────────────────────────────────────────────────────────────

class UIButton(InteractiveObject):
    """
    Clickable, non-draggable UI element. Flexible image input:

        UIButton("nav_order", "assets/ui/20.png",        (10, 600), cb)   # path
        UIButton("accept",    theme.button_surface(...), (860, 700), cb,
                 anchor="topleft")                                        # surface

    Parameters
    ----------
    image  : path | Surface | {"default": Surface}
    pos    : (x, y) — interpreted per `anchor`
    anchor : "center" (default — legacy behaviour) or any Rect keyword
    layer  : draw layer (default LAYER_UI)
    """

    def __init__(self, name, image, pos, callback,
                 anchor: str = "center",
                 layer:  int = LAYER_UI):
        surf = _resolve_image(image)
        super().__init__(name, pos, {"default": surf})

        # InteractiveObject forces a center rect; override if caller wanted else.
        if anchor != "center":
            self.rect = surf.get_rect(**{anchor: pos})

        self._layer   = layer
        self.callback = callback

    def has_tag(self, tag):
        # UIButton is not in ItemData — answer directly without a DB lookup
        if tag == "clickable":  return True
        if tag == "draggable":  return False
        if tag == "locked":     return self.is_locked
        return False

    def on_click(self):
        if self.callback:
            self.callback()


# ── Grillable Item ────────────────────────────────────────────────────────────

class GrillableItem(InteractiveObject):
    STATES           = ("precook", "raw", "cooked", "burnt")
    COOKED_THRESHOLD = 0.50
    BURNT_THRESHOLD  = 1.50

    def __init__(self, name, pos, images: dict):
        self.max_cook_time  = ItemData.get_prop(name, "max_cook_time", 10.0)
        self._cook_state    = "precook"
        self._time_on_grill = 0.0
        self.state_images   = images
        super().__init__(name, pos, images)
        self.image = images["precook"] if isinstance(images, dict) else images
        self._last_tint_step = -1
        self._tinted_image   = None

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
        # Only tint once cooking has actually started
        if self._cook_state != "precook":
            self.image = self._get_tinted_image()

    def _evaluate_cook_state(self):
        ratio = self._time_on_grill / self.max_cook_time
        if   ratio >= self.BURNT_THRESHOLD:  return "burnt"
        elif ratio >= self.COOKED_THRESHOLD: return "cooked"
        else:                                return "raw"

    def cook_progress(self):
        return min(self._time_on_grill / (self.max_cook_time * self.BURNT_THRESHOLD), 1.0)

    def _get_tinted_image(self):
        progress = self.cook_progress()
        step     = int(progress * 10) / 10
        if step == self._last_tint_step:
            return self._tinted_image

        self._last_tint_step = step
        state_key = self._cook_state if self._cook_state in ("raw","cooked","burnt") else "raw"
        base      = self.state_images[state_key].copy()
        # 255 = no change, 0 = black. Multiply RGB channels only, alpha untouched
        brightness = int((1.0 - step * 0.7) * 255)  # darkens to 30% at max
        dark_surf  = pygame.Surface(base.get_size(), pygame.SRCALPHA)
        dark_surf.fill((brightness, brightness, brightness, 255))
        base.blit(dark_surf, (0, 0), special_flags=pygame.BLEND_RGBA_MULT)

        self._tinted_image = base
        return base


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