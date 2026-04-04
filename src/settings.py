import pygame
import sys
import os
import math
WINDOW_WIDTH, WINDOW_HEIGHT = 1920, 1080
TILE_SIZE = 64
FPS = 60

TILESHEETS = []
TILESMAPDATA = [
    [20, 20, 20, 20, 20, 20, 20, 20, 20, 20],
    [20, 1, 1, 1, 1, 1, 1, 1, 1, 20],
    [20, 1, 1, 1, 1, 1, 1, 1, 1, 20],
    [20, 1, 1, 1, 1, 1, 1, 1, 1, 20],
    [20, 1, 1, 1, 1, 1, 1, 1, 1, 20],
    [20, 1, 1, 1, 1, 1, 1, 1, 1, 20],
    [20, 1, 1, 1, 1, 1, 1, 1, 1, 20],
    [20, 1, 1, 1, 1, 1, 1, 1, 1, 20],
    [20, 1, 1, 1, 1, 1, 1, 1, 1, 20],
    [20, 20, 20, 20, 20, 20, 20, 20, 20, 20]
]
# TILESMAPDATA = [[1 for x in range(40)] for x in range(40)]
# Tile map data is a dict which contain
# TILESDATA = {1:{"collision": True, "name": "floor"},
#              }
# print(TILESMAPDATA)
def get_path(*path_parts):
    # Joins the base directory with any number of folder/file names
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, *path_parts)