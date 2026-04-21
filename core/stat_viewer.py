"""
stat_viewer.py
--------------
Standalone Tkinter analytics dashboard for burger game playtesting.

Call show_stat() from anywhere in your game to open the window.
The call BLOCKS until the user closes the window, then resumes normally.

Two dropdowns:
  * View  — which chart to look at (Revenue, Satisfaction, Throughput, ...)
  * Range — "Last 100" rows or "All" rows of CSV data

CSV files expected (resolved via GamePath.get_gamedata):
    revenue_log.csv       game_hour, revenue, real_elapsed_s
    satisfaction_log.csv  game_hour, rating, real_elapsed_s
    throughput_log.csv    game_hour, throughput, real_elapsed_s
    accuracy_log.csv      game_hour, score, max_score, accuracy_pct, real_elapsed_s
    ingredients_log.csv   game_hour, item_id, quantity, revenue, real_elapsed_s

Charts are regenerated each time the View or Range changes.
"""

import os
import tkinter as tk
from tkinter import ttk
from PIL import Image, ImageTk             # pip install pillow
import pandas as pd                        # pip install pandas
import matplotlib                          # pip install matplotlib
matplotlib.use("Agg")                      # off-screen rendering, safe w/ pygame
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from core.settings import GamePath


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CSV_DIR  = os.path.dirname(os.path.abspath(__file__))
IMG_DIR  = GamePath.get_gamedata("stat_img")
IMG_SIZE = (820, 500)

STAT_LABELS = [
    "Net Revenue",
    "Customer Satisfaction",
    "Customer Throughput",
    "Assembly Accuracy",
    "Ingredients Sold",
]

CSV_FILES = {
    "Net Revenue":           "revenue_log.csv",
    "Customer Satisfaction": "satisfaction_log.csv",
    "Customer Throughput":   "throughput_log.csv",
    "Assembly Accuracy":     "accuracy_log.csv",
    "Ingredients Sold":      "ingredients_log.csv",
}

IMG_FILES = {
    k: os.path.join(IMG_DIR, k.lower().replace(" ", "_") + ".png")
    for k in STAT_LABELS
}

# Range toggle — mutated by the UI, read by every chart.
# Dict (not a bare string) so _read() can see UI-side changes without `global`.
RANGE_OPTIONS = ["Last 100", "All"]
_window = {"mode": "Last 100"}


# ---------------------------------------------------------------------------
# Matplotlib dark theme
# ---------------------------------------------------------------------------

BG     = "#1a1a2e"
PANEL  = "#16213e"
ACCENT = "#e94560"
TEXT   = "#eaeaea"
GRID   = "#2a2a4a"

plt.rcParams.update({
    "figure.facecolor": BG,
    "axes.facecolor":   PANEL,
    "axes.edgecolor":   GRID,
    "axes.labelcolor":  TEXT,
    "axes.titlecolor":  TEXT,
    "xtick.color":      TEXT,
    "ytick.color":      TEXT,
    "text.color":       TEXT,
    "grid.color":       GRID,
    "grid.linestyle":   "--",
    "grid.alpha":       0.5,
    "font.family":      "monospace",
})


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _save(fig, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=110, bbox_inches="tight", facecolor=BG)
    plt.close(fig)


def _placeholder(path, filename):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.text(0.5, 0.5, f"No data found\n({filename})",
            ha="center", va="center", fontsize=16, color=ACCENT,
            transform=ax.transAxes)
    ax.axis("off")
    _save(fig, path)


def _apply_window(df):
    """Return the slice of df according to the current range selection."""
    if df is None or df.empty:
        return df
    if _window["mode"] == "Last 100":
        return df.tail(100).reset_index(drop=True)
    return df


def _read(label):
    """Load CSV for this stat and apply the range window."""
    path = CSV_FILES[label]
    src  = GamePath.get_gamedata(path)
    if not os.path.exists(src):
        return None
    df = pd.read_csv(src)
    return _apply_window(df)


def _range_suffix():
    return _window["mode"]


# ---------------------------------------------------------------------------
# Chart generators
# ---------------------------------------------------------------------------

def chart_revenue(out):
    df = _read("Net Revenue")
    if df is None or df.empty or "revenue" not in df.columns:
        return _placeholder(out, CSV_FILES["Net Revenue"])

    fig, ax = plt.subplots(figsize=(8, 5))
    x = range(len(df))
    ax.plot(x, df["revenue"], color=ACCENT, linewidth=2, zorder=3)
    ax.fill_between(x, df["revenue"], alpha=0.15, color=ACCENT)
    ax.set_title(f"Net Revenue  —  {_range_suffix()}", fontsize=14, pad=12)
    ax.set_xlabel("Transaction #")
    ax.set_ylabel("Money")
    ax.grid(True)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    fig.tight_layout()
    _save(fig, out)


def chart_satisfaction(out):
    df = _read("Customer Satisfaction")
    if df is None or df.empty or "rating" not in df.columns:
        return _placeholder(out, CSV_FILES["Customer Satisfaction"])

    counts = df["rating"].value_counts().sort_index()
    colors = [ACCENT, "#17c3b2", "#533483", "#0f3460", "#f8a978", "#84a9c0"][: len(counts)]

    fig, ax = plt.subplots(figsize=(7, 5))
    _, _, autotexts = ax.pie(
        counts.values,
        labels=[f"{int(r)} ★" for r in counts.index],
        colors=colors, autopct="%1.1f%%", startangle=140,
        wedgeprops=dict(edgecolor=BG, linewidth=2),
    )
    for t in autotexts:
        t.set_color(TEXT)
        t.set_fontsize(11)
    ax.set_title(f"Customer Satisfaction  —  {_range_suffix()}", fontsize=14, pad=12)
    fig.tight_layout()
    _save(fig, out)


def chart_throughput(out):
    df = _read("Customer Throughput")
    if df is None or df.empty or "throughput" not in df.columns:
        return _placeholder(out, CSV_FILES["Customer Throughput"])

    counts = df["throughput"].value_counts().sort_index()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(counts.index.astype(str), counts.values,
           color=ACCENT, edgecolor=BG, linewidth=0.8)
    ax.set_title(f"Customer Throughput  —  {_range_suffix()}", fontsize=14, pad=12)
    ax.set_xlabel("Customers in Shop")
    ax.set_ylabel("Frequency")
    ax.grid(True, axis="y")
    fig.tight_layout()
    _save(fig, out)


def chart_accuracy(out):
    df = _read("Assembly Accuracy")
    if df is None or df.empty or "accuracy_pct" not in df.columns:
        return _placeholder(out, CSV_FILES["Assembly Accuracy"])

    mean = df["accuracy_pct"].mean()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(df["accuracy_pct"], bins=20, color=ACCENT,
            edgecolor=BG, linewidth=0.8, range=(0, 100))
    ax.axvline(mean, color="#17c3b2", linewidth=2,
               linestyle="--", label=f"Mean  {mean:.1f}%")
    ax.set_title(f"Assembly Accuracy  —  {_range_suffix()}", fontsize=14, pad=12)
    ax.set_xlabel("Accuracy (%)")
    ax.set_ylabel("Frequency")
    ax.legend()
    ax.grid(True, axis="y")
    fig.tight_layout()
    _save(fig, out)


def chart_ingredients(out):
    df = _read("Ingredients Sold")
    if df is None or df.empty or "item_id" not in df.columns:
        return _placeholder(out, CSV_FILES["Ingredients Sold"])

    grp = df.groupby("item_id")
    summary = pd.DataFrame({
        "Total":   grp["quantity"].sum(),
        "Mean":    grp["quantity"].mean().round(2),
        "StdDev":  grp["quantity"].std().round(2),
        # Graceful fallback: old CSVs (pre-revenue-column) still render
        "Revenue": grp["revenue"].sum() if "revenue" in df.columns else 0,
    }).sort_values("Total", ascending=False).reset_index()

    fig_h = max(3.5, len(summary) * 0.45 + 1.5)
    fig, ax = plt.subplots(figsize=(8, fig_h))
    ax.axis("off")

    col_labels = ["Ingredient", "Total Units", "Mean / Customer",
                  "Std Dev", "Total Revenue"]
    rows = []
    for _, r in summary.iterrows():
        std = r["StdDev"]
        std_s = f"{std:.2f}" if pd.notna(std) else "—"
        rev = int(r["Revenue"]) if pd.notna(r["Revenue"]) else 0
        rows.append([
            r["item_id"],
            int(r["Total"]),
            f'{r["Mean"]:.2f}',
            std_s,
            f'${rev:,}',
        ])

    tbl = ax.table(cellText=rows, colLabels=col_labels,
                   cellLoc="center", loc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(11)
    tbl.scale(1, 1.6)

    for j in range(len(col_labels)):
        tbl[0, j].set_facecolor(ACCENT)
        tbl[0, j].set_text_props(color=TEXT, fontweight="bold")
        tbl[0, j].set_edgecolor(GRID)

    for i in range(1, len(rows) + 1):
        fc = "#1e1e3a" if i % 2 == 0 else PANEL
        for j in range(len(col_labels)):
            tbl[i, j].set_facecolor(fc)
            tbl[i, j].set_text_props(color=TEXT)
            tbl[i, j].set_edgecolor(GRID)

    ax.set_title(f"Ingredients Sold  —  {_range_suffix()}",
                 fontsize=14, pad=16, color=TEXT)
    fig.tight_layout()
    _save(fig, out)


CHART_FUNCS = {
    "Net Revenue":           chart_revenue,
    "Customer Satisfaction": chart_satisfaction,
    "Customer Throughput":   chart_throughput,
    "Assembly Accuracy":     chart_accuracy,
    "Ingredients Sold":      chart_ingredients,
}


def generate_all_charts():
    """Re-generate every chart PNG from the current CSV data."""
    for label, func in CHART_FUNCS.items():
        func(IMG_FILES[label])


# ---------------------------------------------------------------------------
# Tkinter window
# ---------------------------------------------------------------------------

class StatViewer(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Playtesting Analytics")
        self.resizable(False, False)
        self.configure(bg=BG)
        self._photo = None
        self._build_ui()
        self._select(STAT_LABELS[0])

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=BG)
        hdr.pack(fill="x", padx=20, pady=(14, 2))
        tk.Label(hdr, text="Playtesting Analytics",
                 bg=BG, fg=ACCENT,
                 font=("Courier New", 15, "bold")).pack(side="left")

        # Controls row — View dropdown + Range dropdown
        ctrl = tk.Frame(self, bg=BG)
        ctrl.pack(fill="x", padx=20, pady=(4, 8))

        tk.Label(ctrl, text="View:", bg=BG, fg=TEXT,
                 font=("Courier New", 11)).pack(side="left", padx=(0, 6))

        self._stat_var = tk.StringVar(value=STAT_LABELS[0])
        stat_combo = ttk.Combobox(ctrl, textvariable=self._stat_var,
                                  values=STAT_LABELS, state="readonly",
                                  width=28, font=("Courier New", 11))
        stat_combo.pack(side="left")
        stat_combo.bind("<<ComboboxSelected>>",
                        lambda e: self._select(self._stat_var.get()))

        tk.Label(ctrl, text="Range:", bg=BG, fg=TEXT,
                 font=("Courier New", 11)).pack(side="left", padx=(18, 6))

        self._range_var = tk.StringVar(value=_window["mode"])
        range_combo = ttk.Combobox(ctrl, textvariable=self._range_var,
                                   values=RANGE_OPTIONS, state="readonly",
                                   width=12, font=("Courier New", 11))
        range_combo.pack(side="left")
        range_combo.bind("<<ComboboxSelected>>", self._on_range_change)

        # Combobox styling
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox",
                        fieldbackground=PANEL, background=PANEL,
                        foreground=TEXT, selectbackground=ACCENT,
                        arrowcolor=ACCENT)

        # Image canvas
        self._img_label = tk.Label(self, bg=PANEL,
                                   width=IMG_SIZE[0], height=IMG_SIZE[1])
        self._img_label.pack(padx=20, pady=(0, 10))

        # Footer
        tk.Label(self, text="Close this window to continue",
                 bg=BG, fg="#555577",
                 font=("Courier New", 9)).pack(pady=(0, 10))

    def _on_range_change(self, _event):
        """User flipped between 'Last 100' and 'All' — regenerate + reload."""
        _window["mode"] = self._range_var.get()
        generate_all_charts()
        self._select(self._stat_var.get())

    def _select(self, label):
        path = IMG_FILES[label]
        if not os.path.exists(path):
            self._img_label.config(
                image="", text=f"Image not found:\n{path}",
                fg=ACCENT, font=("Courier New", 12))
            return
        img = Image.open(path).resize(IMG_SIZE, Image.LANCZOS)
        self._photo = ImageTk.PhotoImage(img)
        self._img_label.config(image=self._photo, text="")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def show_stat():
    """
    Generate charts from CSVs, open the analytics window, and BLOCK
    until the user closes it. Safe to call from anywhere in your game.

    Usage:
        from core.stat_viewer import show_stat
        show_stat()          # blocks until user closes the window
    """
    generate_all_charts()
    app = StatViewer()
    app.mainloop()


# ---------------------------------------------------------------------------
# Run standalone for testing
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    show_stat()