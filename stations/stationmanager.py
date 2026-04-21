from core.settings import *
from core.gamedata import GameData
from ui.interactive import *
from ui.group import *
from ui.factory import ItemFactory
from ui.orderui import OrderUI
from stations.customermanager import CustomerManager
from core.stattracker import GameHour, StatTracker
from core.itemdata import ItemData
from stations.restock_station import RestockStation
from stations.station import *
from ui.hud import HUDGroup
import ui.theme as theme

# ─────────────────────────────────────────────────────────────────────────────
# StationManager
# ─────────────────────────────────────────────────────────────────────────────
class StationManager:
    def __init__(self, screen, on_switch_callback, gamedata: GameData):
        self.__screen    = screen
        self.__on_switch = on_switch_callback
        self.__nav_group = BaseGroup()

        self.gamedata = gamedata

        # ── Shared singletons ─────────────────────────────────────────────────
        self.game_hour        = GameHour(real_seconds_per_hour=120, total_hours=6)
        self.stat_tracker     = StatTracker(self.game_hour,
                                            gamedata=gamedata,
                                            throughput_interval=10)
        self.customer_manager = CustomerManager(max_capacity=5,
                                                min_spawn_time=10.0,
                                                max_spawn_time=20.0)
        self.order_ui = OrderUI()       # uses theme defaults
        self.hud      = HUDGroup()

        # Tray travels between GrillStation and AssembleStation
        factory   = ItemFactory()
        self.tray = TrayGroup(
            name         = "tray",
            pos          = theme.POS_TRAY,
            max_capacity = 10,
            base_plate   = factory.create_base_plate("base_plate", theme.POS_TRAY),
        )

        # ── Stations ──────────────────────────────────────────────────────────
        self.stations = self._build_stations(screen, factory)
        self.current_station = "order"
        self._create_nav_buttons()

    def _build_stations(self, screen, factory):
        return {
            "order": OrderStation(
                screen, GamePath.get_station("test2.jpg"),
                self.customer_manager, self.order_ui,
            ),
            "grill": GrillStation(
                screen, GamePath.get_station("grill.png"),
                self.gamedata, self.tray, self.order_ui,
            ),
            "assemble": AssembleStation(
                screen, GamePath.get_station("test2.jpg"),
                self.gamedata, self.tray,
                self.order_ui, self.customer_manager, self.stat_tracker,
            ),
            "restock": RestockStation(
                screen, GamePath.get_station("test2.jpg"),
                self.gamedata,
            ),
        }

    def _create_nav_buttons(self):
        for target, pos in theme.POS_NAV.items():
            name = f"btn_{target}"
            btn  = UIButton(name, GamePath.get_ui(f"{target}.png"), pos,
                            lambda t=target: self.switch_station(t), anchor="topleft")
            self.__nav_group.add(btn)

    def switch_station(self, target):
        self.current_station = target
        self.__on_switch(self.get_all_groups())

    def get_active_station(self):
        return self.stations[self.current_station]

    def get_all_groups(self):
        return self.get_active_station().get_all_groups() + [self.__nav_group]

    def update(self, dt):
        self.game_hour.update(dt)

        # ── Single tick point for the customer model ──────────────────────────
        self.customer_manager.update(dt)            # spawn
        self.customer_manager.update_ordering(dt)   # ordering patience
        self.customer_manager.update_waiting(dt)    # waiting  patience

        customer_count = (len(self.customer_manager.on_ordering)
                        + len(self.customer_manager.on_waiting))
        self.stat_tracker.update(dt, customer_count)

        # HUD + OrderUI redraw every frame (both are shared across stations)
        self.hud.refresh(self.game_hour, self.gamedata)
        self.order_ui.update_ui(dt)

        for station in self.stations.values():
            station.update(dt)
        self.__nav_group.update(dt)

    def draw(self):
        self.get_active_station().draw_background()
        for group in self.get_active_station().get_all_groups():
            group.draw(self.__screen)
        self.__nav_group.draw(self.__screen)
        self.hud.draw(self.__screen)   # always on top