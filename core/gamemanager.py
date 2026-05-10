from core.settings import *
from stations.station import *
from ui.interactive import *
import pygame
from stations.stationmanager import *
from core.stat_viewer import StatViewer
from core.inputhandler import InputHandler
from ui.group import BaseGroup
import ui.theme as theme
from core.menuscreen import MenuScreen
from core.audiomanager import AudioManager

class GameManager:
    """
    Top-level orchestrator. Public API: __init__() and main().
    Everything else is internal machinery.
    """

    def __init__(self):
        pygame.init()

        info = pygame.display.Info()
        self.__screen_width  = info.current_w
        self.__screen_height = info.current_h

        self.__screen = pygame.display.set_mode(
            (self.__screen_width, self.__screen_height),
            pygame.FULLSCREEN
        )
        self.__game_wrapper = pygame.Surface((GAME_W, GAME_H))
        self.__clock        = pygame.time.Clock()
        self.__fps          = FPS
        self.__running      = True

        self.__gamedata        = GameData()
        self.__input_handler   = InputHandler(self.__screen_width, self.__screen_height)
        self.__station_manager = StationManager(
            self.__game_wrapper, self.__on_station_switch, self.__gamedata
        )
        self.__stat_viewer = StatViewer
        self.__audio_manager = AudioManager()

        self.__state      = "menu"
        self.__menu       = None
        self.__pause_rect = None
        self.__dt         = 0.0

        self.__build_menu()

    def __show_stat(self):
        self.__stat_viewer.run()
    # ── Internal callback (kept as a no-op hook for future use) ──────────

    def __on_station_switch(self):
        pass

    # ── Menu building ────────────────────────────────────────────────────

    def __build_menu(self):
        self.__menu = MenuScreen("Midnight Griddle", [
            ("CONTINUE SHIFT", self.__continue_game),
            ("NEW SHIFT",      self.__new_game),
            ("VIEW STATS",     self.__show_stat),
            ("QUIT",           self.__quit),
        ])

    def __build_pause(self):
        self.__menu = MenuScreen("PAUSED", [
            ("RESUME",      self.__resume),
            ("VIEW STATS",  self.__show_stat),
            ("RETURN HOME", self.__return_home),
        ])

    def __build_gameover(self):
        self.__menu = MenuScreen("SHIFT FAILED", [
            ("VIEW STATS",  self.__show_stat),
            ("RETURN HOME", self.__return_home),
        ])

    def __build_complete(self):
        night = self.__gamedata.night
        self.__menu = MenuScreen("SHIFT COMPLETE", [
            ("VIEW STATS",  self.__show_stat),
            (f"Continue at night {night}", self.__continue_game),
            ("RETURN HOME", self.__return_home),
        ])

    # ── State transitions ────────────────────────────────────────────────

    def __continue_game(self):
        self.__gamedata.init_new_game()  # ← move before StationManager
        self.__station_manager = StationManager(
            self.__game_wrapper, self.__on_station_switch, self.__gamedata
        )
        self.__clock.tick()  # ← drain accumulated time before playing starts
        self.__state = "playing"
        self.__menu  = None

    def __new_game(self):
        self.__gamedata.restart_data()
        self.__station_manager = StationManager(
            self.__game_wrapper, self.__on_station_switch, self.__gamedata
        )
        self.__clock.tick()  # ← same here
        self.__state = "playing"
        self.__menu  = None

    def __pause(self):
        self.__build_pause()
        self.__state = "paused"
        self.__audio_manager.pause_all()

    def __resume(self):
        self.__clock.tick()  # ← drain pause time
        self.__state = "playing"
        self.__menu  = None
        self.__audio_manager.resume_all()

    def __return_home(self):
        self.__build_menu()
        self.__state = "menu"
        self.__audio_manager.kill_all_sounds()

    def __quit(self):
        self.__running = False

    # ── Playing loop ─────────────────────────────────────────────────────

    def __handle_events(self):
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                self.__running = False
                return
            elif event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_p):
                self.__pause()
                return
            elif event.type == pygame.MOUSEBUTTONDOWN:
                pos = self.__input_handler._remap(event.pos)
                if self.__pause_rect and self.__pause_rect.collidepoint(pos):
                    self.__pause()
                    return

        groups = self.__station_manager.get_all_groups()
        self.__input_handler.handle_events(events, *groups)

    def __update(self):
        self.__input_handler.handle_dragging()
        self.__station_manager.update(self.__dt)

    def __render(self):
        self.__game_wrapper.fill((30, 30, 30))
        self.__station_manager.draw()

        held = self.__input_handler.held_item
        if held and self.__input_handler.is_dragging:
            self.__game_wrapper.blit(held.image, held.rect)

        self.__draw_pause_button()

        scaled = pygame.transform.scale(
            self.__game_wrapper, (self.__screen_width, self.__screen_height)
        )
        self.__screen.blit(scaled, (0, 0))
        pygame.display.flip()

    def __draw_pause_button(self):
        """Pause glyph at the top-center of the game surface."""
        cx, cy = GAME_W // 2, 60
        w, h   = 60, 44
        rect   = pygame.Rect(cx - w//2, cy - h//2, w, h)

        pygame.draw.rect(self.__game_wrapper, theme.C_BG,     rect, border_radius=8)
        pygame.draw.rect(self.__game_wrapper, theme.C_BORDER, rect, 2, border_radius=8)
        pygame.draw.rect(self.__game_wrapper, theme.C_TEXT, (cx - 10, cy - 10, 6, 20))
        pygame.draw.rect(self.__game_wrapper, theme.C_TEXT, (cx +  4, cy - 10, 6, 20))

        self.__pause_rect = rect

    def __playing(self):
        self.__dt = self.__clock.tick(self.__fps) / 1000
        self.__handle_events()
        if self.__state != "playing":
            return

        self.__update()

        if self.__gamedata.game_hour.is_over:
            self.__audio_manager.kill_all_sounds()

            self.__gamedata.next_night()
            self.__build_complete()
            self.__state = "complete"
            return

        if self.__gamedata.average_rating < 2:
            self.__audio_manager.kill_all_sounds()
            self.__build_gameover()
            self.__state = "gameover"
            self.__gamedata.restart_data()
            return

        self.__render()

    # ── Menu / paused / gameover / complete loop ─────────────────────────

    def __handle_menu(self):
        # self.__dt = self.__clock.tick(self.__fps) / 1000

        events = pygame.event.get()
        
        # Handle quit and escape directly
        for event in events:
            if event.type == pygame.QUIT:
                self.__running = False
                return
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                if self.__state == "paused":
                    self.__resume()
                    return

        # Pass ALL events including MOUSEMOTION to input handler
        self.__input_handler.handle_events(events, self.__menu)

        if self.__menu is None:
            return

        if self.__state != "paused":
            self.__game_wrapper.fill((30, 30, 30))

        self.__menu.draw(self.__game_wrapper)

        scaled = pygame.transform.scale(
            self.__game_wrapper, (self.__screen_width, self.__screen_height)
        )
        self.__screen.blit(scaled, (0, 0))
        pygame.display.flip()

    # ── Main loop ────────────────────────────────────────────────────────

    def main(self):
        while self.__running:
            if self.__state == "playing":
                self.__playing()
            elif self.__state in ("menu", "paused", "gameover", "complete"):
                self.__handle_menu()
        pygame.quit()