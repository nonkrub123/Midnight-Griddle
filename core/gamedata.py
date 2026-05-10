"""
gamedata.py
───────────
GameData — shared mutable game state passed around by reference.

Responsibilities
────────────────
- Frame heartbeat (dt, events)
- Money
- Item stock  (item_id → count, -1 = infinite)
- Held-item tracking (for drag state)
- Current station name
- Game hour / shift clock
"""

from core.settings import *
from core.itemdata import ItemData
import csv
import os

# ── GameHour ──────────────────────────────────────────────────────────────────

class GameHour:
    """
    real_seconds_per_hour : real seconds = one game hour  (default 60)
    total_hours           : shift length in game hours     (default 6)
    """
    def __init__(self, real_seconds_per_hour=60.0, total_hours=6.0):
        self.__rate        = real_seconds_per_hour
        self.__total_hours = total_hours
        self.__elapsed     = 0.0

    def update(self, dt):
        if not self.is_over:
            self.__elapsed += dt

    def restart(self):
        self.__elapsed = 0

    @property
    def elapsed(self):
        return self.__elapsed
    
    @property
    def current_hour(self) -> float:
        return self.__elapsed / self.__rate

    @property
    def hour_label(self) -> str:
        """Returns '0', '0.5', '1', '1.5' ... '6'."""
        snapped = (self.current_hour * 2) // 1 / 2
        return str(int(snapped) if snapped == int(snapped) else snapped)

    @property
    def is_over(self) -> bool:
        return self.current_hour >= self.__total_hours

    @property
    def progress(self) -> float:
        return min(self.current_hour / self.__total_hours, 1.0)

# ── GameData ──────────────────────────────────────────────────────────────────

class GameData:
    def __init__(self):
        self.save_path = GamePath.get_statdata("gameplay.csv")
        self.__money   = 100
        self.__night   = 1
        self.__ratings: list[int] = [5]
        self.__stock: dict[str, int] = {}
        for item_id in ItemData.get_all_edible():
            self.__stock[item_id] = 10

        self.game_hour = GameHour(real_seconds_per_hour=60, total_hours=6)

        self.load()  # auto-load on init if save exists


    # ── Save / Load ───────────────────────────────────────────────────────────

    def save(self):
        with open(self.save_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["money",   self.__money])
            writer.writerow(["night",   self.__night])
            writer.writerow(["ratings", *self.__ratings])
            for item_id, count in self.__stock.items():
                writer.writerow(["stock", item_id, count])

    def load(self):
        if not os.path.exists(self.save_path):
            return  # no save file yet, keep defaults
        with open(self.save_path, "r") as f:
            reader = csv.reader(f)
            for row in reader:
                if not row:
                    continue
                key = row[0]
                if key == "money":
                    self.__money = int(row[1])
                elif key == "night":
                    self.__night = int(row[1])
                elif key == "ratings":
                    self.__ratings = [int(x) for x in row[1:] if x]
                elif key == "stock" and row[1] in self.__stock:
                    self.__stock[row[1]] = int(row[2])

    # ── Money ─────────────────────────────────────────────────────────────────

    @property
    def money(self) -> int:
        return self.__money

    def add_money(self, amount: int):
        if amount > 0:
            self.__money += amount

    def spend_money(self, amount: int) -> bool:
        if amount <= self.__money:
            self.__money -= amount
            return True
        return False

    # ── Night ─────────────────────────────────────────────────────────────────

    @property
    def night(self) -> int:
        return self.__night

    def next_night(self):
        self.__night += 1

    # ── Rating ────────────────────────────────────────────────────────────────

    @property
    def average_rating(self) -> float:
        if not self.__ratings:
            return 0.0
        return sum(self.__ratings) / len(self.__ratings)

    def add_rating(self, score: int):
        self.__ratings.append(score)

    # ── Stock ─────────────────────────────────────────────────────────────────

    def get_stock(self, item_id: str) -> int:
        return self.__stock.get(item_id, 0)

    def has_stock(self, item_id: str, amount: int = 1) -> bool:
        return self.__stock.get(item_id, 0) >= amount

    def add_stock(self, item_id: str, amount: int):
        if item_id in self.__stock:
            self.__stock[item_id] += amount

    def use_stock(self, item_id: str, amount: int = 1) -> bool:
        if self.has_stock(item_id, amount):
            self.__stock[item_id] -= amount
            return True
        return False

    def restock(self, item_id: str, amount: int) -> bool:
        """Buy stock using buy_price from ItemData. Returns False if insufficient funds."""
        cost = ItemData.get_prop(item_id, "buy_price", 0) * amount
        if self.spend_money(cost):
            self.add_stock(item_id, amount)
            return True
        return False

    # ── Restart ───────────────────────────────────────────────────────────────
    def init_new_game(self):
        self.game_hour.restart()

    def set_night1_stat(self):
        self.init_new_game()
        self.save_path = GamePath.get_statdata("gameplay.csv")
        self.__money   = 100
        self.__night   = 1
        self.__ratings: list[int] = [5]
        self.__stock: dict[str, int] = {}
        for item_id in ItemData.get_all_edible():
            self.__stock[item_id] = 10
        self.game_hour = GameHour(real_seconds_per_hour=60, total_hours=6)

    def restart_data(self):
        print("Restarting the game Data")
        self.set_night1_stat()
        with open(self.save_path, 'w', newline='') as f:
            pass