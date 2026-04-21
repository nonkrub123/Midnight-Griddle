"""
stattracker.py
──────────────
GameHour    : Converts real dt into in-game hours (0 → 6 in 0.5 steps).
StatTracker : Records 5 gameplay stats to separate CSV files.

Rating formula (1–5 stars)
──────────────────────────
  20% ordering_ratio  — patience remaining when player accepted the order
  60% accuracy_pct    — weighted item correctness (0–100)
  20% waiting_ratio   — patience remaining when food was served

CSV columns
───────────
  revenue_log.csv      game_hour, revenue, real_elapsed_s
  satisfaction_log.csv game_hour, rating, real_elapsed_s
  throughput_log.csv   game_hour, throughput, real_elapsed_s
  accuracy_log.csv     game_hour, score, max_score, accuracy_pct, real_elapsed_s
  ingredients_log.csv  game_hour, item_id, quantity, real_elapsed_s
"""

from __future__ import annotations
import csv, os
from core.settings  import GamePath
from core.itemdata  import ItemData


# ── File paths ────────────────────────────────────────────────────────────────

def _path(filename):
    p = GamePath.get_gamedata(filename)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    return p

REVENUE_CSV      = _path("revenue_log.csv")
SATISFACTION_CSV = _path("satisfaction_log.csv")
THROUGHPUT_CSV   = _path("throughput_log.csv")
ACCURACY_CSV     = _path("accuracy_log.csv")
INGREDIENTS_CSV  = _path("ingredients_log.csv")

_HEADERS = {
    REVENUE_CSV:      ["game_hour", "revenue",    "real_elapsed_s"],
    SATISFACTION_CSV: ["game_hour", "rating",     "real_elapsed_s"],
    THROUGHPUT_CSV:   ["game_hour", "throughput", "real_elapsed_s"],
    ACCURACY_CSV:     ["game_hour", "score", "max_score", "accuracy_pct", "real_elapsed_s"],
    INGREDIENTS_CSV:  ["game_hour", "item_id", "quantity", "revenue", "real_elapsed_s"]
}

def _append(filepath, row):
    is_new = not os.path.exists(filepath) or os.path.getsize(filepath) == 0
    with open(filepath, "a", newline="") as f:
        w = csv.writer(f)
        if is_new:
            w.writerow(_HEADERS[filepath])
        w.writerow(row)


# ── GameHour ──────────────────────────────────────────────────────────────────

class GameHour:
    """
    real_seconds_per_hour : real seconds = one game hour  (default 120)
    total_hours           : shift length in game hours     (default 6)
    """
    def __init__(self, real_seconds_per_hour=120.0, total_hours=6.0):
        self._rate        = real_seconds_per_hour
        self._total_hours = total_hours
        self._elapsed     = 0.0

    def update(self, dt):
        if not self.is_over:
            self._elapsed += dt

    @property
    def current_hour(self) -> float:
        return self._elapsed / self._rate

    @property
    def hour_label(self) -> str:
        """Returns '0', '0.5', '1', '1.5' ... '6'."""
        snapped = round(self.current_hour * 2) / 2
        return str(int(snapped) if snapped == int(snapped) else snapped)

    @property
    def is_over(self) -> bool:
        return self.current_hour >= self._total_hours

    @property
    def progress(self) -> float:
        return min(self.current_hour / self._total_hours, 1.0)


# ── StatTracker ───────────────────────────────────────────────────────────────

class StatTracker:
    def __init__(self, game_hour: GameHour, gamedata=None, throughput_interval=10.0):
        self._gh                  = game_hour
        self._gamedata            = gamedata
        self._throughput_interval = throughput_interval
        self._throughput_timer    = 0.0
        self._real_elapsed        = 0.0

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _hour(self):
        snapped = round(self._gh.current_hour * 2) / 2
        return int(snapped) if snapped == int(snapped) else snapped

    def _elapsed(self):
        return round(self._real_elapsed, 1)

    # ── Frame update ──────────────────────────────────────────────────────────

    def update(self, dt, customer_count):
        self._real_elapsed     += dt
        self._throughput_timer += dt
        if self._throughput_timer >= self._throughput_interval:
            self._throughput_timer -= self._throughput_interval
            self.log_throughput(customer_count)

    # ── 1. Revenue ────────────────────────────────────────────────────────────

    def log_revenue(self, amount: int):
        _append(REVENUE_CSV, [self._hour(), amount, self._elapsed()])

    # ── 2. Satisfaction ───────────────────────────────────────────────────────

    def log_satisfaction(self, rating: int):
        """Also stores rating in GameData so average_rating stays current."""
        _append(SATISFACTION_CSV, [self._hour(), rating, self._elapsed()])
        if self._gamedata:
            self._gamedata.add_rating(rating)

    # ── 3. Throughput ─────────────────────────────────────────────────────────

    def log_throughput(self, customer_count: int):
        _append(THROUGHPUT_CSV, [self._hour(), customer_count, self._elapsed()])

    # ── 4. Assembly Accuracy ──────────────────────────────────────────────────

    def log_accuracy(self, player_items: list[dict], order_items: list[str]) -> float:
        """
        Weighted item-by-item comparison. Returns accuracy_pct (0–100).

        player_items : [{"name": str, "cook_state": str|None}] from plate.get_items_with_state()
        order_items  : [item_id, ...] from customer.order (bottom → top)

        Scoring per slot:
          - Wrong item at this position → 0
          - Grillable item (meat): only earns weight if cook_state == "cooked"
          - Non-grillable: position match = full weight
        """
        max_score = sum(ItemData.get_prop(i, "weight", 1) for i in order_items)
        score     = 0

        for i, order_id in enumerate(order_items):
            if i >= len(player_items):
                break
            player      = player_items[i]
            item_weight = ItemData.get_prop(order_id, "weight", 1)
            if player["name"] != order_id:
                continue
            if ItemData.get_prop(order_id, "grillable", False):
                if player["cook_state"] == "cooked":
                    score += item_weight
            else:
                score += item_weight

        pct = round(score / max_score * 100, 1) if max_score > 0 else 0.0
        _append(ACCURACY_CSV, [self._hour(), score, max_score, pct, self._elapsed()])
        return pct

    # ── 5. Ingredients Sold ───────────────────────────────────────────────────

    def log_ingredients(self, items_sold: list[str]):
        counts: dict[str, int] = {}
        for item in items_sold:
            counts[item] = counts.get(item, 0) + 1
        for item_id, qty in counts.items():
            sell_price = ItemData.get_prop(item_id, "sell_price", 0)
            revenue    = sell_price * qty
            _append(INGREDIENTS_CSV, [self._hour(), item_id, qty, revenue, self._elapsed()])

    # ── Rating ────────────────────────────────────────────────────────────────

    @staticmethod
    def compute_rating(ordering_ratio: float,
                    accuracy_pct:   float,
                    waiting_ratio:  float) -> int:
        """
        Composite 0–5 star rating. Accuracy is the gate — the ordering/waiting
        patience bonuses are scaled by accuracy, so serving the wrong burger
        never earns points for being fast.

        composite = accuracy × (60% base + 20% × ordering_ratio + 20% × waiting_ratio)

        0%  accuracy, any patience   → 0 ★
        100% accuracy, 0   patience  → 3 ★   (only the base 60%)
        100% accuracy, full patience → 5 ★
        50%  accuracy, full patience → 2–3 ★
        """
        acc       = accuracy_pct / 100.0
        composite = acc * (0.60 + 0.20 * ordering_ratio + 0.20 * waiting_ratio)
        return max(0, min(5, round(composite * 5)))