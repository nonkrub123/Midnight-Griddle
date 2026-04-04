from settings import *
from gamedata import *

class UIButton(pygame.sprite.Sprite):
    def __init__(self, pos, image_name, ui_group, callback):
        # 1. Initialize the parent Sprite and add to group automatically
        super().__init__(ui_group) 
        
        # 2. Load the 'Cozy' asset
        self.image = pygame.image.load(get_path('assets', 'ui', image_name)).convert_alpha()
        self.rect = self.image.get_rect(topleft=pos)
        
        # 3. Store the action to perform on click
        self.callback = callback

    def handle_events(self, event_list):
        for event in event_list:
            if event.type == pygame.MOUSEBUTTONDOWN:
                # print(f"BUTTON CLICKED! Callback is: {self.callback}")
                if self.rect.collidepoint(event.pos):
                    if callable(self.callback):
                        self.callback()
                    else:
                        print("ERROR: Callback is not a function!")
    # def update(self, event_list):
    #     for event in event_list:
    #         if event.type == pygame.MOUSEBUTTONDOWN:
    #             print(f"Mouse clicked at {event.pos}. My rect is {self.rect}")
    #             if self.rect.collidepoint(event.pos):
    #                 print("Hitbox triggered!")
    #                 self.callback()

# class StationUIGroup(pygame.sprite.Group):
#     def __init__(self):
        super().__init__()

class StationManager:
    def __init__(self, screen):
        self.__screen = screen
        
        # 1. The Navigation UI (Persistent across all stations)
        self.__nav_group = pygame.sprite.Group()
        self.create_nav_buttons()

        # 2. The Stations (The actual content)
        self.stations = {
            "order": Station(self.__screen, "path"),
            "grill": GrillStation(self.__screen, "path"),
        }
        self.current_station = "order"

    def create_nav_buttons(self):
        """Buttons that stay on screen no matter which station you are in."""
        # Switch to Order
        UIButton((10, 550), "20.png", self.__nav_group, 
                 lambda: self.switch_station("order"))
        
        # Switch to Grill
        UIButton((120, 550), "20.png", self.__nav_group, 
                 lambda: self.switch_station("grill"))

    def switch_station(self, target):
        print(f"Navigating to {target}")
        self.current_station = target

    def main(self, events, dt):
        # Update Logic
        # Update the active station's internal logic (patties, customers)
        for key, station in self.stations:
            station.update(dt)
        
        self.stations[self.current_station].handle_events(events)
        # Update the persistent Navigation buttons
        self.__nav_group.handle_events(events)

        # Rendering
        self.render()

    def render(self):
        # Step 1: Draw the Station Content (Background + Items)
        self.stations[self.current_station].draw()
        
        # Step 2: Draw the Navigation UI (On top of everything)
        self.__nav_group.draw(self.__screen)

class Station:
    def __init__(self, screen, bg_image_path):
        self.screen = screen
        self.background = pygame.image.load(bg_image_path).convert()
        # self.ui_group = pygame.sprite.Group()
        self.items = pygame.sprite.Group() # Better as a Group than a List!

    def handle_events(self, events):
        """Only called when this station is visible."""
        # self.ui_group.update(events)
        self.items.update(events) # If items need to be clicked/dragged

    def update(self, dt):
        """Always called so burgers keep cooking in the background."""
        # You can pass dt to your items here
        # Note: We use a custom method name to avoid confusion with Sprite.update
        for item in self.items:
            if hasattr(item, 'process_time'):
                item.process_time(dt)

    def draw(self):
        self.screen.blit(self.background, (0, 0))
        self.items.draw(self.screen)
        # self.ui_group.draw(self.screen)

class GrillStation(Station):
    def __init__(self, screen, bg_image_path):
        super.__init__(screen, bg_image_path)   

class InteractiveIngredient(pygame.sprite.Sprite):
    def __init__(self, name, image_path, x, y):
        # Initialize the parent Sprite class
        super().__init__()
        
        self.name = name
        # Load image and ensure transparency is handled
        self.image = pygame.image.load(image_path).convert_alpha()
        self.rect = self.image.get_rect(topleft=(x, y))
        
        self.dragging = False
        self.is_placed = False

    def on_plate(self):
        """Logic triggered when successfully dropped on a station."""
        self.is_placed = True
        self.dragging = False
        print(f"Success! {self.name} is now on the station.")

    def update(self):
        """If being dragged, follow the mouse cursor."""
        if self.dragging:
            self.rect.center = pygame.mouse.get_pos()

class StationBlock(pygame.sprite.Sprite):
    def __init__(self, name, image_path, x, y):
        super().__init__()
        
        self.name = name
        self.image = pygame.image.load(image_path).convert_alpha()
        self.rect = self.image.get_rect(topleft=(x, y))
        
        # A list to keep track of what's currently on this station
        self.contained_items = []

    def place_item(self, item):
        """Snaps the item to the center of the station and tracks it."""
        # Calculate stacking offset (so items don't perfectly overlap)
        # Each new item sits 5 pixels higher than the last
        stack_offset = len(self.contained_items) * 5
        
        item.rect.centerx = self.rect.centerx
        item.rect.centery = self.rect.centery - stack_offset
        
        # Add to the station's internal list
        self.contained_items.append(item)
        
        # Tell the item it has been placed
        item.on_plate()

class Order:
    pass

class Ingredient:
    pass

class CustomerManager:
    pass

class Customer:
    pass

