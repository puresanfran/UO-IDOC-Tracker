# Britannia House Tracker

An interactive map tool for tracking house locations, decay status, and IDOC countdowns on the Britannia map.

![Britannia House Tracker](https://img.shields.io/badge/platform-Windows-blue) ![Python](https://img.shields.io/badge/built%20with-PyQt6-purple)

---

## ⚠️ Antivirus Warning

Norton, Windows Defender, and other antivirus tools may flag `BritanniaHouseTracker.exe` as suspicious. **This is a false positive.** It is caused by PyInstaller — the tool used to package the app — which is commonly flagged by AVs because it bundles a Python runtime into a single exe file.

The full source code is open and auditable right here on GitHub (`tracker.py`). If you don't trust the exe, you can run directly from source — see [Running from Source](#running-from-source) below.

To allow it in Norton: **My Norton → Device Security → Scans → History → find the file → More Options → Restore & Exclude.**

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
| Left-click pin | Open pin bubble (notes preview) |
| Right-click pin | Edit or delete pin |
| Ctrl+F | Focus pin search |
| R | Reset view |

---

## Tracking Houses

Right-click anywhere on the map to drop a pin. Each pin records:

- **Label** — a nickname for the house
- **House type** — size/style
- **Decay status** — current stage
- **Time remaining** — manually set how much time is left in the current stage
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

### Notes
- Left-click a pin on the map to open a bubble with a short notes preview
- In the Decay Timers panel, hover the 📋 icon next to a pin's name to read the full notes

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

> **Note:** Running from source requires the UOAM BMP map files and .MAP landmark files. These are bundled inside the standalone exe but must be provided separately for source runs.
