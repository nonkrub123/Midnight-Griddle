"""
stat_viewer.py
--------------
Standalone Tkinter analytics dashboard for burger game playtesting.

Call StatViewer.run() from anywhere in your game to open the window.
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
# Private configuration
# ---------------------------------------------------------------------------

_IMG_SIZE = (820, 500)

_STAT_LABELS = [
    "Net Revenue",
    "Customer Satisfaction",
    "Customer Throughput",
    "Assembly Accuracy",
    "Ingredients Sold",
]

_CSV_FILES = {
    "Net Revenue":           "revenue_log.csv",
    "Customer Satisfaction": "satisfaction_log.csv",
    "Customer Throughput":   "throughput_log.csv",
    "Assembly Accuracy":     "accuracy_log.csv",
    "Ingredients Sold":      "ingredients_log.csv",
}

_IMG_FILES = {
    k: os.path.join(GamePath.get_gamedata("stat_img"), k.lower().replace(" ", "_") + ".png")
    for k in _STAT_LABELS
}

# Range toggle — mutated by the UI, read by every chart.
# Dict (not a bare string) so _read() can see UI-side changes without `global`.
_RANGE_OPTIONS = ["Last 100", "All"]
_window = {"mode": "Last 100"}


# ---------------------------------------------------------------------------
# Private matplotlib dark theme
# ---------------------------------------------------------------------------

_BG     = "#1a1a2e"
_PANEL  = "#16213e"
_ACCENT = "#e94560"
_TEXT   = "#eaeaea"
_GRID   = "#2a2a4a"

plt.rcParams.update({
    "figure.facecolor": _BG,
    "axes.facecolor":   _PANEL,
    "axes.edgecolor":   _GRID,
    "axes.labelcolor":  _TEXT,
    "axes.titlecolor":  _TEXT,
    "xtick.color":      _TEXT,
    "ytick.color":      _TEXT,
    "text.color":       _TEXT,
    "grid.color":       _GRID,
    "grid.linestyle":   "--",
    "grid.alpha":       0.5,
    "font.family":      "monospace",
})


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

def _save(fig, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fig.savefig(path, dpi=110, bbox_inches="tight", facecolor=_BG)
    plt.close(fig)


def _placeholder(path, filename):
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.text(0.5, 0.5, f"No data found\n({filename})",
            ha="center", va="center", fontsize=16, color=_ACCENT,
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
    src = GamePath.get_gamedata(_CSV_FILES[label])
    if not os.path.exists(src) or os.path.getsize(src) == 0:
        return None
    try:
        df = pd.read_csv(src, on_bad_lines="skip")
    except Exception as e:
        print(f"[stat_viewer] failed to read {src}: {e}")
        return None
    return _apply_window(df)


def _range_suffix():
    return _window["mode"]


# ---------------------------------------------------------------------------
# Private chart generators
# ---------------------------------------------------------------------------

def _chart_revenue(out):
    df = _read("Net Revenue")
    if df is None or df.empty or "revenue" not in df.columns:
        return _placeholder(out, _CSV_FILES["Net Revenue"])

    fig, ax = plt.subplots(figsize=(8, 5))
    x = range(len(df))
    ax.plot(x, df["revenue"], color=_ACCENT, linewidth=2, zorder=3)
    ax.fill_between(x, df["revenue"], alpha=0.15, color=_ACCENT)
    ax.set_title(f"Net Revenue  —  {_range_suffix()}", fontsize=14, pad=12)
    ax.set_xlabel("Transaction #")
    ax.set_ylabel("Money")
    ax.grid(True)
    ax.yaxis.set_major_formatter(mticker.FuncFormatter(lambda v, _: f"${v:,.0f}"))
    fig.tight_layout()
    _save(fig, out)


def _chart_satisfaction(out):
    df = _read("Customer Satisfaction")
    if df is None or df.empty or "rating" not in df.columns:
        return _placeholder(out, _CSV_FILES["Customer Satisfaction"])

    counts = df["rating"].value_counts().sort_index()
    colors = [_ACCENT, "#17c3b2", "#533483", "#0f3460", "#f8a978", "#84a9c0"][: len(counts)]
    total = counts.values.sum()

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.set_position([0.05, 0.05, 0.55, 0.85])

    wedges, _, autotexts = ax.pie(
        counts.values,
        labels=None,
        colors=colors,
        autopct=lambda pct: f"{pct:.1f}%" if pct >= 5.0 else "",
        startangle=90,
        wedgeprops=dict(edgecolor=_BG, linewidth=2),
        pctdistance=0.75,
    )
    for t in autotexts:
        t.set_color(_TEXT)
        t.set_fontsize(10)
        t.set_fontweight("bold")

    legend_labels = [
        f"{int(r)} ★  —  {int(c)}  ({c / total * 100:.1f}%)"
        for r, c in zip(counts.index, counts.values)
    ]
    ax.legend(
        wedges, legend_labels,
        loc="center left",
        bbox_to_anchor=(1.08, 0.5),
        frameon=True,
        framealpha=0.15,
        edgecolor=_GRID,
        labelcolor=_TEXT,
        fontsize=10,
        title="Rating",
        title_fontsize=11,
    )
    ax.set_title(f"Customer Satisfaction  —  {_range_suffix()}", fontsize=14, pad=12)
    _save(fig, out)


def _chart_throughput(out):
    df = _read("Customer Throughput")
    if df is None or df.empty or "throughput" not in df.columns or "game_hour" not in df.columns:
        return _placeholder(out, _CSV_FILES["Customer Throughput"])

    # Average customers in shop per half-hour bucket
    series = df.groupby("game_hour")["throughput"].mean()

    # Force the X-axis to cover the entire shift (hour 0 -> 5.5, 12 buckets).
    # Missing buckets get 0 so the chart always shows the full timeline,
    # even if the player only played part of the shift.
    full_index = [i * 0.5 for i in range(12)]   # 0, 0.5, 1, ..., 5.5
    series = series.reindex(full_index, fill_value=0).sort_index()

    # Label each bucket as its game-hour value (e.g. "0", "0.5", "1", ...).
    # Whole hours render without the decimal so the axis reads cleanly.
    def _fmt_hour(h):
        return str(int(h)) if h == int(h) else str(h)

    labels = [_fmt_hour(h) for h in series.index]
    values = series.values

    fig, ax = plt.subplots(figsize=(8, 5))
    ax.bar(labels, values,
           color=_ACCENT, edgecolor=_BG, linewidth=0.8)
    ax.set_title(f"Customer Throughput  —  {_range_suffix()}",
                 fontsize=14, pad=12)
    ax.set_xlabel("Game Hour")
    ax.set_ylabel("Avg. Customers in Shop")
    ax.grid(True, axis="y")
    fig.tight_layout()
    _save(fig, out)


def _chart_accuracy(out):
    df = _read("Assembly Accuracy")
    if df is None or df.empty or "accuracy_pct" not in df.columns:
        return _placeholder(out, _CSV_FILES["Assembly Accuracy"])

    mean = df["accuracy_pct"].mean()
    fig, ax = plt.subplots(figsize=(8, 5))
    ax.hist(df["accuracy_pct"], bins=20, color=_ACCENT,
            edgecolor=_BG, linewidth=0.8, range=(0, 100))
    ax.axvline(mean, color="#17c3b2", linewidth=2,
               linestyle="--", label=f"Mean  {mean:.1f}%")
    ax.set_title(f"Assembly Accuracy  —  {_range_suffix()}", fontsize=14, pad=12)
    ax.set_xlabel("Accuracy (%)")
    ax.set_ylabel("Frequency")
    ax.legend()
    ax.grid(True, axis="y")
    fig.tight_layout()
    _save(fig, out)


def _chart_ingredients(out):
    df = _read("Ingredients Sold")
    if df is None or df.empty or "item_id" not in df.columns:
        return _placeholder(out, _CSV_FILES["Ingredients Sold"])

    grp = df.groupby("item_id")
    summary = pd.DataFrame({
        "Total":   grp["quantity"].sum(),
        "Mean":    grp["quantity"].mean().round(2),
        "StdDev":  grp["quantity"].std().round(2),
        "Revenue": grp["revenue"].sum() if "revenue" in df.columns else 0,
    }).sort_values("Total", ascending=False).reset_index()

    fig_h = max(3.5, len(summary) * 0.45 + 1.5)
    fig, ax = plt.subplots(figsize=(8, fig_h))
    ax.axis("off")

    col_labels = ["Ingredient", "Total Units", "Mean / Customer",
                  "Std Dev", "Total Revenue"]
    rows = []
    for _, r in summary.iterrows():
        std_s = f"{r['StdDev']:.2f}" if pd.notna(r["StdDev"]) else "—"
        rev   = int(r["Revenue"]) if pd.notna(r["Revenue"]) else 0
        rows.append([r["item_id"], int(r["Total"]), f'{r["Mean"]:.2f}', std_s, f"${rev:,}"])

    tbl = ax.table(cellText=rows, colLabels=col_labels,
                   cellLoc="center", loc="center")
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(11)
    tbl.scale(1, 1.6)

    for j in range(len(col_labels)):
        tbl[0, j].set_facecolor(_ACCENT)
        tbl[0, j].set_text_props(color=_TEXT, fontweight="bold")
        tbl[0, j].set_edgecolor(_GRID)

    for i in range(1, len(rows) + 1):
        fc = "#1e1e3a" if i % 2 == 0 else _PANEL
        for j in range(len(col_labels)):
            tbl[i, j].set_facecolor(fc)
            tbl[i, j].set_text_props(color=_TEXT)
            tbl[i, j].set_edgecolor(_GRID)

    ax.set_title(f"Ingredients Sold  —  {_range_suffix()}",
                 fontsize=14, pad=16, color=_TEXT)
    fig.tight_layout()
    _save(fig, out)


_CHART_FUNCS = {
    "Net Revenue":           _chart_revenue,
    "Customer Satisfaction": _chart_satisfaction,
    "Customer Throughput":   _chart_throughput,
    "Assembly Accuracy":     _chart_accuracy,
    "Ingredients Sold":      _chart_ingredients,
}


def _generate_all_charts():
    """Re-generate every chart PNG from the current CSV data."""
    for label, func in _CHART_FUNCS.items():
        func(_IMG_FILES[label])


# ---------------------------------------------------------------------------
# Tkinter window
# ---------------------------------------------------------------------------

class StatViewer(tk.Tk):
    """
    Analytics dashboard window.

    Public surface
    --------------
    StatViewer.run()   — the only method callers outside this module need.

    Everything else is a private implementation detail (_single) or a
    Tk-internal reference that must never be overwritten (__double).
    """

    @classmethod
    def run(cls):
        """
        Generate charts from CSVs, open the analytics window, and BLOCK
        until the user closes it. Safe to call from anywhere in your game.

        Usage:
            from core.stat_viewer import StatViewer
            StatViewer.run()    # blocks until user closes the window
        """
        _generate_all_charts()
        cls().mainloop()

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    def __init__(self):
        super().__init__()
        self.title("Playtesting Analytics")
        self.resizable(False, False)
        self.configure(bg=_BG)
        self.__photo     = None   # Tk image ref — must stay alive or image vanishes
        self.__stat_var  = None
        self.__range_var = None
        self.__img_label = None
        self._build_ui()
        self._select(_STAT_LABELS[0])

    # ------------------------------------------------------------------
    # Private UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        # Header
        hdr = tk.Frame(self, bg=_BG)
        hdr.pack(fill="x", padx=20, pady=(14, 2))
        tk.Label(hdr, text="Playtesting Analytics",
                 bg=_BG, fg=_ACCENT,
                 font=("Courier New", 15, "bold")).pack(side="left")

        # Controls row
        ctrl = tk.Frame(self, bg=_BG)
        ctrl.pack(fill="x", padx=20, pady=(4, 8))

        tk.Label(ctrl, text="View:", bg=_BG, fg=_TEXT,
                 font=("Courier New", 11)).pack(side="left", padx=(0, 6))

        self.__stat_var = tk.StringVar(value=_STAT_LABELS[0])
        stat_combo = ttk.Combobox(ctrl, textvariable=self.__stat_var,
                                  values=_STAT_LABELS, state="readonly",
                                  width=28, font=("Courier New", 11))
        stat_combo.pack(side="left")
        stat_combo.bind("<<ComboboxSelected>>",
                        lambda e: self._select(self.__stat_var.get()))

        tk.Label(ctrl, text="Range:", bg=_BG, fg=_TEXT,
                 font=("Courier New", 11)).pack(side="left", padx=(18, 6))

        self.__range_var = tk.StringVar(value=_window["mode"])
        range_combo = ttk.Combobox(ctrl, textvariable=self.__range_var,
                                   values=_RANGE_OPTIONS, state="readonly",
                                   width=12, font=("Courier New", 11))
        range_combo.pack(side="left")
        range_combo.bind("<<ComboboxSelected>>", self._on_range_change)

        self._apply_combobox_style()

        # Image canvas
        self.__img_label = tk.Label(self, bg=_PANEL,
                                    width=_IMG_SIZE[0], height=_IMG_SIZE[1])
        self.__img_label.pack(padx=20, pady=(0, 10))

        # Footer
        tk.Label(self, text="Close this window to continue",
                 bg=_BG, fg="#555577",
                 font=("Courier New", 9)).pack(pady=(0, 10))

    def _apply_combobox_style(self):
        """Dark-theme combobox styling — explicit contrast so text reads before clicking."""
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox",
                        fieldbackground="#0f3460",
                        background="#0f3460",
                        foreground=_TEXT,
                        selectbackground=_ACCENT,
                        selectforeground=_TEXT,
                        insertcolor=_TEXT,
                        arrowcolor=_ACCENT,
                        bordercolor=_GRID,
                        lightcolor=_GRID,
                        darkcolor=_GRID)
        style.map("TCombobox",
                  fieldbackground=[("readonly", "#0f3460")],
                  foreground=[("readonly", _TEXT)],
                  background=[("readonly", "#0f3460"),
                              ("active",   _ACCENT)],
                  arrowcolor=[("readonly", _ACCENT),
                              ("active",   _TEXT)])

    # ------------------------------------------------------------------
    # Private event handlers
    # ------------------------------------------------------------------

    def _on_range_change(self, _event):
        _window["mode"] = self.__range_var.get()
        _generate_all_charts()
        self._select(self.__stat_var.get())

    def _select(self, label):
        path = _IMG_FILES[label]
        if not os.path.exists(path):
            self.__img_label.config(
                image="", text=f"Image not found:\n{path}",
                fg=_ACCENT, font=("Courier New", 12))
            return
        img = Image.open(path).resize(_IMG_SIZE, Image.LANCZOS)
        self.__photo = ImageTk.PhotoImage(img)
        self.__img_label.config(image=self.__photo, text="")