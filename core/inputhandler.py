from core.settings import *
import time

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
        for group in reversed(groups):
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
            if   event.type == pygame.MOUSEBUTTONDOWN: self._on_mouse_down(pos, *groups)
            elif event.type == pygame.MOUSEMOTION:     self._on_mouse_motion(pos)
            elif event.type == pygame.MOUSEBUTTONUP:   self._on_mouse_up(pos, *groups)

    def handle_dragging(self):
        if self.is_dragging and self.held_item:
            self.held_item.rect.center = (int(self.mouse_pos[0]), int(self.mouse_pos[1]))

    def _on_mouse_down(self, pos, *groups):
        self.mouse_down_time = time.time()
        self.mouse_down_pos  = pos
        self.mouse_pos       = pos
        # print(pos)
        sprite, group = self._find_sprite_and_group(pos, *groups)
        if sprite is None:
            return
        if sprite.has_tag("draggable"):
            self.held_item  = sprite
            self.held_group = group
        else:
            group.handle_click(sprite)

    def _on_mouse_motion(self, pos):
        self.mouse_pos = pos
        if self.held_item and not self.is_dragging:
            if time.time() - self.mouse_down_time >= CLICK_THRESHOLD:
                self.is_dragging = True
                self.held_group.handle_drag(self.held_item, pos)

    def _on_mouse_up(self, pos, *groups):
        # print(f"This is pos {pos}")
        if not self.held_item:
            return
        # if not self.held_item or not self.held_group:
        #     return
        
        held_duration = time.time() - self.mouse_down_time
        dx = pos[0] - self.mouse_down_pos[0]
        dy = pos[1] - self.mouse_down_pos[1]
        moved = (dx * dx + dy * dy) > 4

        if held_duration < CLICK_THRESHOLD or not moved:
            if self.is_dragging:
                home = self.held_item.current_group or self.held_group
                home.handle_snapback(self.held_item)
            self.held_group.handle_click(self.held_item)
        else:
            target, target_group = self._find_sprite_and_group(pos, *groups)
            dropped = False
            if target and target is not self.held_item:
                dropped = target_group.handle_drop(self.held_item, target)
            if not dropped:
                home = self.held_item.current_group or self.held_group
                home.handle_snapback(self.held_item)

        self._reset()