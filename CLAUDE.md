# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the Game

```bash
# Run directly (no install needed)
python main.py

# Or install as a package and run via entry point
pip install -e .
mech-quartermaster
```

There are no tests or a linter configured. This is a small vibe-coded project.

## Building the Windows Executable

PyInstaller is used to produce a single-file `.exe`:

```bash
pyinstaller --onefile --name mech-quartermaster main.py
```

The resulting binary lands in `dist/`. The `build/` directory contains PyInstaller's working files.

## Architecture

The game is a BattleTech-inspired terminal management game (BattleMech mercenary company). All game logic lives under `src/mech_quartermaster/`.

**Data layer (`data.py`)** — pure static constants, no logic:
- `CHASSIS_DATA` — all mech chassis with per-location armor/structure/equipment stats
- `PARTS_CATALOG` — buyable parts with cost and repair time
- `MISSION_TYPES` — mission definitions with damage scales, reward ranges, and class bonuses
- `MECH_PRICES`, overhead rate constants, `FINAL_MISSION` sentinel

**Domain model (`mech.py`)**:
- `Component` — one of the 8 BattleTech locations (Head, CT, LT, RT, LA, RA, LL, RL). Tracks current/max armor and structure, equipment, and destroyed equipment. `apply_damage()` runs the armor→structure→critical-hit pipeline.
- `Mech` — wraps a chassis definition from `CHASSIS_DATA`, owns a `dict[str, Component]`. Key properties: `is_combat_ready`, `working_weapons`, `overall_status`.
- `Inventory` — tracks C-Bills, parts stock, and pending supply orders (arrive on future day).

**Mission simulation (`missions.py`)** — `simulate_mission()` takes a mech list and a mission type dict, rolls success chance, calls `Component.apply_damage()` on each deployed mech, returns a structured report dict (success bool, events log, C-Bill reward, casualties).

**Campaign system (`campaigns/`)**:
- `base.py` defines `Campaign` and `NarrativeEvent` dataclasses. A `Campaign` holds starting conditions, a `victory_condition` callable `fn(GameState) -> bool`, optional `final_mission`, and a list of `NarrativeEvent`s.
- `iron_lance.py` implements the default campaign (survive 12 contracts). Add new campaigns here and register them in `campaigns/__init__.py`'s `ALL_CAMPAIGNS` list.

**Game loop (`game.py`)**:
- `GameState` holds all mutable runtime state: mech roster, inventory, day counter, campaign reference, `missions_run`, difficulty settings.
- `DIFFICULTIES` dict modifies overhead multiplier, damage multiplier, and tech hours bonus.
- `BATTLE_ORDERS` list (3 options) modifies damage/salvage/reward/success multipliers per deployment.
- `MAX_MECHS = 8`, `MAX_DEPLOYED = 4` are the roster caps.
- Screen functions (`screen_*`) handle individual UI flows and call back into the main loop.
- Entry point is `run()` called from `main.py`.

**UI helpers (`ui.py`)** — `C` class for ANSI color codes (auto-disabled when not a TTY), `header()`, `section()`, `hr()`, `menu()`, `prompt()`, `pause()`, `clear()`, `print_mech_detail()`. `WIDTH = 72` is the display column width.

## Key Conventions

- All monetary values are in C-Bills (integers).
- Damage flows: armor absorbed first, overflow hits structure, structure hits trigger 35% per-item critical roll on all equipment in that location.
- A mech is a total loss (`mech.total_loss = True`) when its Center Torso structure reaches 0 — it is removed from the roster permanently.
- Parts are consumed one-per-repair-action; the repair system in `game.py` tracks available tech hours per day.
- New chassis go in `CHASSIS_DATA` (data.py) and `MECH_PRICES` (data.py). New campaigns go in `campaigns/` and must be added to `ALL_CAMPAIGNS` in `campaigns/__init__.py`.
