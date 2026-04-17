from settings import *
from gamedata import *
from interactive import *
from group import *

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

    def get_active_station(self):
        return self.stations[self.current_station]
    
    def switch_station(self, target):
        self.current_station = target
        self.__on_switch(self.get_all_sprites(), self.get_all_groups())  # notify GameManager with new sprites

    def get_all_sprites(self):
        all_sprites = self.get_active_station().get_all_sprites()
        for sprite in self.__nav_group:
            all_sprites.add(sprite)
        return all_sprites

        # Active station's sprites
        # active = self.stations[self.current_station]
        # for sprite in active.get_all_sprites():
        #     all_sprites.add(sprite)

        return all_sprites

    def get_all_groups(self):
        return self.all_groups + self.get_active_station().get_all_groups()
    
    def update(self, dt):
        for station in self.stations.values():
            station.update(dt)

    def render_ui(self):
        self.stations[self.current_station].draw()
        self.__nav_group.draw(self.__screen)

class Station:
    def __init__(self, screen, bg_image_path):
        self.screen      = screen
        self.background  = pygame.image.load(bg_image_path).convert()
        
        self.all_sprites = pygame.sprite.LayeredUpdates()
        self.all_groups  = []

    def add_sprites_group(self, group, sprites):
        group.add(*sprites)

    def register_group(self, group):
        self.all_groups.append(group)          # [grill, plate, dispenser, ...]
        print(f"Registered: Appended {group} to all groups")
        self.all_sprites.add(group.sprites())

    def get_all_sprites(self):
        return self.all_sprites

    def get_all_groups(self):
        return self.all_groups                 # → [GrillGroup, PlateGroup, ...]

    def update(self, dt):
        self.all_sprites.update(dt)

    def draw(self):
        self.screen.blit(self.background, (0, 0))
        self.all_sprites.draw(self.screen)

class GrillStation(Station):
    def __init__(self, screen, bg_image_path):
        super().__init__(screen, bg_image_path)

        self.grill = GrillGroup("grill", GamePath.get_ingredients("meat_burn.png"), (100, 100), max_capacity=2)
        self.plate = GrillGroup("plate", GamePath.get_ingredients("bun2.png"), (400, 100), max_capacity=20)
        
        self.other_group = BaseGroup()
        item = InteractiveGrillable("meat", GamePath.get_ingredients("meat.png"), (600, 100))
        item2 = InteractiveGrillable("meat", GamePath.get_ingredients("meat_medium.png"), (1000, 100))
        self.other_group.add(item, item2)      # add item BEFORE registering

        self.register_group(self.grill)
        self.register_group(self.plate)
        self.register_group(self.other_group)  # now has item in it

    # def get_all_groups(self):
    #     return self.all_groups   # → [self.grill, self.plate]
    
