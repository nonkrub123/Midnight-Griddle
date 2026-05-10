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


# ── StatTracker ───────────────────────────────────────────────────────────────

class StatTracker:
    def __init__(self, game_hour: GameHour, gamedata=None, throughput_interval=10.0):
        self._gh                  = game_hour
        self._gamedata            = gamedata
        self._throughput_interval = throughput_interval
        self._throughput_timer    = 0.0

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _hour(self):
        snapped = (self._gh.current_hour * 2) // 1 / 2
        return int(snapped) if snapped == int(snapped) else snapped

    def _elapsed(self):
        return round(self._gh.elapsed, 1)

    def _append(self, filepath, row):
        is_new = not os.path.exists(filepath) or os.path.getsize(filepath) == 0
        with open(filepath, "a", newline="") as f:
            w = csv.writer(f)
            if is_new:
                w.writerow(_HEADERS[filepath])
            w.writerow(row)

    # ── Frame update ──────────────────────────────────────────────────────────



    def update(self, dt, customer_count):
        self._throughput_timer += dt
        if self._throughput_timer >= self._throughput_interval:
            self._throughput_timer -= self._throughput_interval
            self.log_throughput(customer_count)

    # ── 1. Revenue ────────────────────────────────────────────────────────────

    def log_revenue(self, amount: int):
        self._append(REVENUE_CSV, [self._hour(), amount, self._elapsed()])

    # ── 2. Satisfaction ───────────────────────────────────────────────────────

    def log_satisfaction(self, rating: int):
        """Also stores rating in GameData so average_rating stays current."""
        self._append(SATISFACTION_CSV, [self._hour(), rating, self._elapsed()])
        if self._gamedata:
            self._gamedata.add_rating(rating)

    # ── 3. Throughput ─────────────────────────────────────────────────────────

    def log_throughput(self, customer_count: int):
        self._append(THROUGHPUT_CSV, [self._hour(), customer_count, self._elapsed()])

    # ── 4. Assembly Accuracy ──────────────────────────────────────────────────

    def _accuracy_by_count(self, player_items: list[dict], order_items: list[str]) -> float:
        max_score = sum(ItemData.get_prop(i, "weight", 1) for i in order_items)
        if max_score == 0:
            return 0.0

        order_counts: dict[str, int] = {}
        for item_id in order_items:
            order_counts[item_id] = order_counts.get(item_id, 0) + 1

        # Separate cooked vs non-cooked counts for grillables
        player_counts: dict[str, int] = {}
        player_cooked_counts: dict[str, int] = {}
        for p in player_items:
            name = p["name"]
            if ItemData.get_prop(name, "grillable", False):
                if p["cook_state"] == "cooked":
                    player_cooked_counts[name] = player_cooked_counts.get(name, 0) + 1
            else:
                player_counts[name] = player_counts.get(name, 0) + 1

        score = 0
        for item_id, needed in order_counts.items():
            weight = ItemData.get_prop(item_id, "weight", 1)
            if ItemData.get_prop(item_id, "grillable", False):
                matched = min(needed, player_cooked_counts.get(item_id, 0))
            else:
                matched = min(needed, player_counts.get(item_id, 0))
            score += matched * weight

        pct = score / max_score * 100
        return round(pct * 0.8, 1)

    def _accuracy_by_sequence(self, player_items: list[dict], order_items: list[str]) -> float:
        """
        Calculates accuracy based on the Longest Common Subsequence (LCS).
        This rewards the player for keeping ingredients in the correct relative order,
        even if they skip an item or add an extra one in the middle.
        """
        n = len(player_items)
        m = len(order_items)

        if m == 0:
            return 100.0 if n == 0 else 0.0

        # Extract names for comparison
        player_names = [p["name"] for p in player_items]
        
        # 1. Standard LCS DP Table
        # dp[i][j] stores the max weighted score for first i player items and first j order items
        dp = [[0.0] * (m + 1) for _ in range(n + 1)]

        for i in range(1, n + 1):
            for j in range(1, m + 1):
                order_id = order_items[j-1]
                player_item = player_items[i-1]
                
                if player_names[i-1] == order_id:
                    # Calculate weight (only if cooked correctly, matching your original logic)
                    weight = ItemData.get_prop(order_id, "weight", 1)
                    
                    # Check cooking state for grillables
                    is_grillable = ItemData.get_prop(order_id, "grillable", False)
                    if is_grillable and player_item.get("cook_state") != "cooked":
                        # Penalty: You matched the item, but it's raw/burnt. 
                        # We take the best of skipping this item or taking it with 0 weight.
                        dp[i][j] = max(dp[i-1][j], dp[i][j-1])
                    else:
                        dp[i][j] = dp[i-1][j-1] + weight
                else:
                    # Items don't match, take the best path without this match
                    dp[i][j] = max(dp[i-1][j], dp[i][j-1])

        # 2. Calculate Max Possible Score
        max_score = sum(ItemData.get_prop(i, "weight", 1) for i in order_items)
        
        # 3. Final Calculation
        actual_score = dp[n][m]
        pct = (actual_score / max_score * 100) if max_score > 0 else 0.0
        
        # 4. Optional: Penalty for extra items (The "Overstuffed" penalty)
        if n > m:
            penalty = (n - m) * 5.0  # Lose 5% per extra item
            pct = max(0.0, pct - penalty)

        return round(pct, 1)
    
    def log_accuracy(self, player_items: list[dict], order_items: list[str]) -> float:
        """
        Weighted item-by-item comparison. Returns accuracy_pct (0–100).

        player_items : [{"name": str, "cook_state": str|None}] from plate.get_items_with_state()
        order_items  : [item_id, ...] from customer.order (bottom → top)

        Scoring per slot:
        - Wrong item at this position → 0
        - Grillable item (meat): only earns weight if cook_state == "cooked"
        - Non-grillable: position match = full weight

        Final pct = max(index_pct, count_pct) where count_pct is capped at 75.
        """
        max_score = sum(ItemData.get_prop(i, "weight", 1) for i in order_items)

        score = 0
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

        index_pct = round(score / max_score * 100, 1) if max_score > 0 else 0.0
        count_pct = self._accuracy_by_count(player_items, order_items)

        pct = max(index_pct, count_pct)
        self._append(ACCURACY_CSV, [self._hour(), score, max_score, pct, self._elapsed()])
        return pct

    # ── 5. Ingredients Sold ───────────────────────────────────────────────────

    def log_ingredients(self, items_sold: list[str]):
        counts: dict[str, int] = {}
        for item in items_sold:
            counts[item] = counts.get(item, 0) + 1
        for item_id, qty in counts.items():
            sell_price = ItemData.get_prop(item_id, "sell_price", 0)
            revenue    = sell_price * qty
            self._append(INGREDIENTS_CSV, [self._hour(), item_id, qty, revenue, self._elapsed()])

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