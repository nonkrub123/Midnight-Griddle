from core.settings import *

DRAG_THRESHOLD_PX = 6  # pixels moved before a grab becomes a drag

class InputHandler:
    def __init__(self, screen_width, screen_height):
        self.ratio_x = GAME_W / screen_width
        self.ratio_y = GAME_H / screen_height

        self.held_item      = None
        self.held_group     = None
        self.mouse_down_pos = (0, 0)
        self.is_dragging    = False
        self.mouse_pos      = (0, 0)

    def _remap(self, pos):
        return (pos[0] * self.ratio_x, pos[1] * self.ratio_y)

    def _reset(self):
        self.held_item   = None
        self.held_group  = None
        self.is_dragging = False

    def _find_sprite_and_group(self, pos, *groups, for_drop=False):
        for group in reversed(groups):
            sprites_at = [s for s in reversed(group.sprites())
                          if s.rect.collidepoint(pos)
                          and s is not self.held_item]

            if for_drop:
                if sprites_at:
                    return sprites_at[0], group
            else:
                interactable = [s for s in sprites_at
                                if not s.is_locked
                                and (s.has_tag("draggable") or s.has_tag("clickable"))]
                if interactable:
                    return interactable[0], group

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
        self.mouse_down_pos = pos
        self.mouse_pos      = pos
        self.is_dragging    = False

        sprite, group = self._find_sprite_and_group(pos, *groups)
        if sprite is None:
            return

        # Tentatively hold any sprite — decide click vs drag on mouse up
        self.held_item  = sprite
        self.held_group = group

    def _on_mouse_motion(self, pos):
        self.mouse_pos = pos

        if self.held_item and not self.is_dragging:
            dx = pos[0] - self.mouse_down_pos[0]
            dy = pos[1] - self.mouse_down_pos[1]
            if (dx * dx + dy * dy) >= DRAG_THRESHOLD_PX * DRAG_THRESHOLD_PX:
                if self.held_item.has_tag("draggable"):
                    self.is_dragging = True
                    self.held_group.handle_drag(self.held_item, pos)
                else:
                    # Not draggable — drop the hold so it doesn't follow the mouse
                    self._reset()

    def _on_mouse_up(self, pos, *groups):
        if not self.held_item:
            return

        if self.is_dragging:
            target, target_group = self._find_sprite_and_group(pos, *groups, for_drop=True)
            dropped = False
            if target and target is not self.held_item:
                dropped = target_group.handle_drop(self.held_item, target)
            if not dropped:
                home = self.held_item.current_group or self.held_group
                home.handle_snapback(self.held_item)
        else:
            # Never moved enough to be a drag — treat as click
            if self.held_group and self.held_item:
                self.held_group.handle_click(self.held_item)

        self._reset()