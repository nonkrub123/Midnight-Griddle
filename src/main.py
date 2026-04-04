from settings import *
from station import *

class InputHandler:
    def __init__(self):
        self.gamedata = GameData()

    def handle_events(self, events, active_station):
        for event in events:
            # 1. Grabbing
            if event.type == pygame.MOUSEBUTTONDOWN:
                # Check station ingredients
                for sprite in active_station.items:
                    if sprite.rect.collidepoint(event.pos):
                        self.gamedata.grab(sprite)
                        break

            # 2. Dropping
            if event.type == pygame.MOUSEBUTTONUP:
                held = self.gamedata.get_held_item()
                if held:
                    # Check if dropped on a station block
                    # We look at the blocks INSIDE the active station
                    hit_block = pygame.sprite.spritecollideany(held, active_station.blocks)
                    if hit_block:
                        hit_block.place_item(self.gamedata.release_item())
                    else:
                        self.gamedata.release_item() # Drop it in mid-air

class GameManager:
    def __init__(self):
        pygame.init()

        info = pygame.display.Info()
        self.screen_width = info.current_w
        self.screen_height = info.current_h

        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height), 
            pygame.FULLSCREEN
        )
        self.game_wrapper = pygame.surface.Surface((640, 360))

        self.clock = pygame.time.Clock()
        self.fps = FPS
        self.running = True
        self.state = "playing" # Menu(load game/ new game), Play, horror, gameover, setting
        
        # InputHanlder & Station
        self.input_handler = InputHandler()
        self.station_manager = StationManager(self.game_wrapper)

        # Drawing group
        self.all_sprites = pygame.sprite.Group()

        # 2. The "Snap Points" (Grills, Plates, Trash cans)
        self.stations_group = pygame.sprite.Group()

        # 3. The "Moving Parts" (Patties, Buns, Cheese)
        self.ingredients_group = pygame.sprite.Group()

        # Tracking the item currently being dragged
        self.selected_item = None

    def handle_events(self):
        # 1. Get the raw OS events
        self.events = pygame.event.get()
        
        # 2. Calculate the "Shrink Ratio" 
        # (How much smaller is the game than the window?)
        ratio_x = 640 / self.screen_width
        ratio_y = 360 / self.screen_height

        for event in self.events:
            if event.type == pygame.QUIT:
                self.running = False
            
            # 3. The Magic Fix: Remap the mouse position
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                # Translate the 1000x1000 click back to 640x360 logic
                new_x = event.pos[0] * ratio_x
                new_y = event.pos[1] * ratio_y
                
                # Overwrite the event position so the UI sees the "Game World" coords
                event.pos = (new_x, new_y)

                # Pick up logic
                if event.type == pygame.MOUSEBUTTONDOWN:
                    for sprite in self.ingredients_group:
                        if sprite.rect.collidepoint(event.pos):
                            self.selected_item = sprite
                            sprite.dragging = True
                            break

                # Drop logic
                if event.type == pygame.MOUSEBUTTONUP:
                    if self.selected_item:
                        # Check if dropped on a station
                        hit_station = pygame.sprite.spritecollideany(self.selected_item, self.stations_group)
                        if hit_station:
                            hit_station.place_item(self.selected_item)
                        
                        self.selected_item.dragging = False
                        self.selected_item = None

    def update(self):
        # Pass the already-remapped events to the manager
        self.station_manager.main(self.events, self.dt)
        
        # Update all ingredients (this handles the "following the mouse" logic)
        # We pass the remapped mouse_pos specifically
        if self.selected_item:
            self.selected_item.update(self.mouse_pos, self.dt)
        
    def render(self):
        """Renders everything to the screen."""
        # 0. Clear the virtual canvas, NOT the physical screen
        self.game_wrapper.fill((30, 30, 30)) 

        # 1. Draw to the WRAPPER (the 640x360 surface)
        self.stations_group.draw(self.game_wrapper)
        self.ingredients_group.draw(self.game_wrapper)
        
        if self.selected_item:
            self.game_wrapper.blit(self.selected_item.image, self.selected_item.rect)

        # 4.This is change station ui
        self.station_manager.render_ui()

        # 5. Scale that small surface up to the big window size
        self.scaled_game = pygame.transform.scale(
            self.game_wrapper, 
            (self.screen_width, self.screen_height)
        )
        
        # 3. Blit the big image to the actual monitor
        self.screen.blit(self.scaled_game, (0, 0))
        pygame.display.flip()
    
    def playing(self):
            """The main Game Loop."""
                # Limits FPS and provides 'dt' (delta time) if needed for smooth movemen
            self.dt = self.clock.tick(self.fps) / 1000

            # Update Game Data
            self.handle_events()
            self.update()
            self.render()   

    def menu(self):
        pass
    
    def setting(self):
        pass

    def gameover(self):
        pass
    
    def main(self):
        while self.running:
            if self.state == "playing":
                self.playing()
            elif self.state == "menu":
                self.menu()
            elif self.state == "setting":
                self.setting()
            elif self.state == "gameover":
                self.gameover()

if __name__ == "__main__":
    game = GameManager()
    game.main()