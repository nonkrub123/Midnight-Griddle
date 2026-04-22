"""
customermanager.py
──────────────────
CustomerManager owns all customer lifecycle — spawning, patience ticking,
and phase transitions.

Two queues
──────────
  _ordering  : customers waiting for the player to take their order
  _waiting   : customers whose order was taken, now waiting for food

The Customer itself carries the phase so OrderUI / rating code can read a
single source of truth instead of keeping parallel copies.

Public API
──────────
    manager = CustomerManager()
    manager.update(dt)              # spawn tick
    manager.update_ordering(dt)     # tick ordering-queue patience
    manager.update_waiting(dt)      # tick waiting-queue patience

    manager.take_order()            # ordering → waiting, returns Customer
    manager.finish_order()          # remove from waiting, returns Customer

    manager.on_ordering             # list of customers currently ordering
    manager.on_waiting              # list of customers currently waiting for food
"""

from __future__ import annotations
import random
from collections import deque
import pygame
from core.itemdata import ItemData


# ── Filling pool ──────────────────────────────────────────────────────────────

def _build_filling_pool() -> list[str]:
    skip = {"down_bun", "top_bun"}
    return [k for k in ItemData.get_all_edible()
            if k not in skip]

FILLING_POOL = _build_filling_pool()


# ── Customer ──────────────────────────────────────────────────────────────────

class Customer:
    """
    Self-contained customer state. Anything that needs to read a customer's
    patience / phase reads it off the Customer directly — no snapshots, no
    duplicated fields.
    """
    def __init__(self, image: pygame.Surface, order: list[str],
                 patience_ordering: float, patience_waiting: float):
        self.image             = image
        self.order             = order          # ["down_bun", ..., "top_bun"]

        # Current patience (ticked by CustomerManager)
        self.patience_ordering = patience_ordering
        self.patience_waiting  = patience_waiting

        # Baselines so downstream code can compute ratios (0..1)
        self.start_patience_ordering = patience_ordering
        self.start_patience_waiting  = patience_waiting

        # Single source of truth for phase: "ordering" | "waiting" | "done"
        self.phase   = "ordering"
        self.is_late = False
        self.ordering_ratio_at_accept: float | None = None

    # Convenience read-throughs for rating / UI code
    @property
    def ordering_ratio(self) -> float:
        return self.patience_ordering / max(1, self.start_patience_ordering)

    @property
    def waiting_ratio(self) -> float:
        return self.patience_waiting / max(1, self.start_patience_waiting)


# ── CustomerManager ───────────────────────────────────────────────────────────

class CustomerManager:
    """
    Parameters
    ----------
    max_capacity   : max customers in the ordering queue at once
    min_spawn_time : min seconds between spawns
    max_spawn_time : max seconds between spawns
    min_fillings   : min filling items between the buns
    max_fillings   : max filling items between the buns
    """

    def __init__(self, max_capacity=5, min_spawn_time=10.0, max_spawn_time=20.0,
                 min_fillings=3, max_fillings=7):
        self._max_capacity   = max_capacity
        self._min_spawn_time = min_spawn_time
        self._max_spawn_time = max_spawn_time
        self._min_fillings   = min_fillings
        self._max_fillings   = max_fillings

        self._ordering: deque[Customer] = deque()   # waiting to have order taken
        self._waiting:  list[Customer]  = []         # order taken, waiting for food

        self._timer   = 0.0
        self._next_at = self._roll()
        self._avatars = self._make_avatars()

    # ── Properties ────────────────────────────────────────────────────────────

    @property
    def on_ordering(self) -> list[Customer]:
        """All customers waiting to give their order."""
        return list(self._ordering)

    @property
    def on_waiting(self) -> list[Customer]:
        """All customers waiting for their food."""
        return list(self._waiting)

    def is_empty(self) -> bool:
        return len(self._ordering) == 0

    def get_customer(self) -> "Customer | None":
        """Alias for take_order() — kept for compatibility."""
        return self.take_order()

    # ── Main actions ──────────────────────────────────────────────────────────

    def take_order(self) -> Customer | None:
        if not self._ordering:
            return None
        customer       = self._ordering.popleft()
        customer.phase = "waiting"
        customer.ordering_ratio_at_accept = customer.ordering_ratio
        self._waiting.append(customer)
        return customer

    def finish_order(self, customer: Customer | None = None) -> Customer | None:
        """
        Remove an order from the waiting queue. Flips phase to "done".
        Pass a specific Customer to finish them, or leave None for FIFO.
        Returns the finished Customer, or None if waiting is empty.
        """
        if not self._waiting:
            return None
        if customer and customer in self._waiting:
            self._waiting.remove(customer)
            customer.phase = "done"
            return customer
        c = self._waiting.pop(0)
        c.phase = "done"
        return c

    # ── Update ────────────────────────────────────────────────────────────────

    def update(self, dt: float):
        """Spawn timer only — patience is ticked via the dedicated methods."""
        self._try_spawn(dt)

    def update_ordering(self, dt: float) -> list[Customer]:
        """Tick ordering-queue patience. Returns customers who expired this frame."""
        expired: list[Customer] = []
        for c in list(self._ordering):
            c.patience_ordering = max(0.0, c.patience_ordering - dt)
            if c.patience_ordering <= 0:
                c.phase   = "abandoned"
                c.is_late = True
                self._ordering.remove(c)
                expired.append(c)
        return expired

    def update_waiting(self, dt: float) -> list[Customer]:
        """Tick waiting-queue patience. Returns customers who expired this frame."""
        expired: list[Customer] = []
        for c in list(self._waiting):
            c.patience_waiting = max(0.0, c.patience_waiting - dt)
            if c.patience_waiting <= 0:
                c.phase   = "abandoned"
                c.is_late = True
                self._waiting.remove(c)
                expired.append(c)
        return expired

    def _try_spawn(self, dt: float):
        if len(self._ordering) < self._max_capacity:
            self._timer += dt
            if self._timer >= self._next_at:
                self._ordering.append(self._spawn())
                self._timer   = 0.0
                self._next_at = self._roll()

    # ── Spawn helpers ─────────────────────────────────────────────────────────

    def _spawn(self) -> Customer:
        return Customer(
            image             = random.choice(self._avatars).copy(),
            order             = self._build_order(),
            patience_ordering = random.uniform(50.0, 70.0),
            patience_waiting  = random.uniform(70.0, 80.0),
        )

    def _build_order(self) -> list[str]:
        pool_size = len(FILLING_POOL)
        lo = min(self._min_fillings, pool_size)
        hi = min(self._max_fillings, pool_size)
        n = random.randint(lo, hi)
        return ["down_bun"] + random.sample(FILLING_POOL, n) + ["top_bun"]

    def _roll(self) -> float:
        return random.uniform(self._min_spawn_time, self._max_spawn_time)

    def _make_avatars(self) -> list[pygame.Surface]:
        colours = [(220,120,80),(80,160,220),(100,200,120),(200,180,60),(180,80,180)]
        avatars = []
        for c in colours:
            surf = pygame.Surface((64, 64), pygame.SRCALPHA)
            pygame.draw.circle(surf, c, (32, 32), 30)
            avatars.append(surf)
        return avatars