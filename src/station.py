from settings import *
from gamedata import *
from interactive import *

class Sprite_Interactive(pygame.sprite.Sprite):
    def __init__(self, pos, path, x, y):
        # 1. Initialize the parent Sprite and add to group automatically
        # super().__init__(ui_group) 
        self._layer = LAYER_UI

        # 2. Load the 'Cozy' asset
        self.image = pygame.image.load(path).convert_alpha()
        self.rect = self.image.get_rect(topleft=pos)

    def is_dragable(self):
        return False
    
    def on_click(self):
        self.callback()
    
    def on_place(self, pos):
        print("On place")
        pass

    def on_drag(self, pos):
        pass

class StationManager:
    def __init__(self, screen, on_switch_callback):
        self.__screen = screen
        self.__on_switch = on_switch_callback  # instead of holding GameManager

        self.__nav_group = BaseGroup()
        self.all_groups = [self.__nav_group]

        self.stations = {
            "order": Station(self.__screen, GamePath.get_station("test.png")),
            "grill": GrillStation(self.__screen, GamePath.get_station("test2.jpg")),
        }
        self.current_station = "order"

        self.create_nav_buttons()

    def create_nav_buttons(self):
        button1 = UIButton("button1", GamePath.get_ui("20.png"), (10, 550), lambda: self.switch_station("order"))
        button2 = UIButton("button2", GamePath.get_ui("20.png"), (120, 550), lambda: self.switch_station("grill"))
        self.__nav_group.add(button1, button2)
        # UIButton((10, 550),  "20.png", self.__nav_group, lambda: self.switch_station("order"))
        # UIButton((120, 550), "20.png", self.__nav_group, lambda: self.switch_station("grill"))

    def switch_station(self, target):
        self.current_station = target
        self.__on_switch(self.get_all_sprites(), self.get_all_groups())  # notify GameManager with new sprites

    def get_all_sprites(self):
        """Returns every sprite GameManager needs to know about."""
        all_sprites = pygame.sprite.LayeredUpdates()

        all_sprites.add(self.__nav_group)
        # Nav buttons are always present
        for sprite in self.__nav_group:
            all_sprites.add(sprite)

        # Active station's sprites
        active = self.stations[self.current_station]
        for sprite in active.get_sprites():
            all_sprites.add(sprite)

        return all_sprites

    def get_all_groups(self):
        return self.all_groups
    
    def update(self, dt):
        for station in self.stations.values():
            station.update(dt)

    def render_ui(self):
        self.stations[self.current_station].draw()
        self.__nav_group.draw(self.__screen)

class Station:
    def __init__(self, screen, bg_image_path):
        self.screen = screen
        self.background = pygame.image.load(bg_image_path).convert()
        self.items  = pygame.sprite.Group()
        self.blocks = pygame.sprite.Group()

    def get_sprites(self):
        """Station returns its own sprites — Station's responsibility."""
        all_sprites = pygame.sprite.LayeredUpdates()
        all_sprites.add(self.items)
        all_sprites.add(self.blocks)
        return all_sprites

    def update(self, dt):
        for item in self.items:
            if hasattr(item, 'update'):
                item.update(dt)

    def draw(self):
        self.screen.blit(self.background, (0, 0))
        self.items.draw(self.screen)
        self.blocks.draw(self.screen)
        
class GrillStation(Station):
    def __init__(self, screen, bg_image_path):
        super().__init__(screen, bg_image_path)
        self.items.add(InteractiveIngredient("bun2", GamePath.get_ingredients("bun2.png"), (10, 10)))

class Order:
    pass

class Ingredient:
    pass

class CustomerManager:
    pass

class Customer:
    pass

