from settings import *

import pygame

class GameData:
    def __init__(self):
        # --- Private Attributes ---
        self._dt = 0
        self._events = []
        self._money = 100
        self._held_item = None
        self._inventory = []
        self._current_station_name = "order"
        self._is_paused = False

    # --- NEW GETTERS ---
    @property
    def dt(self):
        """Returns the delta time for the current frame."""
        return self._dt

    @property
    def events(self):
        """Returns the list of pygame events for the current frame."""
        return self._events

    # --- EXISTING GETTERS ---
    @property
    def money(self): return self._money

    @property
    def held_item(self): return self._held_item

    @property
    def current_station(self): return self._current_station_name

    # --- NEW SETTERS (The "Pump") ---
    def update_frame_data(self, dt, events):
        """
        Called once per frame by the GameManager 
        to refresh the global 'heartbeat'.
        """
        self._dt = dt
        self._events = events

    # --- EXISTING SETTERS ---
    def change_station(self, station_name):
        self._current_station_name = station_name

    def add_money(self, amount):
        if amount > 0: self._money += amount

    def grab_item(self, item):
        if self._held_item is None:
            self._held_item = item
            item.dragging = True
            return True
        return False

    def release_item(self):
        if self._held_item:
            item = self._held_item
            item.dragging = False
            self._held_item = None
            return item
        return None