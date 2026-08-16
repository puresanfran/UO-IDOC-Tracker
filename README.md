# Britannia House Tracker

An interactive map tool for tracking house locations, decay status, and IDOC countdowns on the Britannia map.

![Britannia House Tracker](https://img.shields.io/badge/platform-Windows-blue) ![Python](https://img.shields.io/badge/built%20with-PyQt6-purple)

---

## Quick Start (No Install Required)

1. Download the latest release
2. Unzip the folder anywhere on your PC
3. Double-click **`BritanniaHouseTracker.exe`**

That's it — no Python, no dependencies, no setup.

`pins.json` is created automatically in the same folder as the exe the first time you save a pin. The map data is bundled inside the exe — no other files are needed.

---

## Controls

| Input | Action |
|-------|--------|
| Left-drag | Pan the map |
| Scroll wheel | Zoom in / out |
| Right-click map | Drop a new pin |
| Left-click pin | Select pin |
| Right-click pin | Edit or delete pin |
| R | Reset view |
| Delete | Delete selected pin |
| Ctrl+F | Focus pin search |

---

## Tracking Houses

Right-click anywhere on the map to drop a pin. Each pin records:

- **Label** — a nickname for the house
- **House type** — size/style
- **Decay status** — current stage
- **Notes** — anything extra

The app uses UO's real decay timing:

| Stage | Duration |
|-------|----------|
| Brand New | 67h 12m |
| Slightly Worn | 67h 12m |
| Somewhat Worn | 67h 12m |
| Fairly Worn | 67h 12m |
| Greatly Worn | 67h 12m |
| In Danger of Collapsing | 24h |

Countdowns run in real time and survive app restarts. The **Decay Timers** panel in the sidebar shows all tracked houses sorted by urgency.

---

## Running from Source

Requires Python 3.10+ and the following packages:

```
pip install PyQt6 Pillow
```

Then:

```
python tracker.py
```

Source also expects the UOAM map files at `E:\UOAM\` (MAP0-1/2/4/8.BMP and the .MAP landmark files). The standalone exe has these bundled in.

---

## Building the Exe

```
pip install pyinstaller
python -m PyInstaller --onefile --windowed --name "BritanniaHouseTracker" \
  --add-data "E:\UOAM\MAP0-1.BMP;uoam" \
  --add-data "E:\UOAM\MAP0-2.BMP;uoam" \
  --add-data "E:\UOAM\MAP0-4.BMP;uoam" \
  --add-data "E:\UOAM\MAP0-8.BMP;uoam" \
  --add-data "E:\UOAM\Common.MAP;uoam" \
  --add-data "E:\UOAM\Atlas.MAP;uoam" \
  --add-data "E:\UOAM\Dungeons.MAP;uoam" \
  tracker.py
```
