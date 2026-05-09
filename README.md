# Midnight Griddle

## Project Description

- **Project by:** [Your Name]
- **Game Genre:** Management Simulation, Time Pressure

Midnight Griddle is a station-based management simulation where the player runs a burger stand during the 11 PM – 6 AM graveyard shift. Each "night" is a 6-minute real-time round in which the player must take customer orders, cook patties on a 12-slot grill, assemble burgers via drag-and-drop, and submit them before the customer's patience runs out — all while managing finite ingredient stock and a cash balance that has to cover restocking. Difficulty scales both within a shift (a calm opening into a rush hour) and across nights (each successive night starts harder than the last). A built-in Tkinter analytics dashboard tracks revenue, customer satisfaction, throughput, assembly accuracy, and ingredient usage across sessions.

---

## Installation

To clone this project:

```sh
git clone https://github.com/<username>/midnight-griddle.git
cd midnight-griddle
```

To create and activate a Python environment for this project:

**Windows:**

```bat
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

**Mac:**

```sh
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

The `requirements.txt` contains:

```
pygame-ce>=2.5.0
pandas>=2.0.0
matplotlib>=3.7.0
pillow>=10.0.0
```

> **Note:** this project uses `pygame-ce` (Community Edition), not the original `pygame`. They share the same `import pygame` API, but installing both in the same environment causes conflicts — pick one. If you already have regular `pygame` installed, run `pip uninstall pygame` first.

`tkinter` is part of Python's standard library on Windows and most Linux distributions. On macOS, if `import tkinter` fails, install Python from <https://www.python.org/downloads/> (the official installer bundles Tk) rather than relying on the system Python.

---

## Running Guide

After activating the Python environment, run the game from the project root:

**Windows:**

```bat
python main.py
```

**Mac:**

```sh
python3 main.py
```

The game opens in fullscreen at 1920 × 1080. Press `ESC` or `P` at any time to pause.

---

## Tutorial / Usage

**Main menu**

When the game starts you land on the main menu. Four options:

- **CONTINUE SHIFT** — resume from the last saved night.
- **NEW SHIFT** — wipe the save file and start fresh from Night 1.
- **VIEW STATS** — open the analytics dashboard (blocks the game until closed).
- **QUIT** — exit.

**The four stations**

Use the navigation buttons at the bottom of the screen to switch between stations:

1. **Order Station** — incoming customers wait here. Click **ACCEPT ORDER** to take their order; the customer moves to the waiting queue and their ticket appears in the order panel on the right.
2. **Grill Station** — drag a raw patty from the meat dispenser onto any of the 12 grill slots. Patties cook through three states (raw → cooked → burnt) over time. Cooked patties go in the tray to be carried to the assembly station.
3. **Assemble Station** — drag ingredients from the right-side dispensers onto the plate in the correct stacking order (bottom bun on the bottom, top bun on top). The current order is mirrored on the left so you don't have to switch tabs. Click **SUBMIT ORDER** when done.
4. **Restock Station** — buy more of any ingredient using the cash you've earned. Each ingredient has its own buy price.

**Drag vs. click**

The same item can be either clicked or dragged depending on motion. A short press in place is a click; any motion past a small threshold becomes a drag.

**Pause**

Press `ESC` / `P`, or click the pause button at the top center of the screen. From the pause menu you can resume, view stats, or return to the main menu.

**Stats dashboard**

Inside the **VIEW STATS** window:

- The **View** dropdown switches between the five charts (Net Revenue, Customer Satisfaction, Customer Throughput, Assembly Accuracy, Ingredients Sold).
- The **Range** dropdown toggles between the last 100 events and lifetime data.
- Close the window to return to the game.

**Win / lose conditions**

- **Shift Complete** — survive until 6 AM (6 in-game hours / 6 real minutes). Night counter advances by one.
- **Shift Failed** — average rating drops below 2 stars. Save data is wiped and you have to start a new shift.

---

## Game Features

- **Four-station layout** — Order, Grill, Assemble, and Restock, each with its own UI and input rules.
- **Drag-and-drop assembly** — physics-lite ingredient stacking with snapback for invalid drops, hover feedback on every clickable button, and a configurable click-vs-drag motion threshold.
- **Cooking system** — patties on the grill transition through raw → cooked → burnt states with a darkening tint and a looping sizzle SFX tied to each patty's lifecycle. Submitting a raw or burnt patty hurts your accuracy score.
- **Two-axis difficulty curve** — a permanent per-night baseline (`+12%` per night) combined with an exponential time ramp inside each shift, both bounded by a global cap. Difficulty drives spawn frequency, customer patience, and order length.
- **Two-phase customer queue** — separate patience timers for "waiting to order" and "waiting for food," each contributing independently to the final star rating.
- **Composite rating formula** — `accuracy × (0.6 + 0.2 × ordering_ratio + 0.2 × waiting_ratio)`, gated by accuracy so a wrong burger never earns points for being delivered fast.
- **Dual accuracy scoring** — index-based slot match (full credit for correct layering) plus an unordered count match (capped at 80%); the higher score wins.
- **Persistent save / load** — money, night, rating history, and stock are written to `gameplay.csv` after every successful submit.
- **Analytics dashboard** — Tkinter + matplotlib + pandas window with five views (line chart, pie chart, bar chart, histogram, data table) and a Last-100 / All range toggle.
- **HUD bar** — always-visible top bar showing night number, in-game hour, money, and average star rating.
- **Audio system** — singleton SFX manager with bell, pickup pop, place pop, submit, and looped grill sizzle.
- **Full menu state machine** — main menu, pause, game-over, and shift-complete screens, all built from one reusable `MenuScreen` widget.

---

## Known Bugs

- The looping sizzle channel can occasionally be stolen by other SFX during heavy bursts, leaving a cooking patty silent until the next state change re-triggers `_ensure_sizzle()`.
- If the player drags an item exactly when it reaches the end of its tween animation, the snapback target can be off by one frame.
- Music playlist code in `audiomanager.py` is currently commented out — no background music plays.

---

## Unfinished Works

- **Background music** — the playlist system in `AudioManager` (`play_music`, `play_playlist`, `next_music`, auto-advance) is implemented but commented out. Tracks need to be added to the `MUSIC` registry to enable it.
- **`_accuracy_by_sequence`** — a weighted Longest Common Subsequence scorer was prototyped in `stattracker.py` but is not wired into `log_accuracy`. Left in the file for future tuning experiments.
- **Tutorial overlay** — there is no in-game first-run tutorial; players currently learn the controls from this README.

---


## External Sources

- **Game design inspiration** — *Papa's Burgeria* by Flipline Studios. The core loop (take order → grill patties → assemble in layers → serve before patience runs out) and the drag-and-drop ingredient interface are inspired by it. Midnight Griddle differs in three intentional ways: finite ingredient stock with a cash-gated restock system, a hard 6-minute shift timer instead of an open-ended day, and an escalating difficulty curve across nights. All sprite art and code in this project are original.
- **Art / sprites** — None (all art is original or placeholder).
- **Fonts** — System `serif` (no external font files).
- **Sound / music** — All clips sourced from [Pixabay](https://pixabay.com/sound-effects/) under the Pixabay Content License:
  - `bell` — [Service receptionist bell (418758)](https://pixabay.com/sound-effects/servicereceptionist-bell-418758/)
  - `place_pop` — [Clean minimal pop (467466)](https://pixabay.com/sound-effects/clean-minimal-pop-467466/)
  - `pick_pop` — [Pop (402323)](https://pixabay.com/sound-effects/pop-402323/)
  - `ghost_submit` — [Creepy ghost sound (487677)](https://pixabay.com/sound-effects/creepy-ghost-sound-487677/)
  - `sizzle_loop` — [Frying pan hot sizzle loop (200913)](https://pixabay.com/sound-effects/frying-pan-hot-sizzle-loop-2-200913/)
- **Code snippets / tutorials** — Some base code was adapted from this YouTube tutorial: <https://www.youtube.com/watch?v=AY9MnQ4x3zk&t=306s>
- **Libraries**
  - Third-party: `pygame-ce`, `pandas`, `matplotlib`, `pillow`
  - Standard library: `tkinter`, `os`, `csv`, `copy`, `math`, `random`, `collections`

---

*Built with Python 3, Pygame-CE, Tkinter, Matplotlib, Pandas, and Pillow.*