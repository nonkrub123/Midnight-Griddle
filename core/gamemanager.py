from core.settings import *
from stations.station import *
from ui.interactive import *
import time
import pygame
from stations.stationmanager import *
from core.stat_viewer import show_stat
from core.inputhandler import InputHandler
from ui.group import BaseGroup
import ui.theme as theme
from core.menuscreen import MenuScreen

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

        self.gamedata        = GameData()
        self.input_handler   = InputHandler(self.screen_width, self.screen_height)
        self.station_manager = StationManager(
            self.game_wrapper, self._on_station_switch, self.gamedata
        )

        self.__state = "menu"        # start on title screen
        self.menu    = None
        self._pause_rect = None      # hitbox for the in-game pause button
        self._build_menu()

    def _on_station_switch(self, new_groups):
        pass

    # ── Menu building ────────────────────────────────────────────────────

    def _build_menu(self):
        self.menu = MenuScreen("BURGER SHIFT", [
            ("START SHIFT", self._start_game),
            ("VIEW STATS",  show_stat),
            ("QUIT",        self._quit),
        ])

    def _build_pause(self):
        self.menu = MenuScreen("PAUSED", [
            ("RESUME",      self._resume),
            ("VIEW STATS",  show_stat),
            ("RETURN HOME", self._return_home),
        ])

    def _build_gameover(self):
        self.menu = MenuScreen("SHIFT FAILED", [
            ("VIEW STATS",  show_stat),
            ("RETURN HOME", self._return_home),
        ])

    def _build_complete(self):
        self.menu = MenuScreen("SHIFT COMPLETE", [
            ("VIEW STATS",  show_stat),
            ("RETURN HOME", self._return_home),
        ])

    # ── State transitions ────────────────────────────────────────────────

    def _start_game(self):
        # Fresh shift: rebuild station manager so hour/customers reset
        self.station_manager = StationManager(
            self.game_wrapper, self._on_station_switch, self.gamedata
        )
        self.__state = "playing"
        self.menu    = None

    def _pause(self):
        self._build_pause()
        self.__state = "paused"

    def _resume(self):
        self.__state = "playing"
        self.menu    = None

    def _return_home(self):
        self._build_menu()
        self.__state = "menu"

    def _quit(self):
        self.running = False

    # ── Playing loop ─────────────────────────────────────────────────────

    def handle_events(self):
        self.events = pygame.event.get()
        for event in self.events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
                self._pause()
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = self.input_handler._remap(event.pos)
                if self._pause_rect and self._pause_rect.collidepoint(pos):
                    self._pause()
                    return

        groups = self.station_manager.get_all_groups()
        self.input_handler.handle_events(self.events, *groups)

    def update(self):
        self.input_handler.handle_dragging()
        self.station_manager.update(self.dt)

    def render(self):
        self.game_wrapper.fill((30, 30, 30))
        self.station_manager.draw()

        held = self.input_handler.held_item
        if held and self.input_handler.is_dragging:
            self.game_wrapper.blit(held.image, held.rect)

        self._draw_pause_button()

        scaled = pygame.transform.scale(
            self.game_wrapper, (self.screen_width, self.screen_height)
        )
        self.screen.blit(scaled, (0, 0))
        pygame.display.flip()

    def _draw_pause_button(self):
        """Pause glyph at the top-center of the game surface."""
        cx, cy = GAME_W // 2, 60
        w, h   = 60, 44
        rect   = pygame.Rect(cx - w//2, cy - h//2, w, h)

        pygame.draw.rect(self.game_wrapper, theme.C_BG,     rect, border_radius=8)
        pygame.draw.rect(self.game_wrapper, theme.C_BORDER, rect, 2, border_radius=8)
        # Two vertical bars = pause icon
        pygame.draw.rect(self.game_wrapper, theme.C_TEXT, (cx - 10, cy - 10, 6, 20))
        pygame.draw.rect(self.game_wrapper, theme.C_TEXT, (cx +  4, cy - 10, 6, 20))

        self._pause_rect = rect   # for event hitbox

    def playing(self):
        self.dt = self.clock.tick(self.fps) / 1000
        self.handle_events()
        if self.__state != "playing":
            return   # handler transitioned us (e.g. pause) — don't keep ticking this frame

        self.update()

        # End-of-shift checks
        if self.station_manager.game_hour.is_over:
            self._build_complete()
            self.__state = "complete"
            return

        if len(self.gamedata._ratings) >= 3 and self.gamedata.average_rating < 2:
            self._build_gameover()
            self.__state = "gameover"
            self.gamedata.restart_data()
            return

        self.render()

    # ── Menu / paused / gameover / complete loop ─────────────────────────

    def handle_menu(self):
        self.dt = self.clock.tick(self.fps) / 1000

        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.__state == "paused":
                    self._resume()
                    return

        self.input_handler.handle_events(events, self.menu)

        # A button callback may have transitioned us to "playing" → self.menu is now None.
        # Bail out; the next frame will route to playing() naturally.
        if self.menu is None:
            return

        if self.__state != "paused":
            self.game_wrapper.fill((30, 30, 30))

        self.menu.draw(self.game_wrapper)

        scaled = pygame.transform.scale(
            self.game_wrapper, (self.screen_width, self.screen_height)
        )
        self.screen.blit(scaled, (0, 0))
        pygame.display.flip()

    # ── Main loop ────────────────────────────────────────────────────────

    def main(self):
        while self.running:
            if   self.__state == "playing": self.playing()
            elif self.__state in ("menu", "paused", "gameover", "complete"):
                self.handle_menu()
        pygame.quit()