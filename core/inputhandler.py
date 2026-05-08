from core.settings import *
from ui.group import UIGroup
from ui.group_orderui import OrderUI
from core.menuscreen import MenuScreen

DRAG_THRESHOLD_PX = 6  # pixels moved before a grab becomes a drag

class InputHandler:
    def __init__(self, screen_width, screen_height):
        self.ratio_x = GAME_W / screen_width
        self.ratio_y = GAME_H / screen_height

        self.__held_item    = None
        self.__held_group   = None
        self.mouse_down_pos = (0, 0)
        self.is_dragging    = False
        self.mouse_pos      = (0, 0)
        self.__last_hovered = None
        
    def _remap(self, pos):
        return (pos[0] * self.ratio_x, pos[1] * self.ratio_y)

    def __reset(self):
        self.__held_item  = None
        self.__held_group = None
        self.is_dragging  = False

    @property
    def held_item(self):
        return self.__held_item

    def __find_sprite_and_group(self, pos, *groups, for_drop=False):
        for group in reversed(groups):
            sprites_at = [s for s in reversed(group.sprites())
                          if s.rect.collidepoint(pos)
                          and s is not self.__held_item]

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

    # ── Hover detection ──────────────────────────────────────────────────

    def __update_hover(self, pos, *groups):
        found = None
        for group in reversed(groups):
            if not isinstance(group, (OrderUI, UIGroup, MenuScreen)):
                continue
            for sprite in reversed(group.sprites()):
                if sprite.has_tag("hoverable") and sprite.rect.collidepoint(pos):
                    found = sprite
                    break
            if found:
                break

        if found is self.__last_hovered:
            return  # nothing changed, skip entirely

        if self.__last_hovered:
            self.__last_hovered.set_hovered(False)  # unhover old
        if found:
            found.set_hovered(True)                 # hover new

        self.__last_hovered = found

    # ── Event entry point ────────────────────────────────────────────────

    def handle_events(self, events, *groups):
        for event in events:
            if event.type not in (pygame.MOUSEBUTTONDOWN,
                                  pygame.MOUSEBUTTONUP,
                                  pygame.MOUSEMOTION):
                continue
            pos = self._remap(event.pos)
            if   event.type == pygame.MOUSEBUTTONDOWN: self.__on_mouse_down(pos, *groups)
            elif event.type == pygame.MOUSEMOTION:     self.__on_mouse_motion(pos, *groups)
            elif event.type == pygame.MOUSEBUTTONUP:   self.__on_mouse_up(pos, *groups)

    def handle_dragging(self):
        if self.is_dragging and self.__held_item:
            self.__held_item.rect.center = (int(self.mouse_pos[0]), int(self.mouse_pos[1]))

    def __on_mouse_down(self, pos, *groups):
        self.mouse_down_pos = pos
        self.mouse_pos      = pos
        self.is_dragging    = False

        sprite, group = self.__find_sprite_and_group(pos, *groups)
        if sprite is None:
            return

        # Tentatively hold — decide click vs drag on mouse up
        self.__held_item  = sprite
        self.__held_group = group

    def __on_mouse_motion(self, pos, *groups):
        self.mouse_pos = pos
        self.__update_hover(pos, *groups)  # only runs on actual mouse movement

        if self.__held_item and not self.is_dragging:
            dx = pos[0] - self.mouse_down_pos[0]
            dy = pos[1] - self.mouse_down_pos[1]
            if (dx * dx + dy * dy) >= DRAG_THRESHOLD_PX * DRAG_THRESHOLD_PX:
                if self.__held_item.has_tag("draggable"):
                    self.is_dragging = True
                    self.__held_group.handle_drag(self.__held_item, pos)
                else:
                    self.__reset()

    def __on_mouse_up(self, pos, *groups):
        if not self.__held_item:
            return

        if self.is_dragging:
            target, target_group = self.__find_sprite_and_group(pos, *groups, for_drop=True)
            dropped = False
            if target and target is not self.__held_item:
                dropped = target_group.handle_drop(self.__held_item, target)
            if not dropped:
                home = self.__held_item.current_group or self.__held_group
                home.handle_snapback(self.__held_item)
        else:
            # Never moved enough — treat as click
            if self.__held_group and self.__held_item:
                self.__held_group.handle_click(self.__held_item)

        self.__reset()