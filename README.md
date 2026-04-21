# Burger Game

## Project Structure

```
burger_game/
│
├── main.py                   # Entry point — run this to start the game
│
├── core/                     # Pure data & logic, no rendering
│   ├── settings.py           # Constants (screen size, FPS, layers, GamePath)
│   ├── itemdata.py           # Item database + image loader (ItemData)
│   ├── gamedata.py           # Mutable game state: money, stock, ratings (GameData)
│   └── stattracker.py        # CSV logging, GameHour clock, rating formula
│
├── ui/                       # Rendering, sprites, and UI widgets
│   ├── theme.py              # Colors, fonts, layout constants, button builder
│   ├── interactive.py        # Sprite base classes (InteractiveObject, StaticUI, UIButton,
│   │                         #   GrillableItem, IngredientItem, BasePlate)
│   ├── group.py              # Sprite groups (BaseGroup, StackGroup, GrillGroup,
│   │                         #   PlateGroup, DispenserGroup, TrayGroup, TrashGroup...)
│   ├── factory.py            # ItemFactory — creates sprites from ItemData
│   ├── hud.py                # HUDGroup — top bar (clock, money, rating)
│   └── orderui.py            # OrderUI — right-side order panel
│
├── stations/                 # Game screens / gameplay logic
│   ├── customermanager.py    # Customer lifecycle: spawning, patience, queues
│   ├── station.py            # Station base + OrderStation, GrillStation, AssembleStation
│   ├── restock_station.py    # RestockStation — shop screen
│   └── stationmanager.py     # StationManager — owns all stations, routing, shared state
│
├── assets/                   # Art assets (populate before running)
│   ├── grillable/            # meat.png, meat_raw.png, meat_medium.png, meat_burn.png
│   ├── ingredients/          # down_bun.png, top_bun.png, cheese.png
│   ├── station/              # test.png, test2.jpg (station backgrounds)
│   ├── ui/                   # 20.png (nav button icons)
│   └── objects/              # sauce_bottle.png, base_plate.png
│
└── data/
    └── gamedata/             # Auto-generated save files & stat CSVs
        ├── gameplay.csv
        ├── revenue_log.csv
        ├── satisfaction_log.csv
        ├── throughput_log.csv
        ├── accuracy_log.csv
        └── ingredients_log.csv
```

## How to Run

```bash
cd burger_game
python main.py
```

## Package Dependency Order

```
core  ←  ui  ←  stations  ←  main
```

`core` has no internal dependencies.
`ui` imports from `core` only.
`stations` imports from `core` and `ui`.
`main` imports from `stations` (and transitively everything else).
