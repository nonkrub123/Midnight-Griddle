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
    manager = CustomerManager(game_data)    # pass GameData reference
    manager.update(dt)                      # spawn tick + difficulty ramp
    manager.update_ordering(dt)             # tick ordering-queue patience
    manager.update_waiting(dt)              # tick waiting-queue patience

    manager.take_order()            # ordering → waiting, returns Customer
    manager.finish_order()          # remove from waiting, returns Customer

    manager.on_ordering             # list of customers currently ordering
    manager.on_waiting              # list of customers currently waiting for food

Difficulty system — two axes
─────────────────────────────
  Final difficulty = night_baseline × time_ramp(t)

  1. NIGHT BASELINE  — permanent per-night multiplier read from GameData.night
     Each successive night starts harder and has a higher personal ceiling:

         night_baseline = 1.0 + (night - 1) * NIGHT_SCALE

     With NIGHT_SCALE = 0.12:
       Night 1 → baseline = 1.00  (normal)
       Night 2 → baseline = 1.12  (+12 %)
       Night 3 → baseline = 1.24
       Night 5 → baseline = 1.48
       Night 10 → baseline = 2.08  (already harder before the clock starts)

  2. TIME RAMP  — exponential-saturation curve within each night,
     scaled so it still reaches DIFFICULTY_CAP regardless of baseline:

         ramp(t) = baseline + (CAP - baseline) * (1 - exp(-k * t))

     This means the ramp always drives toward the same absolute cap,
     but later nights arrive there faster because baseline is already higher.

  Combined example (CAP = 5.0, k = 0.000060):
    Night 1, t=0s    → difficulty ≈ 1.00  (opening, calm)
    Night 1, t=300s  → difficulty ≈ 1.08
    Night 1, t=600s  → difficulty ≈ 1.16
    Night 3, t=0s    → difficulty = 1.24  (starts harder)
    Night 3, t=300s  → difficulty ≈ 1.31
    Night 5, t=600s  → difficulty ≈ 1.58
    Night 10, t=600s → difficulty ≈ 2.27
    Any night, t→∞   → difficulty → 5.00  (absolute ceiling)

  What difficulty actually changes:
    • Spawn interval:    divided by difficulty  (spawns faster)
    • Ordering patience: divided by difficulty  (less time to take order)
    • Waiting patience:  divided by difficulty  (less time to cook)
    • Max fillings:      scales up with difficulty (more complex orders)
"""

from __future__ import annotations
import math
import random
from collections import deque
import pygame
from core.itemdata import ItemData


# ── Difficulty constants ───────────────────────────────────────────────────────

DIFFICULTY_CAP  = 5.0        # absolute ceiling across all nights
DIFFICULTY_K    = 0.000060   # ramp reaches ~80% much later in the shift
NIGHT_SCALE     = 0.12       # each extra night raises baseline by +12%

# Hard floors — game stays challenging but never literally unplayable
MIN_PATIENCE_ORDERING = 20.0   # seconds
MIN_PATIENCE_WAITING  = 30.0   # seconds
MIN_SPAWN_INTERVAL    = 6.0    # seconds


# ── Private filling pool ──────────────────────────────────────────────────────

def _build_filling_pool() -> list[str]:
    skip = {"down_bun", "top_bun"}
    return [k for k in ItemData.get_all_edible() if k not in skip]

_FILLING_POOL = _build_filling_pool()


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

        self.patience_ordering = patience_ordering
        self.patience_waiting  = patience_waiting

        self.start_patience_ordering = patience_ordering
        self.start_patience_waiting  = patience_waiting

        self.phase   = "ordering"
        self.is_late = False
        self.ordering_ratio_at_accept: float | None = None

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
    max_capacity          : max customers in the ordering queue at once
    min_spawn_time        : min seconds between spawns at difficulty 1
    max_spawn_time        : max seconds between spawns at difficulty 1
    min_fillings          : min filling items between the buns (at difficulty 1)
    max_fillings          : max filling items between the buns (at difficulty 1)
    min_patience_ordering : floor for ordering patience (seconds)
    min_patience_waiting  : floor for waiting patience (seconds)
    night_duration        : total length of the shift in seconds (used for UI/stats only)
    """

    def __init__(self, game_data,
                 max_capacity=5,
                 min_spawn_time=MIN_SPAWN_INTERVAL, max_spawn_time=30.0,
                 min_fillings=2, max_fillings=5,
                 min_patience_ordering=MIN_PATIENCE_ORDERING,
                 min_patience_waiting=MIN_PATIENCE_WAITING,
                 night_duration=360.0):

        self.__game_data             = game_data
        self.__max_capacity          = max_capacity
        self.__base_min_spawn        = min_spawn_time
        self.__base_max_spawn        = max_spawn_time
        self.__min_fillings          = min_fillings
        self.__base_max_fill         = max_fillings
        self.__min_patience_ordering = min_patience_ordering
        self.__min_patience_waiting  = min_patience_waiting
        self.night_duration          = night_duration   # read by UI/stats

        self.__ordering: deque[Customer] = deque()
        self.__waiting:  list[Customer]  = []

        self.__night_elapsed  = 0.0
        self.__night_baseline = 1.0
        self.__difficulty     = 1.0

        self.__timer   = 0.0
        self.__next_at = self._roll()

        self.__avatars = self._make_avatars()

    # ── Public properties ─────────────────────────────────────────────────────

    @property
    def difficulty(self) -> float:
        """Current combined difficulty multiplier (night baseline × time ramp)."""
        return self.__difficulty

    @property
    def night_baseline(self) -> float:
        """Permanent per-night starting multiplier (≥ 1.0, grows each night)."""
        return self.__night_baseline

    @property
    def night_elapsed(self) -> float:
        """Seconds elapsed since the shift started."""
        return self.__night_elapsed

    @property
    def night_progress(self) -> float:
        """0.0 → 1.0 fraction of the night that has passed."""
        return min(1.0, self.__night_elapsed / max(1.0, self.night_duration))

    @property
    def on_ordering(self) -> list[Customer]:
        return list(self.__ordering)

    @property
    def on_waiting(self) -> list[Customer]:
        return list(self.__waiting)

    # ── Public methods ────────────────────────────────────────────────────────

    def is_empty(self) -> bool:
        return len(self.__ordering) == 0

    def get_customer(self) -> "Customer | None":
        """Alias for take_order() — kept for compatibility."""
        return self.take_order()

    def take_order(self) -> Customer | None:
        if not self.__ordering:
            return None
        customer       = self.__ordering.popleft()
        customer.phase = "waiting"
        customer.ordering_ratio_at_accept = customer.ordering_ratio
        self.__waiting.append(customer)
        return customer

    def finish_order(self, customer: Customer | None = None) -> Customer | None:
        if not self.__waiting:
            return None
        if customer and customer in self.__waiting:
            self.__waiting.remove(customer)
            customer.phase = "done"
            return customer
        c = self.__waiting.pop(0)
        c.phase = "done"
        return c

    def update(self, dt: float):
        """
        Master update: advance night clock, recompute both difficulty axes, then spawn.
        Reads game_data.night live every frame so it instantly reflects night changes.
        """
        self.__night_elapsed  += dt
        self.__night_baseline  = self._compute_night_baseline(self.__game_data.night)
        self.__difficulty      = self._compute_difficulty(self.__night_elapsed,
                                                          self.__night_baseline)
        self._try_spawn(dt)

    def update_ordering(self, dt: float) -> list[Customer]:
        """Tick ordering-queue patience. Returns customers who expired this frame."""
        expired: list[Customer] = []
        for c in list(self.__ordering):
            c.patience_ordering = max(0.0, c.patience_ordering - dt)
            if c.patience_ordering <= 0:
                c.phase   = "abandoned"
                c.is_late = True
                self.__ordering.remove(c)
                expired.append(c)
        return expired

    def update_waiting(self, dt: float) -> list[Customer]:
        """Tick waiting-queue patience. Returns customers who expired this frame."""
        expired: list[Customer] = []
        for c in list(self.__waiting):
            c.patience_waiting = max(0.0, c.patience_waiting - dt)
            if c.patience_waiting <= 0:
                c.phase   = "abandoned"
                c.is_late = True
                self.__waiting.remove(c)
                expired.append(c)
        return expired

    # ── Private — difficulty ──────────────────────────────────────────────────

    @staticmethod
    def _compute_night_baseline(night: int) -> float:
        raw = 1.0 + (max(1, night) - 1) * NIGHT_SCALE
        return min(raw, DIFFICULTY_CAP * 0.80)

    @staticmethod
    def _compute_difficulty(t: float, baseline: float) -> float:
        ramp = baseline + (DIFFICULTY_CAP - baseline) * (1.0 - math.exp(-DIFFICULTY_K * t))
        return min(ramp, DIFFICULTY_CAP)

    # ── Private — spawn ───────────────────────────────────────────────────────

    def _try_spawn(self, dt: float):
        if len(self.__ordering) < self.__max_capacity:
            self.__timer += dt
            if self.__timer >= self.__next_at:
                self.__ordering.append(self._spawn())
                self.__timer   = 0.0
                self.__next_at = self._roll()

    def _spawn(self) -> Customer:
        d = self.__difficulty
        ord_patience  = max(self.__min_patience_ordering,
                            random.uniform(50.0, 70.0) / d)
        wait_patience = max(self.__min_patience_waiting,
                            random.uniform(80.0, 100.0) / d)
        return Customer(
            image             = random.choice(self.__avatars).copy(),
            order             = self._build_order(),
            patience_ordering = ord_patience,
            patience_waiting  = wait_patience,
        )

    def _build_order(self) -> list[str]:
        pool_size = len(_FILLING_POOL)
        lo = min(self.__min_fillings, pool_size)
        scaled_hi = int(self.__base_max_fill * (1.0 + (self.__difficulty - 1.0) * 0.4))
        hi = min(pool_size, max(lo, scaled_hi))
        n  = random.randint(lo, hi)
        return ["down_bun"] + random.choices(_FILLING_POOL, k=n) + ["top_bun"]

    def _roll(self) -> float:
        d  = self.__difficulty
        lo = max(self.__base_min_spawn, self.__base_min_spawn / d)
        hi = max(self.__base_min_spawn + 2.0, self.__base_max_spawn / d)
        return random.uniform(lo, hi)

    def _make_avatars(self) -> list[pygame.Surface]:
        colours = [(220,120,80),(80,160,220),(100,200,120),(200,180,60),(180,80,180)]
        avatars = []
        for c in colours:
            surf = pygame.Surface((64, 64), pygame.SRCALPHA)
            pygame.draw.circle(surf, c, (32, 32), 30)
            avatars.append(surf)
        return avatars