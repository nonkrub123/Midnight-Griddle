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
LAYER_STATION = 1
LAYER_FOOD = 2
LAYER_DRAGGING = 3
LAYER_UI = 4

class GamePath:
    @staticmethod
    def get_path(*path_parts):
        # Joins the base directory with any number of folder/file names
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        return os.path.join(base, *path_parts)
    
    @staticmethod
    def get_player(path_parts):
        return GamePath.get_path("assets", "player", path_parts)

    @staticmethod
    def get_ui(path_parts):
        return GamePath.get_path("assets", "ui", path_parts)

    @staticmethod
    def get_ingredients(path_parts):
        return GamePath.get_path("assets", "ingredients", path_parts)
    
    @staticmethod
    def get_station(path_parts):
        return GamePath.get_path("assets", "station", path_parts)