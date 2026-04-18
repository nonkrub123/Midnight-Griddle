"""
factory.py
──────────
ItemFactory: builds InteractiveObject subclass instances from ITEM_DATABASE.

Usage
─────
    factory = ItemFactory()
    sprite  = factory.create("meat_patty", pos=(300, 200))
    sprite  = factory.create("cheese",     pos=(500, 200))

Images are loaded once and cached (keyed by filename) so repeated calls for
the same item_id don't hit the disk again.
"""

from settings import *
from interactive import *


from interactive import GrillableItem, IngredientItem, InteractiveObject
from itemdata import ItemData

class ItemFactory:
    def __init__(self):
        self._img_cache = {}

    def create(self, name, pos):
        data = ItemData.get_item(name)
        if not data: return None

        item_type = data.get("type")
        
        # Load all state images into Surfaces using ItemData logic
        loaded_surfaces = {}
        for state, file_name in data["state_imgs"].items():
            # Cache key includes type to avoid collisions
            cache_key = f"{item_type}_{file_name}"
            
            if cache_key not in self._img_cache:
                self._img_cache[cache_key] = ItemData.load_img(file_name, item_type)
            
            loaded_surfaces[state] = self._img_cache[cache_key]

        # Return instance based on type
        if item_type == "grillable":
            return GrillableItem(name, pos, loaded_surfaces)
        elif item_type == "ingredient":
            return IngredientItem(name, pos, loaded_surfaces["default"])
        else:
            # Generic fallback for 'ui' or 'object'
            return InteractiveObject(name, pos, loaded_surfaces["default"])

    def create_invisible_plate(self, name, pos, size):
            """
            Creates an invisible drop zone/plate of a specific size.
            :param name: String identifier (e.g., "plate_1")
            :param pos: Tuple (x, y) for the center position
            :param size: Tuple (width, height) in pixels (e.g., (120, 120))
            """
            # 1. Generate the transparent surface
            invisible_surf = pygame.Surface(size, pygame.SRCALPHA)
            invisible_surf.fill((0, 0, 0, 0))
            
            # 2. Package it in the same dictionary format the other objects use
            # (Using "default" and "raw" so it doesn't crash if the object looks for a specific key)
            loaded_surfaces = {
                "default": invisible_surf
            }
            
            # 3. Create and return the base object
            return InteractiveObject(name, pos, loaded_surfaces)