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

from settings import *
import pygame


class GameData:
    def __init__(self):
        self._dt     = 0.0
        self._events = []
        self._money  = 100

        self._held_item            = None
        self._current_station_name = "order"
        self._is_paused            = False

        # item_id → int count  (-1 = infinite)
        self._stock: dict[str, int] = {}

    # ── Frame heartbeat ───────────────────────────────────────────────────────

    @property
    def dt(self) -> float:
        return self._dt

    @property
    def events(self) -> list:
        return self._events

    def update_frame_data(self, dt: float, events: list):
        self._dt     = dt
        self._events = events

    # ── Money ─────────────────────────────────────────────────────────────────

    @property
    def money(self) -> int:
        return self._money

    def add_money(self, amount: int):
        if amount > 0:
            self._money += amount

    def spend_money(self, amount: int) -> bool:
        """Deduct amount. Returns True on success, False if insufficient funds."""
        if amount <= self._money:
            self._money -= amount
            return True
        return False

    # ── Stock ─────────────────────────────────────────────────────────────────

    def set_stock(self, item_id: str, count: int):
        """Set stock. Use -1 for infinite."""
        self._stock[item_id] = count

    def get_stock(self, item_id: str) -> int:
        """Returns stock count. Returns 0 if item_id not registered."""
        return self._stock.get(item_id, 0)

    def has_stock(self, item_id: str, amount: int = 1) -> bool:
        stock = self._stock.get(item_id, 0)
        return stock == -1 or stock >= amount

    def add_stock(self, item_id: str, amount: int):
        if item_id not in self._stock:
            self._stock[item_id] = 0
        if self._stock[item_id] != -1:
            self._stock[item_id] += amount

    def use_stock(self, item_id: str, amount: int = 1) -> bool:
        """
        Consume `amount` from stock.
        Returns True on success, False if insufficient (infinite stock always succeeds).
        """
        stock = self._stock.get(item_id, 0)
        if stock == -1:
            return True
        if stock >= amount:
            self._stock[item_id] -= amount
            return True
        return False

    # ── Held item ─────────────────────────────────────────────────────────────

    @property
    def held_item(self):
        return self._held_item

    def grab_item(self, item) -> bool:
        if self._held_item is None:
            self._held_item  = item
            item.dragging    = True
            return True
        return False

    def release_item(self):
        if self._held_item:
            item             = self._held_item
            item.dragging    = False
            self._held_item  = None
            return item
        return None

    # ── Station ───────────────────────────────────────────────────────────────

    @property
    def current_station(self) -> str:
        return self._current_station_name

    def change_station(self, station_name: str):
        self._current_station_name = station_name