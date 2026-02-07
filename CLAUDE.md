# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Python-based battle simulation tool** for the MMORPG "HolyLandOnline" (聖域Online). It simulates combat between players and monsters using game data exported as JSON, and trains AI combat behavior using **PPO (Proximal Policy Optimization)** reinforcement learning. The GUI is built with **tkinter**.

The tool is designed to mirror the game's combat formulas so balance tuning and AI training can happen outside the Unity game client.

## Running the Application

```bash
# Activate venv
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the simulator (this is the entry point)
python simulator_gui.py
```

Python 3.13 is used. The project uses a Visual Studio Python project (.pyproj/.sln) but can be run directly.

## CI/CD

On push to `master`, a GitHub Action (`SIMULATION_GITACTION.yml`) builds a standalone EXE via PyInstaller and pushes it to the Unity repo (`HLO_new`) at `Assets/Tools/SimulationTool.exe`.

## Architecture

### Data Flow
`JSON files (data/) → GameData singleton → Battle simulation → AI training → PPO model (.pth)`

### Key Modules

- **`simulator_gui.py`** — Entry point. Tkinter GUI (`BattleSimulatorGUI`) for configuring player/enemy, launching battles, and viewing results. Contains all UI widget definitions including HP/MP bars, buff/debuff bars, character overview panels.

- **`game_models.py`** — All game data structures as `@dataclass` classes (skills, monsters, weapons, armor, items, etc.) and the `GameData` singleton that loads everything from `data/*.json` into dictionaries keyed by ID.

- **`battle_simulator.py`** — Core battle engine. Contains:
  - `BattleCharacter`: Represents a combatant with stats split into three layers: `basal` (base), `equip` (equipment), `effect` (buff/debuff). Stats are recalculated by summing all three layers via `_recalculate_stats()`.
  - `BattleSimulator`: Manages the real-time battle loop using `tkinter.after()` timers. `battle_tick()` handles passive timers (cooldowns, buff durations, HP/MP regen). `attack_loop()` drives AI decision-making each turn.

- **`AICombatAction.py`** — PPO reinforcement learning agent (`ai_action` class with `ActorCritic` neural network). Handles state observation, action masking (prevents illegal actions like using skills on cooldown), action selection, reward calculation, and model training. Models saved per job/role in `ppo_models/ppo_{role_id}.pth`.

- **`skill_processor.py`** — `SkillProcessor` (all static methods) executes skill effects by dispatching on `SkillComponentID` (Damage, ContinuanceBuff, CrowdControl, Debuff, PassiveBuff, AdditiveBuff, Utility, Health, EnhanceSkill, UpgradeSkill, etc.). Also handles skill conditions (OR/AND) and dependency chains between skill components.

- **`status_operation.py`** — `StatusValues` dataclass (composed via multiple inheritance from `CharacterStatus_Core`, `CharacterStatus_Secret`, `CharacterStatus_Debuff`, `CharacterStatus_Element`, `MonsterStatus_Core`). `CharacterStatusCalculator` computes final stats from base attributes + race formulas + job bonuses + equipment.

- **`character_status.py`** — Defines the individual status dataclass fragments that compose `StatusValues`.

- **`commonfunction.py`** — Utility class: text lookup from `GameTextDataDic`, resource path resolution (supports PyInstaller `_MEIPASS`), battle log formatting with HTML-like markup (`<color>`, `<size>` tags), image loading, `clamp()`.

- **`commontool.py`** — C#-style `Event` class (supports `+=`/`-=` for subscribe/unsubscribe pattern).

- **`user_config_controller.py` / `user_config_model.py`** — MVC pattern for persisting user configuration to `%APPDATA%/MySimulator/user_config.json`.

### Combat System Design

The combat system uses **real-time tick-based simulation** (0.1s intervals for timers, variable intervals for attack loops). Each combatant has independent attack timers. The damage pipeline is: **Hit check → Block check → Critical check → Damage calculation → Bonus damage → Lifesteal**.

Stats have three layers: `basal` (from level/race/job), `equip` (from gear), `effect` (from buffs/debuffs). When any effect changes, `_recalculate_stats()` re-sums all three layers.

### Data Directory (`data/`)

All game data is in JSON format, exported from the game's data tables. Text content is separated into `*Text.json` files and referenced by `TextID`. Use `CommonFunction.get_text(text_id)` to look up display text.

## Conventions

- Code comments and UI text are in **Traditional Chinese (繁體中文)**.
- The codebase follows patterns from Unity/C# (e.g., the `Event` class, PascalCase for data model fields, `match/case` for dispatching).
- Battle log messages use Unity-style rich text markup (`<color=#hex>`, `<size=N>`).
- Skill effects are data-driven: the `SkillComponentID` field determines which processing branch runs in `SkillProcessor._execute_component()`.
