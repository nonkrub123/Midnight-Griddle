from settings import *
from gamedata import *
from interactive import *
from group import *
from factory import *

class StationManager:
    def __init__(self, screen, on_switch_callback):
        self.__screen = screen
        self.__on_switch = on_switch_callback

        self.__nav_group = BaseGroup()

        self.game_data = GameData()
        self._seed_stock()

        self.stations = {
            "order": TestStation(self.__screen, GamePath.get_station("test.png")),
            "grill": Station(self.__screen, GamePath.get_station("test.png")),
        }
        self.current_station = "order"
        self.create_nav_buttons()

    def _seed_stock(self):
        self.game_data.set_stock("meat",   10)
        self.game_data.set_stock("bun",    -1)
        self.game_data.set_stock("cheese",  5)

    def create_nav_buttons(self):
        b1 = UIButton("button1", GamePath.get_ui("20.png"), (10,  550), lambda: self.switch_station("order"))
        b2 = UIButton("button2", GamePath.get_ui("20.png"), (120, 550), lambda: self.switch_station("grill"))
        self.__nav_group.add(b1, b2)

    def get_active_station(self):
        return self.stations[self.current_station]

    def switch_station(self, target):
        self.current_station = target
        self.__on_switch(self.get_all_groups())

    def get_all_groups(self):
        """Station groups first, nav on top."""
        return self.get_active_station().get_all_groups() + [self.__nav_group]

    def update(self, dt):
        for station in self.stations.values():
            station.update(dt)
        self.__nav_group.update(dt)

    def draw(self):
        """Single entry point for all rendering."""
        # 1. Background
        self.get_active_station().draw_background()
        # 2. Every group in the active station
        for group in self.get_active_station().get_all_groups():
            group.draw(self.__screen)
        # 3. Nav buttons always on top
        self.__nav_group.draw(self.__screen)


# ── Base Station ──────────────────────────────────────────────────────────────

class Station:
    def __init__(self, screen, bg_image_path):
        self.screen     = screen
        self.background = pygame.image.load(bg_image_path).convert()
        self.all_groups: list[BaseGroup] = []

    def register_group(self, group: BaseGroup):
        self.all_groups.append(group)

    def get_all_groups(self):
        return list(self.all_groups)

    def update(self, dt):
        for group in self.all_groups:
            group.update(dt)

    def draw_background(self):
        self.screen.blit(self.background, (0, 0))


# ── Test Station ──────────────────────────────────────────────────────────────

class TestStation(Station):
    def __init__(self, screen, bg_image_path):
        super().__init__(screen, bg_image_path)
        self.factory = ItemFactory()

        item1 = self.factory.create("top_bun", (100, 100))
        item2 = self.factory.create("top_bun", (400, 100))

        self.basegroup = BaseGroup()
        self.basegroup.add(item1, item2)
        self.register_group(self.basegroup)


# ── Grill Station ─────────────────────────────────────────────────────────────

class GrillStation(Station):
    def __init__(self, screen, bg_image_path, game_data: GameData):
        super().__init__(screen, bg_image_path)
        self.game_data = game_data
        self.factory   = ItemFactory()

        self.grill = GrillGroup(
            "grill", GamePath.get_ingredients("meat_burn.png"), (100, 100), max_capacity=2
        )
        self.plate = PlateGroup(
            "plate", GamePath.get_ingredients("bun2.png"), (400, 100), max_capacity=20
        )
        self.loose_group = BaseGroup()

        meat_template = self.factory.create("meat", pos=(0, 0))
        self.meat_dispenser = DispenserGroup(
            name          = "meat_dispenser",
            image_path    = GamePath.get_station("20.png"),
            pos           = (700, 400),
            template_item = meat_template,
            game_data     = game_data,
            item_id       = "meat",
            cost          = 0,
            out_group     = self.loose_group,
        )

        self.register_group(self.grill)
        self.register_group(self.plate)
        self.register_group(self.loose_group)
        self.register_group(self.meat_dispenser)