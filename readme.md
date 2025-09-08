# PyHMI Designer (GT-Designer3-style, PC-only) — Python + PyQt6

> A full-featured **HMI designer** and **runtime simulator** for PC, inspired by Mitsubishi **GT Designer3 (GOT2000)**.  
> Build multi-screen HMIs with buttons, lamps, trends, alarms, recipes, background tasks, and scripts — **design and run entirely on a PC** (no hardware deployment).

---

## ✨ Highlights

- **Design studio:** WYSIWYG canvas, grid/snap, align/distribute, multi-select, z-order, undo/redo.
- **Rich widget set:** Buttons/switches, lamps/indicators, numeric & text I/O, sliders, level bars, trends/charts, images, alarm/recipe displays.
- **Project management:** Multi-screen projects (base/window screens), project tree, templates, assets.
- **Runtime simulator (PC-only):** One-click Run; full interaction, screen navigation, tag updates, alarm flow.
- **Data layer:** Central **Tag Manager/Data Manager** for booleans, integers, floats, strings.
- **Alarms:** Conditions, severity, acknowledge, active/history lists, banner.
- **Logging & trends:** Periodic/triggered logging to CSV/SQLite; historical + live trends.
- **Recipes:** Define sets of tag values; load/apply at runtime.
- **Background tasks:** Timed/trigger-based actions (set/copy tag, change screen, hardcopy, run snippet).
- **Scripting:** Python scripts at **project**, **screen**, and **object** levels with a safe helper API.
- **(Simulated) remote view:** Optional mirror viewer window bound to the same data model.

> **Scope:** This app **does not** target physical HMI hardware. It replicates GT-Designer3-like features for **PC design + simulation only**.

---

## 🧱 Tech Stack

- **Language:** Python 3.10+
- **GUI:** PyQt6 (Qt Graphics View for canvas, QDockWidget panels)
- **Charts (optional):** PyQtGraph / matplotlib
- **Storage:** JSON (project), CSV/SQLite (logs), PNG (screen hardcopy)
- **Packaging (optional):** PyInstaller

---

## 📦 Installation

```bash
# 1) Create venv (recommended)
python -m venv .venv
# Windows
.\.venv\Scriptsctivate
# Linux/macOS
source .venv/bin/activate

# 2) Install deps + local package (exposes `hmi-sim` CLI)
pip install -r requirements.txt

# 3) Run (Designer)
python main.py

# Simulator (independent executable)
# From designer use Project → Run (F5), or run directly:
python runtime_simulator/main.py <path-to-project.hmi>

# Or via module
python -m runtime_simulator --project <path-to-project.hmi>

# Or after editable install (entry point from requirements.txt)
hmi-sim <path-to-project.hmi>
```

## Project Structure (Current)

```
HMI-2.00/
├─ main.py
├─ app_settings.json
├─ requirements.txt
├─ modern_gui v12.hmi
├─ readme.md
├─ components/
│  ├─ array_tree_handler.py
│  ├─ comment_filter_model.py
│  ├─ comment_table_model.py
│  ├─ comment_table_widget.py
│  ├─ docks.py
│  ├─ property_editor.py
│  ├─ ribbon.py
│  ├─ selection_overlay.py
│  ├─ tag_editor_widget.py
│  ├─ toolbar.py
│  ├─ tree_widget.py
│  ├─ welcome_widget.py
│  ├─ button/
│  │  ├─ button_properties_dialog.py
│  │  └─  conditional_style.py
│  ├─ screen/
│  │  ├─ design_canvas.py
│  │  ├─ graphics_items.py
│  │  ├─ screen_manager_widget.py
│  │  ├─ screen_tree.py
│  │  └─  screen_widget.py
├─ dialogs/
│  ├─ actions/
│  │  ├─ bit_action_dialog.py
│  │  ├─ constants.py
│  │  ├─ range_helpers.py
│  │  ├─ select_action_type_dialog.py
│  │  ├─ trigger_utils.py
│  │  └─  word_action_dialog.py
│  ├─ add_tag_dialog.py
│  ├─ base_dialog.py
│  ├─ comment_table_dialog.py
│  ├─ info_dialog.py
│  ├─ project_info_dialog.py
│  ├─ question_dialog.py
│  ├─ screen_properties_dialog.py
│  ├─ tag_browser_dialog.py
│  ├─ tag_database_dialog.py
│  └─  widgets.py
├─ lib/
│  └─  icon/        # SVG icon assets
├─ main_window/
│  ├─ actions.py
│  ├─ clipboard.py
│  ├─ events.py
│  ├─ handlers.py
│  ├─ project_actions.py
│  ├─ tabs.py
│  ├─ ui_setup.py
│  └─  window.py
├─ scripts/
├─ services/
│  ├─ clipboard_service.py
│  ├─ commands.py
│  ├─ command_history_service.py
│  ├─ comment_data_service.py
│  ├─ csv_service.py
│  ├─ excel_service.py
│  ├─ project_service.py
│  ├─ screen_data_service.py
│  ├─ settings_service.py
│  ├─ tag_data_service.py
│  └─  tag_service.py
├─ theme/
│  ├─ dark_theme/
│  ├─ default_theme/
│  └─  light_theme/
├─ tools/
│  └─ button/
└─ utils/
   ├─ constants.py
   └─  icon_manager.py
```

> If PyQt6 wheels fail on your OS/Python combo, try a matching Python version (3.10–3.12) or use PySide6 as fallback (requires minor code tweaks).

---

## 🗂 Project Structure

```
HMI-2.00/
├─ run.py
├─ README.md
├─ requirements.txt
├─ designer/                  # Design-time app
│  ├─ main_window.py
│  ├─ menubar.py
│  ├─ status_bar.py
│  ├─ project_manager.py      # New/Open/Save, schema
│  ├─ project_tree.py         # Screen list, resources
│  ├─ toolbox_panel.py        # Palette of widgets
│  ├─ properties_panel.py     # Context properties
│  ├─ screen_editor.py        # Canvas (QGraphicsView)
│  ├─ selection/              # Handles, multi-select, align
│  ├─ widgets/                # HMI widgets (QGraphicsObject)
│  │  ├─ base.py
│  │  ├─ button.py
│  │  ├─ lamp.py
│  │  ├─ numeric_display.py
│  │  ├─ text_display.py
│  │  ├─ slider.py
│  │  ├─ level_bar.py
│  │  ├─ trend.py             # (proxy to PyQtGraph)
│  │  ├─ alarm_banner.py
│  │  ├─ alarm_table.py
│  │  ├─ recipe_view.py
│  │  └─ image.py
│  └─ tag_manager.py          # Tag schema editor
├─ runtime_simulator/         # Run-time engine (PC)
│  ├─ simulator.py            # Simulation window
│  ├─ screens.py              # Runtime screen loader
│  ├─ data_manager.py         # Central tags w/ signals
│  ├─ alarm_manager.py
│  ├─ logging_manager.py
│  ├─ recipe_manager.py
│  ├─ background_tasks.py
│  ├─ script_engine.py        # Project/Screen/Object
│  └─ remote_view.py          # Mirror window (optional)
├─ data/
│  ├─ icons/
│  ├─ templates/
│  └─ demo_project/
└─ docs/
   └─ user-guide.md
```

---

## 📁 Project File Format (JSON)

```json
{
  "version": "0.1",
  "settings": {
    "resolution": {"w": 1024, "h": 600},
    "scan_ms": 100
  },
  "tags": {
    "MotorRun": {"type": "bool", "init": false},
    "Speed": {"type": "int", "init": 0, "min": 0, "max": 100},
    "Temp": {"type": "float", "init": 25.0}
  },
  "screens": [
    {
      "name": "Main",
      "type": "base",
      "widgets": [
        {"type": "button", "id": "btnStart", "x": 40, "y": 40, "w": 160, "h": 60,
         "props": {"label": "START", "action": {"kind": "set", "tag": "MotorRun", "value": true}}},
        {"type": "lamp", "id": "lampRun", "x": 220, "y": 50, "w": 40, "h": 40,
         "props": {"tag": "MotorRun", "on_color": "#2ecc71", "off_color": "#c0392b"}}
      ],
      "scripts": {"on_open": "write('Speed', 0)"}
    }
  ],
  "alarms": [
    {"id": "ALM_TEMP_HIGH", "expr": "read('Temp') > 80", "message": "High Temperature", "severity": "high", "ack": true}
  ],
  "logging": {
    "cyclic": [{"tags": ["Temp","Speed"], "interval_ms": 1000}],
    "triggered": [{"tag": "MotorRun", "on_change": true}]
  },
  "recipes": {
    "MachineSetup": {
      "fields": ["Speed","Temp"],
      "records": [{"name":"Slow","Speed":20,"Temp":30.0},{"name":"Fast","Speed":80,"Temp":35.0}]
    }
  },
  "background": [
    {"type": "interval", "ms": 5000, "action": {"kind": "hardcopy", "screen": "Main"}},
    {"type": "trigger", "expr": "read('Speed') > 90", "action": {"kind": "change_screen", "screen":"Alarm"}}
  ],
  "scripts": {
    "project_tick": "if read('MotorRun'): write('Speed', min(read('Speed')+1, 100))"
  }
}
```

---

## 🧩 Core Concepts

### Screens
- **Base screens:** full pages; one visible at a time.
- **Window screens:** pop-up/dialog overlay with its own size & transparency.

### Tags (Data Model)
- Types: `bool`, `int`, `float`, `str` (+ optional min/max).
- **DataManager** emits `tagChanged(name, value)`; widgets subscribe.
- Tag creation via Tag Manager or on-the-fly when binding.

### Widgets (Design-time vs Runtime)
- Design-time: draggable/resizable `QGraphicsObject` with property metadata.
- Runtime: same object type in **read-only layout** that reacts to data & events.

### Scripting (Python)
Helper API exposed to scripts:
```python
read(tag: str) -> Any
write(tag: str, value: Any) -> None
toggle(tag: str) -> None
change_screen(name: str) -> None
ack(alarm_id: str) -> None
log(msg: str) -> None
delay_ms(ms: int) -> None   # cooperative delay (non-blocking)
```
Script scopes:
- **Project:** `on_start`, `on_stop`, and `project_tick()` (called every scan).
- **Screen:** `on_open()`, `on_close()`, optional `tick()` while active.
- **Object:** event hooks (e.g., button `on_click()`).

> ⚠️ Avoid blocking calls/sleep in scripts. Use `delay_ms` or background tasks.

---

## 🧪 Runtime Simulator (PC-only)

- Launches a **Simulation Window** matching project resolution.
- All bound widgets become interactive; screen navigation works.
- Data updates flow through **DataManager**; alarms/logging run in background.
- Optional **Remote Viewer** mirrors active screen in another window (same DataManager).

---

## 🔔 Alarms

- Define by **expression** or simple condition on a tag.
- Properties: id, message, severity, **ack required**.
- Runtime:
  - Active list + History (timestamps: raised, cleared, ack’ed).
  - **AlarmBanner** (highest priority text, blink), **AlarmTable** (active/history).
  - Acknowledge from UI or via `ack(id)`.

---

## 🧾 Logging & 📈 Trends

- **Cyclic** (interval) and **triggered** logging to CSV/SQLite (timestamped).
- Trend widget:
  - **Live trend:** subscribes to tags and plots rolling data.
  - **Historical trend:** loads a log window for replay.

---

## 🧰 Background Tasks

- **Interval:** every *n* ms → action (set/copy tag, change screen, hardcopy, run snippet).
- **Trigger:** when expression edge occurs → action.
- **Hardcopy:** saves PNG of current screen to `./hardcopy/YYYYMMDD_hhmmss.png`.

---

## 🧪 Usage (Typical Flow)

1. **New Project** → choose resolution, name.
2. **Add tags** in Tag Manager (or create while binding).
3. **Design screens**: drag widgets from Toolbox, configure properties in Properties Panel.
4. **Navigation**: add buttons with `Change Screen` actions.
5. **Alarms/Logging/Recipes/Background**: configure in respective managers.
6. Optional **scripts** for advanced logic.
7. **Run** → test interaction, values, alarms, trends.
8. (Optional) **Open Remote Viewer** to mirror runtime.
9. **Stop** → iterate design; **Save** project.

---

## ✅ Acceptance Criteria (per major feature)

- **Canvas & Editing**
  - [ ] Grid/snap, zoom/pan, rubber-band multi-select
  - [ ] Align/distribute, z-order, copy/paste, undo/redo

- **Widgets**
  - [ ] Button (momentary/toggle/write value/change screen)
  - [ ] Lamp (bool/multi-state, colors, blink)
  - [ ] Numeric display/input (formatting, keypad)
  - [ ] Text display/input
  - [ ] Slider, Level bar
  - [ ] Image
  - [ ] Trend (live); (hist trend optional in v1)
  - [ ] AlarmBanner, AlarmTable
  - [ ] RecipeView (optional v1)

- **Data**
  - [ ] Tag types with limits; change notification; serialization

- **Simulator**
  - [ ] Run/Stop; screen navigation; input events; tag sync
  - [ ] Remote viewer window (mirror)

- **Alarms**
  - [ ] Define expr; active/history; ack; severity visuals

- **Logging/Trends**
  - [ ] Cyclic logging; triggered logging; CSV export
  - [ ] Live trend from tags/log buffer

- **Recipes**
  - [ ] CRUD recipes; apply set to tags

- **Background**
  - [ ] Interval timers; trigger rules; actions (set/copy/changescreen/hardcopy)

- **Scripting**
  - [ ] Project/Screen/Object hooks; helper API; error capture

---

## 🗺 Roadmap (Milestones & Tasks)

### M1 — Foundations (Project + Canvas)
- [ ] Define JSON schema & versioning
- [ ] New/Open/Save/Recent
- [ ] MainWindow + docks (Toolbox, Properties, Project Tree)
- [ ] QGraphicsScene canvas; grid/snap; selection/handles
- [ ] Undo/redo (QUndoStack); align/distribute; z-order
- [ ] Tag Manager UI

### M2 — Core Widgets & Binding
- [ ] Base widget class (metadata, serialization)
- [ ] Button (actions); Lamp; Label/Text; Numeric I/O; Slider; Level bar; Image
- [ ] Properties panel editors (color, font, tag picker)
- [ ] Binding to DataManager (subscribe/emit)

### M3 — Simulator & Navigation
- [ ] Simulation window; design→runtime mapping
- [ ] Screen loader; `change_screen()`
- [ ] Remote viewer mirror (optional)

### M4 — Alarms
- [ ] Alarm model + expressions
- [ ] AlarmManager (active/history, ack)
- [ ] AlarmBanner/AlarmTable widgets
- [ ] Severity styles (blink/sound optional)

### M5 — Logging & Trends
- [ ] LoggingManager (cyclic/triggered, CSV/SQLite)
- [ ] Live Trend widget (PyQtGraph proxy)
- [ ] Historical trend (optional v1.1)

### M6 — Recipes
- [ ] Recipe model + editor
- [ ] Apply recipe; RecipeView widget

### M7 — Background Tasks
- [ ] Config UI (interval/trigger)
- [ ] Actions: set/copy tag, change screen, hardcopy, run snippet
- [ ] Hardcopy (PNG) implementation

### M8 — Scripting
- [ ] Script editor UI (project/screen/object)
- [ ] Helper API; project tick; screen on_open/on_close; object events
- [ ] Error capture console; non-blocking `delay_ms`

### M9 — Polish & Docs
- [ ] Performance profiling (100+ widgets)
- [ ] Cross-platform checks
- [ ] Sample demo project
- [ ] Docs: user guide + developer notes
- [ ] Optional packaging (PyInstaller)

---

## 🧑‍💻 Contributing

1. Fork → feature branch → PR.  
2. Style: PEP8; type hints preferred.  
3. Write unit tests for non-GUI (data/alarm/logging/script).  
4. Update docs when behavior changes.  
5. For large features, open an issue to discuss design first.

---

## 🧭 Design Notes & Best Practices

- **Canvas items = data:** Every property is serializable; keep runtime-only state separate.
- **Signals first:** Prefer `DataManager` signals over polling.
- **No blocking:** Use Qt timers and `delay_ms` in scripts; avoid `time.sleep`.
- **Determinism:** Keep a stable **scan period** (e.g., 100 ms) for project tick & background checks.
- **Errors visible:** Surface script exceptions and engine warnings in a docked “Console” panel.
- **Isolation:** Scripts run in constrained contexts; expose only helper API & safe objects.

---

## 📜 License

Choose a license (e.g., MIT) and include `LICENSE` in the repository.

---

## 📎 Appendix — Example Scripts

**Project `project_tick`** (soft-ramp a speed when motor runs):
```python
if read('MotorRun'):
    write('Speed', min(read('Speed') + 1, 100))
```

**Screen `on_open`** (init labels/values):
```python
write('Message', 'Welcome to Main Screen')
```

**Button `on_click`** (toggle & navigate):
```python
toggle('MotorRun')
if read('MotorRun'):
    change_screen('RunScreen')
```

**Background trigger action** (when Temp > 80):
```python
# action kind: run_snippet
write('AlarmBlink', True)
```

---

## Designer vs Simulator

- Independent executables: the designer (`main.py`) and the runtime simulator (`runtime_simulator/main.py`) run in separate processes and windows.
- From the designer, use Project → Run (F5) to spawn the simulator for the currently open project.
- You can also launch the simulator directly from a shell: `python runtime_simulator/main.py <path-to-project.hmi>`.
- The simulator never shares in‑process state with the designer; project data flows via the saved `.hmi` JSON file.

### Typical Flow

- Design in the designer UI, Save.
- Press Run (F5) → a separate simulator window opens and loads the saved project.
- Iterate: edit in designer → Save → relaunch Run to test again.
\n---
\n## Shared Services (Designer + Runtime)

- Both applications import from `services/` for project parsing and data access (screens, tags, comments).
- `services/serialization.py` offers `load_from_file()` / `save_to_file()` helpers for consistent JSON I/O.
- Runtime resolves tags using `[DB_NAME]::TAG_NAME` format to match exported references and avoid ambiguity.
