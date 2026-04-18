import pygame
from settings import GamePath

class ItemData:
    """Centralized static database. No instance needed."""
    
    DATABASE = {
        # ── Grillables ────────────────────────────────────────────────────────────
        "meat": {
            "type":           "grillable",
            "clickable":      True,
            "draggable":      True,
            "ingredient":     True,
            "grillable":      True,
            "display_name":   "Beef Patty",
            "pixel_height":   12,
            "max_cook_time":  45.0,
            "layer_priority": 2, 
            "state_imgs": {
                "default": "meat.png",
                "raw":     "meat_raw.png",
                "cooked":  "meat_medium.png",
                "burnt":   "meat_burn.png",
            },
        },

        # ── Ingredients ───────────────────────────────────────────────────────────
        "down_bun": {
            "type":           "ingredient",
            "clickable":      True,
            "draggable":      True,
            "ingredient":     True,
            "grillable":      False,
            "display_name":   "Bottom Bun",
            "pixel_height":   15,
            "layer_priority": 1,
            "state_imgs":     {"default": "down_bun.png"},
        },
        "top_bun": {
            "type":           "ingredient",
            "clickable":      True,
            "draggable":      True,
            "ingredient":     True,
            "grillable":      False,
            "display_name":   "Top Bun",
            "pixel_height":   15,
            "layer_priority": 10,
            "state_imgs":     {"default": "top_bun.png"},
        },
        "cheese": {
            "type":           "ingredient",
            "clickable":      True,
            "draggable":      True,
            "ingredient":     True,
            "grillable":      False,
            "display_name":   "Cheddar Slice",
            "pixel_height":   4,
            "layer_priority": 3,
            "state_imgs":     {"default": "cheese.png"},
        },

        # ── Objects ───────────────────────────────────────────────────────────────
        "sauce_bottle": {
            "type":           "object",
            "clickable":      False,
            "draggable":      False,
            "ingredient":     False,
            "grillable":      False,
            "display_name":   "Ketchup Bottle",
            "pixel_height":   40,
            "layer_priority": 2,
            "state_imgs":     {"default": "sauce_bottle.png"},
        },
        "base_plate": {
            "type":           "object",
            "clickable":      False,
            "draggable":      False,
            "ingredient":     False,
            "grillable":      False,
            "display_name":   "Invisible Plate",
            "pixel_height":   0,
            "layer_priority": 1, 
            "state_imgs":     {"default": None}, 
        },

        # ── UI ────────────────────────────────────────────────────────────────────
        "order_ticket": {
            "type":           "ui",
            "clickable":      True,
            "draggable":      False,
            "ingredient":     False,
            "grillable":      False,
            "display_name":   "Customer Order",
            "pixel_height":   100,
            "layer_priority": 4, 
            "state_imgs":     {"default": "order_ticket.png"},
        },
    }

    @staticmethod
    def get_item(item_name):
        return ItemData.DATABASE.get(item_name)

    @staticmethod
    def get_prop(item_name, prop_name, default_value=False):
        item = ItemData.get_item(item_name)
        if not item: return default_value
        return item.get(prop_name, default_value)

    @staticmethod
    def get_img_name(item_name, state="default"):
        """Static retrieval of image filename."""
        item = ItemData.get_item(item_name)
        if not item or "state_imgs" not in item:
            return None
        return item["state_imgs"].get(state)

    @staticmethod
    def get_state_img(item_name, state="default"):
        """Alias for get_img_name — kept for backward compatibility."""
        return ItemData.get_img_name(item_name, state)

    @staticmethod
    def load_img(img_name, item_type):
        """Logic-based loading: finds the folder based on the item type."""
        if img_name is None:
            # Transparent fallback for invisible objects
            surf = pygame.Surface((64, 64), pygame.SRCALPHA)
            surf.fill((0, 0, 0, 0))
            return surf
            
        # ── Logic to choose path ──
        if item_type == "grillable":
            path = GamePath.get_grillable(img_name)
        elif item_type =="ingredient":
            path = GamePath.get_ingredients(img_name)
        elif item_type == "ui":
            path = GamePath.get_ui(img_name)
        elif item_type == "station":
            path = GamePath.get_station(img_name)
        elif item_type == "object":
            path = GamePath.get_object(img_name)
        else:
            path = GamePath.get_path("assets", img_name)

        try:
            return pygame.image.load(path).convert_alpha()
        except Exception as e:
            print(f"[ITEMDATA] Error loading {path}: {e}")
            fallback = pygame.Surface((32, 32))
            fallback.fill((255, 0, 255)) 
            return fallback