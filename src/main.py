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
        return (pos[0] * self.ratio_x, pos[1] * self.ratio_y)

    def _reset(self):
        self.held_item   = None
        self.held_group  = None
        self.is_dragging = False

    def _find_sprite_and_group(self, pos, *groups):
        """
        Walk groups back-to-front (last group = highest draw priority).
        Within each group check sprites in reverse layer order (topmost first).
        Skip the currently held item and any locked sprites.
        """
        for group in reversed(groups):
            # LayeredUpdates.get_sprites_at is ideal but checking manually is safer
            sprites_at = [s for s in reversed(group.sprites())
                          if s.rect.collidepoint(pos)
                          and s is not self.held_item
                          and not s.is_locked]
            if sprites_at:
                return sprites_at[0], group
        return None, None

    def handle_events(self, events, *groups):
        for event in events:
            if event.type not in (pygame.MOUSEBUTTONDOWN,
                                  pygame.MOUSEBUTTONUP,
                                  pygame.MOUSEMOTION):
                continue
            pos = self._remap(event.pos)
            if event.type == pygame.MOUSEBUTTONDOWN:
                self._on_mouse_down(pos, *groups)
            elif event.type == pygame.MOUSEMOTION:
                self._on_mouse_motion(pos)
            elif event.type == pygame.MOUSEBUTTONUP:
                self._on_mouse_up(pos, *groups)

    def handle_dragging(self):
        """Called every frame. Just moves the held item to mouse pos."""

        if self.is_dragging and self.held_item:
            self.held_item.rect.center = (int(self.mouse_pos[0]), int(self.mouse_pos[1]))

    # ── Mouse down ────────────────────────────────────────────────────────────

    def _on_mouse_down(self, pos, *groups):
        self.mouse_down_time = time.time()
        self.mouse_down_pos  = pos
        self.mouse_pos       = pos
 
        sprite, group = self._find_sprite_and_group(pos, *groups)
        if sprite is None:
            return
 
        if sprite.has_tag("draggable"):
            # Just remember — don't remove from group yet.
            # handle_drag fires in _on_mouse_motion once drag threshold is crossed.
            self.held_item  = sprite
            self.held_group = group
        else:
            group.handle_click(sprite)

    # ── Mouse motion ──────────────────────────────────────────────────────────

    def _on_mouse_motion(self, pos):
        self.mouse_pos = pos
        if self.held_item and not self.is_dragging:
            if time.time() - self.mouse_down_time >= CLICK_THRESHOLD:
                self.is_dragging = True
                self.held_group.handle_drag(self.held_item, pos)  # ← lift the sprite

    # ── Mouse up ──────────────────────────────────────────────────────────────
    def _on_mouse_up(self, pos, *groups):
        if not self.held_item:
            return
        # if not self.held_item or not self.held_group:
        #     return

        held_duration = time.time() - self.mouse_down_time
        dx = pos[0] - self.mouse_down_pos[0]
        dy = pos[1] - self.mouse_down_pos[1]
        moved = (dx * dx + dy * dy) > 4

        # 1. Handle Clicks (Short duration or no movement)
        if held_duration < CLICK_THRESHOLD or not moved:
            if self.is_dragging:
                home = self.held_item.current_group or self.held_group
                home.handle_snapback(self.held_item)
            
            # Fire the click event
            self.held_group.handle_click(self.held_item)

        # 2. Handle Drops (Actual dragging)
        else:
            target, target_group = self._find_sprite_and_group(pos, *groups)
            dropped = False
            
            if target and target is not self.held_item:
                dropped = target_group.handle_drop(self.held_item, target)
            
            if not dropped:
                home = self.held_item.current_group or self.held_group
                home.handle_snapback(self.held_item)

        # 3. ALWAYS RESET
        # This must happen outside the if/else to ensure the state is cleared
        self._reset()


# ── Game Manager ──────────────────────────────────────────────────────────────

class GameManager:
    def __init__(self):
        pygame.init()

        info = pygame.display.Info()
        self.screen_width  = info.current_w
        self.screen_height = info.current_h

        self.screen = pygame.display.set_mode(
            (self.screen_width, self.screen_height),
            pygame.FULLSCREEN
        )
        self.game_wrapper = pygame.Surface((GAME_W, GAME_H))
        self.clock        = pygame.time.Clock()
        self.fps          = FPS
        self.running      = True
        self.state        = "playing"

        self.input_handler   = InputHandler(self.screen_width, self.screen_height)
        self.station_manager = StationManager(self.game_wrapper, self._on_station_switch)

    def _on_station_switch(self, new_groups):
        pass  # GameManager asks station_manager for groups fresh each frame

    # ── Frame ─────────────────────────────────────────────────────────────────

    def handle_events(self):
        self.events = pygame.event.get()
        for event in self.events:
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                self.running = False
        groups = self.station_manager.get_all_groups()
        self.input_handler.handle_events(self.events, *groups)

    def update(self):
        self.input_handler.handle_dragging()
        self.station_manager.update(self.dt)

    def render(self):
        self.game_wrapper.fill((30, 30, 30))

        # Station draws background + all groups + nav
        self.station_manager.draw()

        # Held item always on top
        held = self.input_handler.held_item
        if held and self.input_handler.is_dragging:
            self.game_wrapper.blit(held.image, held.rect)

        scaled = pygame.transform.scale(
            self.game_wrapper, (self.screen_width, self.screen_height)
        )
        self.screen.blit(scaled, (0, 0))
        pygame.display.flip()

    # ── State machine ─────────────────────────────────────────────────────────

    def playing(self):
        self.dt = self.clock.tick(self.fps) / 1000
        self.handle_events()
        self.update()
        self.render()

    def main(self):
        while self.running:
            if   self.state == "playing":  self.playing()
            elif self.state == "menu":     pass
            elif self.state == "setting":  pass
            elif self.state == "gameover": pass
        pygame.quit()


if __name__ == "__main__":
    game = GameManager()
    game.main()