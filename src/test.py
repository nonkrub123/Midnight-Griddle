import pygame
from settings import *
from interactive import *

# 1. Initialize pygame
pygame.init()

# 2. Create a display surface (even if you don't use it yet)
# This allows .convert_alpha() to work.
screen = pygame.display.set_mode((800, 600))

# 3. Now you can create your object
ui = InteractiveObject("button", GamePath.get_ui("20.png"), (0,0))

print(f"Has 'clickable' tag: {ui.has_tag('clickable')}")
print(f"Has 'draggable' tag: {ui.has_tag('draggable')}")