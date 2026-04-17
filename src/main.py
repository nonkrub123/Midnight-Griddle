from settings import *
from station import *
from interactive import *
import time
import pygame


class InputHandler:
    def __init__(self, screen_width, screen_height):
        self.ratio_x = GAME_W / screen_width
        self.ratio_y = GAME_H / screen_height

        self.held_item       = None
        self.held_group      = None
        self.mouse_down_time = 0
        self.mouse_down_pos  = (0, 0)
        self.is_dragging     = False
        self.mouse_pos       = (0, 0)

    def _remap(self, pos):
        """Remap screen position (x,y) to match game position"""
        return (pos[0] * self.ratio_x, pos[1] * self.ratio_y)

    def _reset(self):
        """"""
        self.held_item   = None
        self.held_group  = None
        self.is_dragging = False

    def _find_sprite_and_group(self, pos, *groups):
        for group in groups:
            for sprite in reversed(group.sprites()):
                if sprite is self.held_item:
                    continue
                if sprite.rect.collidepoint(pos):
                    if sprite.has_tag("locked"):
                        continue
                    return sprite, group
        return None, None
    
    def handle_events(self, events, *groups):
        for event in events:
            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEBUTTONUP, pygame.MOUSEMOTION):
                pos = self._remap(event.pos)  # remap once, right here

                if event.type == pygame.MOUSEBUTTONDOWN:
                    self._on_mouse_down(pos, *groups)
                elif event.type == pygame.MOUSEMOTION:
                    self._on_mouse_motion(pos)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self._on_mouse_up(pos, *groups)
                

    def handle_dragging(self):
        if self.is_dragging and self.held_item and self.held_group:
            self.held_group.handle_drag(self.held_item, self.mouse_pos)


    def _on_mouse_down(self, pos, *groups):
        self.mouse_down_time = time.time()
        self.mouse_down_pos  = pos
        self.mouse_pos       = pos

        sprite, group = self._find_sprite_and_group(pos, *groups)
        if sprite is None:
            return

        if sprite.has_tag("draggable"):
            self.held_item  = sprite
            self.held_group = group
            self._original_layer = sprite._layer
            for g in sprite.groups():
                if isinstance(g, pygame.sprite.LayeredUpdates):
                    g.change_layer(sprite, LAYER_DRAGGING)
        else:
            group.handle_click(sprite)

    def _on_mouse_motion(self, pos):
        self.mouse_pos = pos

        if not self.held_item or self.is_dragging:
            return

        if time.time() - self.mouse_down_time >= CLICK_THRESHOLD:
            self.is_dragging = True

    def _on_mouse_up(self, pos, *groups):
        if not self.held_item or not self.held_group:
            return

        # Restore layer first, before drop/snapback repositions the sprite
        for g in self.held_item.groups():
            if isinstance(g, pygame.sprite.LayeredUpdates):
                g.change_layer(self.held_item, self._original_layer)

        held_duration = time.time() - self.mouse_down_time
        dx = pos[0] - self.mouse_down_pos[0]
        dy = pos[1] - self.mouse_down_pos[1]
        moved = (dx*dx + dy*dy) > 4

        if held_duration < CLICK_THRESHOLD or not moved:
            self.held_group.handle_click(self.held_item)
        else:
            target, target_group = self._find_sprite_and_group(pos, *groups)
            if target and target is not self.held_item:
                if target_group.handle_drop(self.held_item, target):
                    self.held_group.handle_remove(self.held_item)
                else:
                    self.held_group.handle_snapback(self.held_item)

        self._reset()
    
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
        self.game_wrapper = pygame.surface.Surface((GAME_W, GAME_H))

        self.clock = pygame.time.Clock()
        self.fps = FPS
        self.running = True
        self.state = "playing" # Menu(load game/ new game), Play, horror, gameover, setting
        
        # InputHanlder & Station
        self.input_handler = InputHandler(self.screen_width, self.screen_height)

        self.station_manager = StationManager(
            self.game_wrapper,
            self.on_station_switch   # ← callback
        )

        # Drawing group
        self.all_sprites = self.station_manager.get_all_sprites()
        self.all_groups = self.station_manager.get_all_groups()
        
    def on_station_switch(self, new_sprites, new_groups):
        """Called by StationManager when station changes."""
        self.all_sprites = new_sprites
        self.all_groups = new_groups

    def handle_events(self):
        self.events = pygame.event.get()
        
        # self.input_handler.handle_events(self.events, *self.all_groups)
        # In GameManager, pass groups front-to-back (UI last passed = checked first if you reverse)
        self.input_handler.handle_events(self.events, *reversed(self.all_groups))

    def update(self):
        self.input_handler.handle_dragging()
        pass
        
    def render(self):
        """Renders everything to the screen."""
        # 0. Clear the virtual canvas, NOT the physical screen
        self.game_wrapper.fill((30, 30, 30)) 

        # 1. Draw to the WRAPPER (the 640x360 surface)
        self.all_sprites.draw(self.game_wrapper)
        # self.ingredients_group.draw(self.game_wrapper)
        
        # if self.selected_item:
        #     self.game_wrapper.blit(self.selected_item.image, self.selected_item.rect)

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