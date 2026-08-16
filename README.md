# UO Second Age — Housing Placement Analyzer

Reads your Ultima Online Second Age client files (read-only)
and produces an interactive map showing every valid house placement spot.

## Setup

1. Copy this folder to `E:\Ultima House Mapping\`
2. Install Python 3.10+ from https://python.org
3. Double-click `run.bat` — it handles everything else

OR run manually in PowerShell:

```powershell
pip install numpy Pillow

# Analyze small houses (fastest — ~5 min)
python 1_analyze.py --house small

# Analyze all sizes (~30 min, saves each as you go)
python 1_analyze.py --all

# Re-run house analysis without re-reading map files (much faster)
python 1_analyze.py --house keep --skip-map

# Open interactive viewer
python 2_viewer.py
```

## Output files (in E:\Ultima House Mapping\output\)

| File | Description |
|------|-------------|
| `britannia_base.png` | Rendered full map (1792×1024 at 4x scale) |
| `terrain_blocked.npy` | Boolean: impassable tiles |
| `terrain_altitude.npy` | Raw altitude values |
| `terrain_flatness.npy` | Altitude variation per tile |
| `guard_zones.npy` | Boolean: guard zone tiles |
| `terrain_tileids.npy` | Raw tile IDs |
| `valid_small.npy` | Valid NW corners for 7×7 house |
| `valid_medium.npy` | Valid NW corners for 14×14 house |
| `valid_large.npy` | Valid NW corners for 14×14 large |
| `valid_tower.npy` | Valid NW corners for 16×14 tower |
| `valid_keep.npy` | Valid NW corners for 24×24 keep |
| `valid_castle.npy` | Valid NW corners for 31×31 castle |
| `housing_*.png` | Overlay map images (one per house size) |

## Viewer controls

| Input | Action |
|-------|--------|
| Left drag | Pan map |
| Scroll wheel | Zoom in/out |
| Left click | Show tile info (coords, altitude, guard zone, valid houses) |
| Right click | Copy tile coordinates to clipboard |
| S key | Save current view as PNG |
| R key | Reset to full map view |
| Sidebar checkboxes | Toggle overlays |
| Town dropdown | Jump to any town |
| Coord box | Jump to specific tile x,y |

## House placement rules applied

- No guard zones (towns, dungeon entrances)
- No impassable tiles (mountains, water, large trees, rocks, walls)
- Terrain must be flat within footprint (altitude variation ≤ 2)
- 5-tile clearance north and south
- 1-tile clearance east and west

## Notes

- Analysis reads from `E:\Ultima Online` but never writes to it
- First run takes 5–30 min depending on house sizes selected
- Subsequent runs with `--skip-map` are much faster (reuses saved .npy files)
- The `.npy` files are large (map arrays) — keep them, they save time
