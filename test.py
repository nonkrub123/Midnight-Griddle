# from settings import *

# class UIButton(pygame.sprite.Sprite):
#     def __init__(self, pos, image_name, ui_group, callback):
#         # 1. Initialize the parent Sprite and add to group automatically
#         super().__init__(ui_group) 
        
#         # 2. Load the 'Cozy' asset
#         self.image = pygame.image.load(get_path('assets', 'ui', image_name)).convert_alpha()
#         self.rect = self.image.get_rect(topleft=pos)
        
#         # 3. Store the action to perform on click
#         self.callback = callback

#     def handle_events(self, event_list):
#         for event in event_list:
#             if event.type == pygame.MOUSEBUTTONDOWN:
#                 # print(f"BUTTON CLICKED! Callback is: {self.callback}")
#                 if self.rect.collidepoint(event.pos):
#                     if callable(self.callback):
#                         self.callback()
#                     else:
#                         print("ERROR: Callback is not a function!")
#     # def update(self, event_list):
#     #     for event in event_list:
#     #         if event.type == pygame.MOUSEBUTTONDOWN:
#     #             print(f"Mouse clicked at {event.pos}. My rect is {self.rect}")
#     #             if self.rect.collidepoint(event.pos):
#     #                 print("Hitbox triggered!")
#     #                 self.callback()

# # class StationUIGroup(pygame.sprite.Group):
# #     def __init__(self):
#         super().__init__()

# class GameState:
#     def __init__(self):
#         # The 'Held Item' logic moves here
#         self.held_item = None
#         self.inventory = []
#         self.money = 0
#         self.active_order = None
#         self.is_paused = False

#     def can_pick_up(self):
#         return self.held_item is None and len(self.inventory) < 5
    
# class InputHandler:
#     def __init__(self, state):
#         self.state = state # Reference to our Data Vault

#     def handle_input(self, events, active_station):
#         for event in events:
#             if event.type == pygame.MOUSEBUTTONDOWN:
#                 self._handle_click(event.pos, active_station)
            
#             if event.type == pygame.MOUSEBUTTONUP:
#                 self._handle_release(event.pos, active_station)

#     def _handle_click(self, pos, station):
#         # 1. Check UI/Nav buttons first
#         # 2. If no UI clicked, check Station Items
#         if self.state.can_pick_up():
#             for item in station.items:
#                 if item.rect.collidepoint(pos):
#                     self.state.held_item = item
#                     item.dragging = True
#                     break

#     def _handle_release(self, pos, station):
#         if self.state.held_item:
#             # Logic for dropping on a StationBlock
#             # We look for blocks in the current station
#             for block in getattr(station, 'blocks', []):
#                 if block.rect.collidepoint(pos):
#                     block.place_item(self.state.held_item)
#                     self.state.held_item = None
#                     return
            
#             # If not dropped on a block, release it
#             self.state.held_item.dragging = False
#             self.state.held_item = None

# class StationManager:
#     def __init__(self, screen):
#         self.__screen = screen
        
#         # Core Components
#         self.state = GameState()
#         self.input_handler = InputHandler(self.state)
        
#         # Navigation
#         self.__nav_group = pygame.sprite.Group()
#         self.create_nav_buttons()

#         # Stations - Pass the state so they can read data
#         self.stations = {
#             "order": Station(self.__screen, "order_bg.png", self.state),
#             "grill": GrillStation(self.__screen, "grill_bg.png", self.state),
#         }
#         self.current_station = "order"

#     def create_nav_buttons(self):
#         """Buttons that stay on screen no matter which station you are in."""
#         # Switch to Order
#         UIButton((10, 550), "btn_order.png", self.__nav_group, 
#                  lambda: self.switch_station("order"))
        
#         # Switch to Grill
#         UIButton((120, 550), "btn_grill.png", self.__nav_group, 
#                  lambda: self.switch_station("grill"))

#     def switch_station(self, target):
#         print(f"Navigating to {target}")
#         self.current_station = target

#     def main(self, events, dt):
#             # 1. Logic Update (Always run for background cooking)
#             for station in self.stations.values():
#                 station.update(dt)

#             # 2. Input Handling (The InputHandler does the heavy lifting)
#             # It checks navigation buttons AND the active station
#             self.input_handler.handle_input(events, self.stations[self.current_station])
#             self.__nav_group.update(events) # Buttons handle their own callbacks

#             # 3. Rendering
#             self.render()

#     def render(self):
#         # Step 1: Draw the Station Content (Background + Items)
#         self.stations[self.current_station].draw()
        
#         # Step 2: Draw the Navigation UI (On top of everything)
#         self.__nav_group.draw(self.__screen)

# class Station:
#     def __init__(self, screen, bg_image_path):
#         self.screen = screen
#         self.background = pygame.image.load(bg_image_path).convert()
#         # self.ui_group = pygame.sprite.Group()
#         self.items = pygame.sprite.Group() # Better as a Group than a List!

#     def handle_events(self, events):
#         """Only called when this station is visible."""
#         # self.ui_group.update(events)
#         self.items.update(events) # If items need to be clicked/dragged

#     def update(self, dt):
#         """Always called so burgers keep cooking in the background."""
#         # You can pass dt to your items here
#         # Note: We use a custom method name to avoid confusion with Sprite.update
#         for item in self.items:
#             if hasattr(item, 'process_time'):
#                 item.process_time(dt)

#     def draw(self):
#         self.screen.blit(self.background, (0, 0))
#         self.items.draw(self.screen)
#         # self.ui_group.draw(self.screen)

# class GrillStation(Station):
#     def __init__(self, screen, bg_image_path):
#         super.__init__(screen, bg_image_path)   

# class InteractiveIngredient(pygame.sprite.Sprite):
#     def __init__(self, name, image_path, x, y):
#         # Initialize the parent Sprite class
#         super().__init__()
        
#         self.name = name
#         # Load image and ensure transparency is handled
#         self.image = pygame.image.load(image_path).convert_alpha()
#         self.rect = self.image.get_rect(topleft=(x, y))
        
#         self.dragging = False
#         self.is_placed = False

#     def on_plate(self):
#         """Logic triggered when successfully dropped on a station."""
#         self.is_placed = True
#         self.dragging = False
#         print(f"Success! {self.name} is now on the station.")

#     def update(self):
#         """If being dragged, follow the mouse cursor."""
#         if self.dragging:
#             self.rect.center = pygame.mouse.get_pos()

# class StationBlock(pygame.sprite.Sprite):
#     def __init__(self, name, image_path, x, y):
#         super().__init__()
        
#         self.name = name
#         self.image = pygame.image.load(image_path).convert_alpha()
#         self.rect = self.image.get_rect(topleft=(x, y))
        
#         # A list to keep track of what's currently on this station
#         self.contained_items = []

#     def place_item(self, item):
#         """Snaps the item to the center of the station and tracks it."""
#         # Calculate stacking offset (so items don't perfectly overlap)
#         # Each new item sits 5 pixels higher than the last
#         stack_offset = len(self.contained_items) * 5
        
#         item.rect.centerx = self.rect.centerx
#         item.rect.centery = self.rect.centery - stack_offset
        
#         # Add to the station's internal list
#         self.contained_items.append(item)
        
#         # Tell the item it has been placed
#         item.on_plate()

# class Order:
#     pass

# class Ingredient:
#     pass

# class CustomerManager:
#     pass

# class Customer:
#     pass

# def b1():

#     def a1():
#         print("a1")
    
#     def a2():
#         print("a2")
    
#     b2 = a1
#     return b2, a2

# def x(y):
#     print(y)
#     return y
# tmp = x(b1())

def outer(func):
    def newfunc():
        print("Outer")
        func()
        print("Outer")
    return newfunc

@outer
def internal():
    print("content")

internal()