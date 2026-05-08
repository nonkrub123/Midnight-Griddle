import pygame
import os

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
    
    @staticmethod
    def get_gamedata(path_parts):
        return GamePath.get_path("data", "gamedata", path_parts)
    
    @staticmethod
    def get_statdata(path_parts):
        return GamePath.get_path("data", "gamedata", path_parts)

    @staticmethod
    def load_img(img_name):
        """Logic-based loading: finds the folder based on the item type."""
        try:
            return pygame.image.load(img_name).convert_alpha()
        except Exception as e:
            print(f"[GAMEPATH] Error loading {img_name}: {e}")
            fallback = pygame.Surface((32, 32))
            fallback.fill((255, 0, 255)) 
            return fallback