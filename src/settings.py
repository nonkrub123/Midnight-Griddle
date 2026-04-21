import pygame
import sys
import os
import math

WINDOW_WIDTH, WINDOW_HEIGHT = 1920, 1080
TILE_SIZE = 64
FPS = 60

CLICK_THRESHOLD = 0.09
GAME_W, GAME_H  = 1920, 1080

LAYER_BACKGROUND = 0
LAYER_STATION    = 1
LAYER_FOOD       = 2
LAYER_DRAGGING   = 3
LAYER_UI         = 4


class GamePath:
    @staticmethod
    def get_path(*path_parts):
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, *path_parts)

    @staticmethod
    def get_grillable(path_parts):
        return GamePath.get_path("assets", "grillable", path_parts)

    @staticmethod
    def get_ui(path_parts):
        return GamePath.get_path("assets", "ui", path_parts)

    @staticmethod
    def get_ingredients(path_parts):
        return GamePath.get_path("assets", "ingredients", path_parts)

    @staticmethod
    def get_station(path_parts):
        return GamePath.get_path("assets", "station", path_parts)

    @staticmethod
    def get_object(path_parts):
        return GamePath.get_path("assets", "object", path_parts)


# ── Item Database ─────────────────────────────────────────────────────────────
# Single source of truth for every placeable / dispensable item in the game.
#
# Keys per type
# ─────────────
# ALL items:
#   type           str   "grillable" | "ingredient" | "object" | "ui"
#   tags           list  pygame-sprite tag strings
#   display_name   str   human-readable label
#   pixel_height   int   logical height used for stacking overlap
#   layer_priority int   draw-order inside a LayeredUpdates group
#
# grillable only:
#   max_cook_time  float seconds to reach "cooked" threshold (50 %)
#   state_imgs     dict  {"raw": filename, "cooked": filename, "burnt": filename}
#                        filenames resolved via GamePath.get_ingredients()
#
# ingredient only:
#   img            str   single image filename (ingredients folder)
#
# object only:
#   img            str   single image filename (ingredients folder)
#   contains       str   item_id this object can dispense (SauceBottle)
#
# Pricing (optional, used by GameData / shop):
#   buy_price      int   cost to restock from shop
#   sell_price     int   revenue when served to a customer
# Assume these are imported from your settings
# LAYER_BACKGROUND, LAYER_STATION, LAYER_FOOD, LAYER_DRAGGING, LAYER_UI

# Assuming these are in settings.py, or import them if this is a separate file:
# LAYER_BACKGROUND = 0
# LAYER_STATION = 1
# LAYER_FOOD = 2
# LAYER_DRAGGING = 3
# LAYER_UI = 4