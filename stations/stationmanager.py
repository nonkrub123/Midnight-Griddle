from core.settings import *
from core.gamedata import GameData
from ui.interactive import *
from ui.group import *
from ui.factory import ItemFactory
from ui.group_orderui import OrderUI
from stations.customermanager import CustomerManager
from core.stattracker import StatTracker
from core.itemdata import ItemData
from stations.restock_station import RestockStation
from stations.station import *
from ui.group_hud import HUDGroup
import ui.theme as theme

# ─────────────────────────────────────────────────────────────────────────────
# StationManager
# ─────────────────────────────────────────────────────────────────────────────
class StationManager:
    def __init__(self, screen, on_switch_callback, gamedata: GameData):
        self.__screen    = screen
        self.__on_switch = on_switch_callback
        self.__nav_group = UIGroup()

        self.__gamedata = gamedata

        # ── Shared singletons ─────────────────────────────────────────────────
        self.__stat_tracker = StatTracker(gamedata.game_hour,
                                        gamedata=gamedata,
                                        throughput_interval=10)
        self.__customer_manager = CustomerManager(game_data=self.__gamedata,
                                                max_capacity=5,
                                                min_spawn_time=10.0,
                                                max_spawn_time=20.0)
        self.__order_ui = OrderUI(customer_manager=self.__customer_manager)
        self.__hud      = HUDGroup()

        # Tray travels between GrillStation and AssembleStation
        factory    = ItemFactory()
        self.__tray = TrayGroup(
            name         = "tray",
            pos          = theme.POS_TRAY,
            max_capacity = 10,
            base_plate   = factory.create_base_plate("plate", theme.POS_TRAY),
        )

        # ── Stations ──────────────────────────────────────────────────────────
        self.__stations         = self._build_stations(screen)
        self.__current_station  = "order"
        self._create_nav_buttons()

    def _build_stations(self, screen):
        return {
            "order": OrderStation(
                screen, GamePath.get_station("test2.jpg"),
                self.__customer_manager, self.__order_ui,
            ),
            "grill": GrillStation(
                screen, GamePath.get_station("grill.png"),
                self.__gamedata, self.__tray, self.__order_ui,
            ),
            "assemble": AssembleStation(
                screen, GamePath.get_station("test2.jpg"),
                self.__gamedata, self.__tray,
                self.__order_ui, self.__customer_manager, self.__stat_tracker,
            ),
            "restock": RestockStation(
                screen, GamePath.get_station("test2.jpg"),
                self.__gamedata,
            ),
        }

    def _create_nav_buttons(self):
        for target, pos in theme.POS_NAV.items():
            btn = UIButton(f"btn_{target}", GamePath.get_ui(f"{target}.png"), pos,
                           lambda t=target: self.__switch_station(t), anchor="topleft")
            self.__nav_group.add(btn)

    def __switch_station(self, target):
        self.__current_station = target
        self.__on_switch()

    def get_active_station(self):
        return self.__stations[self.__current_station]

    def get_all_groups(self):
        return self.get_active_station().get_all_groups() + [self.__nav_group]

    def update(self, dt):
        self.__gamedata.game_hour.update(dt)

        # ── Single tick point for the customer model ──────────────────────────
        self.__customer_manager.update(dt)
        expired  = self.__customer_manager.update_ordering(dt)
        expired += self.__customer_manager.update_waiting(dt)

        for customer in expired:
            self.__stat_tracker.log_satisfaction(0)

        customer_count = (len(self.__customer_manager.on_ordering)
                        + len(self.__customer_manager.on_waiting))
        self.__stat_tracker.update(dt, customer_count)

        self.__hud.refresh(self.__gamedata.game_hour, self.__gamedata)
        self.__order_ui.update_ui(dt)

        for station in self.__stations.values():
            station.update(dt)

    def draw(self):
        self.get_active_station().draw_background()
        for group in self.get_active_station().get_all_groups():
            group.draw(self.__screen)
        self.__nav_group.draw(self.__screen)
        self.__hud.draw(self.__screen)