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
"""

from core.settings import *
from core.itemdata import ItemData

import csv
import os


class GameData:
    def __init__(self):
        self.save_path = GamePath.get_statdata("gameplay.csv")
        self._money   = 100
        self._night   = 1
        self._ratings: list[int] = [5]
        self._stock: dict[str, int] = {}
        for item_id in ItemData.get_all_edible():
            self._stock[item_id] = 10
        self._hour = 0
        
        self.load()  # auto-load on init if save exists


    # ── Save / Load ───────────────────────────────────────────────────────────

    def save(self):
        with open(self.save_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["money",   self._money])
            writer.writerow(["night",   self._night])
            writer.writerow(["ratings", *self._ratings])
            for item_id, count in self._stock.items():
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
                    self._money = int(row[1])
                elif key == "night":
                    self._night = int(row[1])
                elif key == "ratings":
                    self._ratings = [int(x) for x in row[1:] if x]
                elif key == "stock" and row[1] in self._stock:
                    self._stock[row[1]] = int(row[2])

# ── Money ─────────────────────────────────────────────────────────────────

    @property
    def money(self) -> int:
        return self._money

    def add_money(self, amount: int):
        if amount > 0:
            self._money += amount

    def spend_money(self, amount: int) -> bool:
        if amount <= self._money:
            self._money -= amount
            return True
        return False
    
    # ── Night ─────────────────────────────────────────────────────────────────

    @property
    def night(self) -> int:
        return self._night

    def next_night(self):
        self._night += 1

    # ── Rating ────────────────────────────────────────────────────────────────

    @property
    def average_rating(self) -> float:
        if not self._ratings:
            return 0.0
        return sum(self._ratings) / len(self._ratings)

    def add_rating(self, score: int):
        self._ratings.append(score)

    # ── Stock ─────────────────────────────────────────────────────────────────

    def get_stock(self, item_id: str) -> int:
        return self._stock.get(item_id, 0)

    def has_stock(self, item_id: str, amount: int = 1) -> bool:
        return self._stock.get(item_id, 0) >= amount

    def add_stock(self, item_id: str, amount: int):
        if item_id in self._stock:
            self._stock[item_id] += amount

    def use_stock(self, item_id: str, amount: int = 1) -> bool:
        if self.has_stock(item_id, amount):
            self._stock[item_id] -= amount
            return True
        return False

    def restock(self, item_id: str, amount: int) -> bool:
        """Buy stock using buy_price from ItemData. Returns False if insufficient funds."""
        cost = ItemData.get_prop(item_id, "buy_price", 0) * amount
        if self.spend_money(cost):
            self.add_stock(item_id, amount)
            return True
        return False
    
    #  ─ restart --
    def set_start_stat(self):
        self.save_path = GamePath.get_statdata("gameplay.csv")
        self._money   = 100
        self._night   = 1
        self._ratings: list[int] = [5]
        self._stock: dict[str, int] = {}
        for item_id in ItemData.get_all_edible():
            self._stock[item_id] = 10
        self._hour = 0
        
    def restart_data(self):
        print("Restarting the game Data")
        self.set_start_stat()
        with open(self.save_path, 'w', newline='') as f:
            pass

    # ── Hour ─────────────────────────────────────────────────────────────────
    def set_hour(self, hour):
        self._hour = hour
        