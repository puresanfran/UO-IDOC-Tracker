"""
tracker.py  --  UO House Tracker  (PyQt6)
==========================================
Pan/zoom the UOAM map and drop pins to track houses.

Controls:
  Left-drag          Pan
  Scroll wheel       Zoom in/out
  Left-click pin     Select pin
  Right-click map    Drop new pin
  Right-click pin    Edit / Delete
  Ctrl+F             Focus pin search
  R                  Reset view
  Delete             Delete selected pin
"""

import os, sys, json, time, math
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QLabel, QPushButton, QLineEdit, QListWidget, QListWidgetItem,
    QCheckBox, QFrame, QScrollArea, QSplitter, QDialog, QComboBox,
    QTextEdit, QDialogButtonBox, QMenu, QSizePolicy, QToolButton,
    QGraphicsView, QGraphicsScene, QGraphicsPixmapItem,
)
from PyQt6.QtGui import (
    QPixmap, QImage, QPainter, QPen, QBrush, QColor, QFont,
    QFontMetrics, QCursor, QAction, QKeySequence,
)
from PyQt6.QtCore import (
    Qt, QTimer, QPointF, QRectF, QSizeF, pyqtSignal, QThread, QObject,
)
from PIL import Image

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
UOAM_PATH   = r"E:\UOAM"
PINS_FILE   = r"E:\Ultima House Mapping\pins.json"
OUTPUT_PATH = r"E:\Ultima House Mapping\output"

UOAM_BMPS = {
    1: os.path.join(UOAM_PATH, "MAP0-1.BMP"),
    2: os.path.join(UOAM_PATH, "MAP0-2.BMP"),
    4: os.path.join(UOAM_PATH, "MAP0-4.BMP"),
    8: os.path.join(UOAM_PATH, "MAP0-8.BMP"),
}

MAP_W = 5000   # clipped — right half is Trammel/dead space, no houses placeable
MAP_H = 4096

# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
HOUSE_TYPES = [
    "Small 7x7", "Medium 14x14", "Large 14x14",
    "Tower 16x14", "Keep 24x24", "Castle 31x31",
]

DECAY_STAGES = [
    "Brand New", "Slightly Worn", "Somewhat Worn",
    "Fairly Worn", "Greatly Worn", "In Danger of Collapsing",
]

DECAY_COLORS = {
    "Brand New":               ("#22cc44", "#000000"),
    "Slightly Worn":           ("#aadd22", "#000000"),
    "Somewhat Worn":           ("#ffdd00", "#000000"),
    "Fairly Worn":             ("#ff8800", "#ffffff"),
    "Greatly Worn":            ("#ff4400", "#ffffff"),
    "In Danger of Collapsing": ("#cc0000", "#ffffff"),
}

STAGE_DURATION = {
    "Brand New":               67 * 3600 + 12 * 60,   # 242 640 s
    "Slightly Worn":           67 * 3600 + 12 * 60,
    "Somewhat Worn":           67 * 3600 + 12 * 60,
    "Fairly Worn":             67 * 3600 + 12 * 60,
    "Greatly Worn":            67 * 3600 + 12 * 60,
    "In Danger of Collapsing": 24 * 3600,              # 86 400 s
}

NEXT_STAGE = {
    "Brand New":               "Slightly Worn",
    "Slightly Worn":           "Somewhat Worn",
    "Somewhat Worn":           "Fairly Worn",
    "Fairly Worn":             "Greatly Worn",
    "Greatly Worn":            "In Danger of Collapsing",
    "In Danger of Collapsing": None,
}

# ---------------------------------------------------------------------------
# Stylesheet
# ---------------------------------------------------------------------------
GOLD     = "#9b59f5"
GOLD_LT  = "#b87fff"
GOLD_DIM = "#6b3ab8"
BG       = "#141416"
SIDEBAR  = "#1c1c1e"
CARD     = "#242428"
BORDER   = "rgba(255, 255, 255, 20)"
TEXT     = "#e2e2e6"
TEXT_DIM = "#4a4a52"
TEXT_MID = "#8a8a96"
BLUE     = "#763cee"
BLUE_LT  = "#9b59f5"
RED      = "#f70d37"
ORANGE   = "#9b59f5"
GREEN    = "#18e614"
PURPLE   = "#9b59f5"

QSS = f"""
* {{
    font-family: "Segoe UI", sans-serif;
    font-size: 13px;
    color: {TEXT};
    outline: 0;
}}
QMainWindow, QWidget {{ background: {BG}; }}
QSplitter::handle {{ background: {BORDER}; width: 1px; }}

/* Scrollbar */
QScrollArea {{ border: none; background: transparent; }}
QScrollBar:vertical {{
    background: transparent; width: 3px; border: none; margin: 0;
}}
QScrollBar::handle:vertical {{
    background: rgba(255,255,255,32); border-radius: 2px; min-height: 30px;
}}
QScrollBar::handle:vertical:hover {{ background: rgba(255,255,255,56); }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}

/* Accordion */
QToolButton#accordion {{
    background: transparent;
    color: {TEXT_DIM};
    border: none;
    border-bottom: 1px solid {BORDER};
    text-align: left;
    padding: 10px 16px;
    font-size: 10px;
    font-weight: 600;
    letter-spacing: 2px;
}}
QToolButton#accordion:hover {{ color: {TEXT_MID}; background: rgba(255,255,255,6); }}
QToolButton#accordion:checked {{ color: {TEXT}; }}
QFrame#section {{ background: transparent; border: none; }}

/* Inputs */
QLineEdit, QTextEdit {{
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 7px 11px;
    color: {TEXT};
    selection-background-color: rgba(155, 89, 245, 48);
}}
QLineEdit:focus, QTextEdit:focus {{
    border-color: {GOLD};
}}
QComboBox {{
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 7px 11px;
    color: {TEXT};
}}
QComboBox:focus {{ border-color: {GOLD}; }}
QComboBox::drop-down {{ border: none; width: 18px; }}
QComboBox::down-arrow {{ image: none; }}
QComboBox QAbstractItemView {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 7px;
    selection-background-color: rgba(155, 89, 245, 40);
    color: {TEXT};
    padding: 3px;
}}

/* Buttons */
QPushButton {{
    background: rgba(255,255,255,12);
    border: 1px solid {BORDER};
    border-radius: 7px;
    padding: 7px 16px;
    color: {TEXT_MID};
}}
QPushButton:hover {{ background: rgba(255,255,255,24); color: {TEXT}; border-color: rgba(255,255,255,40); }}
QPushButton:pressed {{ background: rgba(255,255,255,6); }}
QPushButton#primary {{
    background: {BLUE};
    border: 1px solid {BLUE_LT};
    border-radius: 7px;
    color: #ffffff;
    font-weight: 600;
    padding: 7px 18px;
}}
QPushButton#primary:hover {{ background: {BLUE_LT}; border-color: {BLUE_LT}; }}
QPushButton#primary:pressed {{ background: #0a0880; }}

/* List */
QListWidget {{
    background: {BG};
    border: 1px solid {BORDER};
    border-radius: 8px;
    outline: none;
    padding: 3px;
}}
QListWidget::item {{
    padding: 5px 9px;
    border-radius: 5px;
    color: {TEXT_MID};
}}
QListWidget::item:selected {{ background: rgba(155,89,245,32); color: {GOLD_LT}; }}
QListWidget::item:hover:!selected {{ background: rgba(255,255,255,10); color: {TEXT}; }}

/* Status bar */
QStatusBar {{
    background: #0a0c10;
    color: {TEXT_DIM};
    font-size: 11px;
    border-top: 1px solid {BORDER};
    padding: 0 6px;
}}
QStatusBar QPushButton {{
    padding: 3px 10px;
    font-size: 11px;
    border-radius: 5px;
    margin: 2px 0;
}}

/* Menus */
QMenu {{
    background: {CARD};
    border: 1px solid {BORDER};
    border-radius: 9px;
    padding: 5px;
    color: {TEXT};
}}
QMenu::item {{ padding: 7px 20px 7px 12px; border-radius: 5px; color: {TEXT_MID}; }}
QMenu::item:selected {{ background: rgba(155,89,245,34); color: {TEXT}; }}
QMenu::separator {{ height: 1px; background: {BORDER}; margin: 4px 8px; }}

/* Dialog */
QDialog {{ background: {SIDEBAR}; }}
QLabel {{ color: {TEXT}; }}
QDialogButtonBox QPushButton {{ min-width: 88px; }}

/* Checkbox */
QCheckBox {{ color: {TEXT_MID}; spacing: 8px; }}
QCheckBox::indicator {{
    width: 15px; height: 15px; border-radius: 4px;
    border: 1px solid {BORDER}; background: {BG};
}}
QCheckBox::indicator:checked {{ background: {BLUE}; border-color: {GOLD}; }}
QCheckBox:hover {{ color: {TEXT}; }}

/* Named labels */
QLabel#idoc_name  {{ color: {TEXT}; font-weight: 600; font-size: 13px; }}
QLabel#idoc_timer {{ color: {RED}; font-family: Consolas; font-size: 12px; font-weight: 600; }}
QLabel#idoc_empty {{ color: {TEXT_DIM}; font-size: 12px; font-style: italic; padding: 4px 0; }}
QLabel#pin_info   {{ color: {TEXT_MID}; font-family: Consolas; font-size: 11px; }}
"""

# ---------------------------------------------------------------------------
# Landmark loader
# ---------------------------------------------------------------------------
def load_landmarks():
    landmarks = []
    for fname in ("Common.MAP", "Atlas.MAP", "Dungeons.MAP"):
        path = os.path.join(UOAM_PATH, fname)
        if not os.path.exists(path):
            continue
        with open(path, encoding="latin-1") as f:
            lines = f.readlines()
        for line in lines[1:]:
            line = line.strip()
            if not line or line[0] not in ("+", "-"):
                continue
            try:
                rest     = line[1:]
                cat, rem = rest.split(":", 1)
                parts    = rem.strip().split(" ", 3)
                x, y, fac = int(parts[0]), int(parts[1]), int(parts[2])
                name     = parts[3].strip() if len(parts) > 3 else cat.strip()
                if fac == 0:
                    landmarks.append((name, x, y, cat.strip()))
            except Exception:
                continue
    landmarks.sort(key=lambda t: t[0].lower())
    return landmarks

# ---------------------------------------------------------------------------
# PIL image → QPixmap
# ---------------------------------------------------------------------------
def pil_to_qpixmap(img: Image.Image) -> QPixmap:
    img = img.convert("RGBA")
    data = img.tobytes("raw", "RGBA")
    qi = QImage(data, img.width, img.height, QImage.Format.Format_RGBA8888)
    return QPixmap.fromImage(qi)

# ---------------------------------------------------------------------------
# Accordion widget
# ---------------------------------------------------------------------------
class Accordion(QWidget):
    def __init__(self, title: str, parent=None, expanded: bool = True):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        self._btn = QToolButton(objectName="accordion")
        self._btn.setObjectName("accordion")
        self._btn.setCheckable(True)
        self._btn.setChecked(expanded)
        self._btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        self._update_text(title, expanded)
        self._title = title
        self._btn.toggled.connect(self._toggle)
        layout.addWidget(self._btn)

        self._content = QFrame(objectName="section")
        self._content.setObjectName("section")
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(0, 4, 0, 4)
        content_layout.setSpacing(4)
        self._content.setVisible(expanded)
        layout.addWidget(self._content)

    def _update_text(self, title, expanded):
        arrow = "▾" if expanded else "▸"
        self._btn.setText(f"  {arrow}  {title.upper()}")

    def _toggle(self, checked):
        self._content.setVisible(checked)
        self._update_text(self._title, checked)

    def content_layout(self):
        return self._content.layout()

    def add_widget(self, w):
        self._content.layout().addWidget(w)

# ---------------------------------------------------------------------------
# Pin dialog
# ---------------------------------------------------------------------------
class PinDialog(QDialog):
    def __init__(self, parent, x, y, pin=None):
        super().__init__(parent)
        self.setWindowTitle("Edit Pin" if pin else "New Pin")
        self.setModal(True)
        self.setMinimumWidth(400)
        self.result_pin = None
        self._pin = pin
        self._x, self._y = x, y

        lay = QVBoxLayout(self)
        lay.setSpacing(12)
        lay.setContentsMargins(24, 20, 24, 20)

        # Header
        title = QLabel("Edit Pin" if pin else "Drop Pin")
        title.setStyleSheet(
            f"color: {GOLD}; font-size: 15px; font-weight: 700; letter-spacing: 1px;")
        lay.addWidget(title)

        coord_lbl = QLabel(f"x = {x}   y = {y}")
        coord_lbl.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 11px; font-family: Consolas;")
        lay.addWidget(coord_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {BORDER};")
        lay.addWidget(sep)

        def field(label_text, widget):
            col = QVBoxLayout()
            col.setSpacing(4)
            lbl = QLabel(label_text.upper())
            lbl.setStyleSheet(
                f"color: {TEXT_DIM}; font-size: 10px; font-weight: 600; letter-spacing: 1.5px;")
            col.addWidget(lbl)
            col.addWidget(widget)
            lay.addLayout(col)
            return widget

        self.label_edit = field("Label", QLineEdit(pin["label"] if pin else ""))
        self.label_edit.setPlaceholderText("House nickname…")

        self.type_combo = QComboBox()
        self.type_combo.addItems(HOUSE_TYPES)
        self.type_combo.setCurrentText(pin["house_type"] if pin else HOUSE_TYPES[0])
        field("House Type", self.type_combo)

        self.decay_combo = QComboBox()
        self.decay_combo.addItems(DECAY_STAGES)
        self.decay_combo.setCurrentText(pin["decay"] if pin else DECAY_STAGES[0])
        field("Decay Status", self.decay_combo)

        self.notes_edit = QTextEdit()
        self.notes_edit.setFixedHeight(72)
        self.notes_edit.setPlaceholderText("Notes…")
        if pin:
            self.notes_edit.setPlainText(pin.get("notes", ""))
        field("Notes", self.notes_edit)

        lay.addSpacing(4)
        btns = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save |
            QDialogButtonBox.StandardButton.Cancel)
        btns.button(QDialogButtonBox.StandardButton.Save).setObjectName("primary")
        btns.accepted.connect(self._save)
        btns.rejected.connect(self.reject)
        lay.addWidget(btns)

        self.label_edit.setFocus()

    def _save(self):
        decay     = self.decay_combo.currentText()
        old_decay = self._pin["decay"] if self._pin else None
        old_set   = self._pin.get("decay_set_at") or self._pin.get("idoc_set_at") if self._pin else None
        # Preserve timestamp if the stage didn't change, otherwise start fresh
        decay_set_at = old_set if (old_decay == decay and old_set) else time.time()

        self.result_pin = {
            "id":           self._pin["id"] if self._pin else int(time.time() * 1000),
            "x":            self._x,
            "y":            self._y,
            "label":        self.label_edit.text().strip(),
            "house_type":   self.type_combo.currentText(),
            "decay":        decay,
            "notes":        self.notes_edit.toPlainText().strip(),
            "decay_set_at": decay_set_at,
        }
        self.accept()

# ---------------------------------------------------------------------------
# Map canvas (QGraphicsView)
# ---------------------------------------------------------------------------
class MapCanvas(QGraphicsView):
    tile_clicked  = pyqtSignal(float, float)   # left-click tile coords
    pin_requested = pyqtSignal(float, float)   # right-click empty space
    pin_context   = pyqtSignal(object, object) # right-click near pin: (pin, QPoint)

    PIN_HIT_PX = 14

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setDragMode(QGraphicsView.DragMode.NoDrag)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        self.setBackgroundBrush(QBrush(QColor("#141416")))
        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

        # Map tiles {scale: QPixmap}
        self.tiles: dict[int, QPixmap] = {}
        self._tile_item = QGraphicsPixmapItem()
        self._tile_item.setZValue(0)
        self._scene.addItem(self._tile_item)

        # Pin overlay item (painted each frame)
        self._pin_item = _PinOverlayItem(self)
        self._pin_item.setZValue(1)
        self._scene.addItem(self._pin_item)

        # View state (tile coords)
        self._view_x   = 0.0
        self._view_y   = 0.0
        self._zoom     = 0.45        # canvas px per tile

        # Smooth zoom
        self._zoom_target  = self._zoom
        self._zoom_anchor  = None    # tile coord to hold
        self._zoom_ev_pos  = None    # viewport pixel

        # Pan state
        self._pan_start    = None
        self._pan_view     = None
        self._pan_moved    = False
        self._panning      = False

        # Pin data (set by MainWindow)
        self.pins:     list  = []
        self.selected: int | None = None
        self.landmarks: list = []

        # Animation
        self._pulse_phase = 0.0
        self._anim_timer  = QTimer(self)
        self._anim_timer.timeout.connect(self._anim_tick)
        self._anim_timer.start(33)

    # ----------------------------------------------------------------
    # Tile helpers
    # ----------------------------------------------------------------
    def load_tile(self, scale: int, path: str):
        img = Image.open(path).convert("RGB")
        self.tiles[scale] = pil_to_qpixmap(img)

    def _best_scale(self) -> int:
        for s in (1, 2, 4, 8):
            if self._zoom * s >= 0.8:
                return s
        return 8

    def get_tile(self, scale: int) -> QPixmap | None:
        if scale in self.tiles:
            return self.tiles[scale]
        # fallback: resize from nearest available
        for s in (1, 2, 4, 8):
            if s in self.tiles:
                src = self.tiles[s]
                ratio = s / scale
                return src.scaled(int(src.width() * ratio),
                                   int(src.height() * ratio),
                                   Qt.AspectRatioMode.IgnoreAspectRatio,
                                   Qt.TransformationMode.FastTransformation)
        return None

    # ----------------------------------------------------------------
    # Coordinate helpers
    # ----------------------------------------------------------------
    def _vp_to_tile(self, vx: float, vy: float):
        return (self._view_x + vx / self._zoom,
                self._view_y + vy / self._zoom)

    def _tile_to_vp(self, tx: float, ty: float):
        return ((tx - self._view_x) * self._zoom,
                (ty - self._view_y) * self._zoom)

    def reset_view(self):
        vw = self.viewport().width()  or 900
        vh = self.viewport().height() or 700
        self._zoom        = 0.45
        self._zoom_target = 0.45
        self._view_x      = max(0.0, 1400 - vw / self._zoom / 2)
        self._view_y      = max(0.0, 1800 - vh / self._zoom / 2)
        self._render()

    def jump_to(self, tx: float, ty: float, zoom: float | None = None):
        vw = self.viewport().width()  or 900
        vh = self.viewport().height() or 700
        if zoom is not None:
            self._zoom = zoom
            self._zoom_target = zoom
        self._view_x = max(0.0, tx - vw / self._zoom / 2)
        self._view_y = max(0.0, ty - vh / self._zoom / 2)
        self._render()

    # ----------------------------------------------------------------
    # Render
    # ----------------------------------------------------------------
    def _render(self):
        vw = self.viewport().width()
        vh = self.viewport().height()
        if vw < 10 or vh < 10:
            return

        sc   = self._best_scale()
        tile = self.get_tile(sc)
        if tile is None:
            return

        tx0 = max(0, int(self._view_x))
        ty0 = max(0, int(self._view_y))
        tx1 = min(MAP_W, int(self._view_x + vw / self._zoom) + 2)
        ty1 = min(MAP_H, int(self._view_y + vh / self._zoom) + 2)

        bx0 = max(0,            tx0 // sc)
        by0 = max(0,            ty0 // sc)
        bx1 = min(tile.width(), tx1 // sc + 1)
        by1 = min(tile.height(), ty1 // sc + 1)

        crop     = tile.copy(bx0, by0, bx1 - bx0, by1 - by0)
        cpx      = self._zoom * sc
        out_w    = max(1, int((bx1 - bx0) * cpx) + 1)
        out_h    = max(1, int((by1 - by0) * cpx) + 1)
        scaled   = crop.scaled(out_w, out_h,
                                Qt.AspectRatioMode.IgnoreAspectRatio,
                                Qt.TransformationMode.FastTransformation)

        off_x = -int((self._view_x - bx0 * sc) * self._zoom)
        off_y = -int((self._view_y - by0 * sc) * self._zoom)

        self._scene.setSceneRect(0, 0, vw, vh)
        self._tile_item.setPixmap(scaled)
        self._tile_item.setPos(off_x, off_y)

        # Update pin overlay bounds
        self._pin_item.setPos(0, 0)
        self._pin_item.prepareGeometryChange()
        self._pin_item._rect = QRectF(0, 0, vw, vh)
        self._pin_item.update()

    # ----------------------------------------------------------------
    # Animation
    # ----------------------------------------------------------------
    def _anim_tick(self):
        self._pulse_phase = (self._pulse_phase + 0.035) % 1.0

        # Smooth zoom
        zoom_changed = False
        if self._zoom_target is not None and not self._panning:
            diff = self._zoom_target - self._zoom
            if abs(diff) > self._zoom * 0.0005:
                self._zoom += diff * 0.18
                if self._zoom_anchor and self._zoom_ev_pos:
                    tx, ty = self._zoom_anchor
                    ex, ey = self._zoom_ev_pos
                    self._view_x = max(0.0, tx - ex / self._zoom)
                    self._view_y = max(0.0, ty - ey / self._zoom)
                zoom_changed = True
            else:
                self._zoom = self._zoom_target
                self._zoom_target = None
                zoom_changed = True

        has_idoc = any(p["decay"] == "In Danger of Collapsing" for p in self.pins)
        if has_idoc or zoom_changed:
            self._render()

    # ----------------------------------------------------------------
    # Mouse events
    # ----------------------------------------------------------------
    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._pan_start  = ev.position()
            self._pan_view   = (self._view_x, self._view_y)
            self._pan_moved  = False
            self._panning    = False

    def mouseMoveEvent(self, ev):
        if self._pan_start is None:
            return
        pos = ev.position()
        dx = pos.x() - self._pan_start.x()
        dy = pos.y() - self._pan_start.y()
        if abs(dx) > 3 or abs(dy) > 3:
            self._pan_moved = True
            self._panning   = True
        self._view_x = max(0.0, self._pan_view[0] - dx / self._zoom)
        self._view_y = max(0.0, self._pan_view[1] - dy / self._zoom)
        self._render()

    def mouseReleaseEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self._panning = False
            if not self._pan_moved:
                pos = ev.position()
                tx, ty = self._vp_to_tile(pos.x(), pos.y())
                self.tile_clicked.emit(tx, ty)
            self._pan_start = None
            self._pan_moved = False

    def contextMenuEvent(self, ev):
        pos = ev.pos()
        tx, ty = self._vp_to_tile(pos.x(), pos.y())
        pin, dist = self._nearest_pin_at(pos.x(), pos.y())
        if pin and dist <= self.PIN_HIT_PX:
            self.pin_context.emit(pin, ev.globalPos())
        else:
            self.pin_requested.emit(tx, ty)

    def wheelEvent(self, ev):
        delta  = ev.angleDelta().y()
        factor = 1.15 if delta > 0 else (1.0 / 1.15)
        pos    = ev.position()
        current = self._zoom_target if self._zoom_target else self._zoom
        self._zoom_target  = max(0.02, min(16.0, current * factor))
        self._zoom_anchor  = self._vp_to_tile(pos.x(), pos.y())
        self._zoom_ev_pos  = (pos.x(), pos.y())

    def keyPressEvent(self, ev):
        if ev.key() == Qt.Key.Key_R:
            self.reset_view()
        else:
            super().keyPressEvent(ev)

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._render()
        # Let MainWindow reposition any floating overlays
        mw = self.window()
        if hasattr(mw, "_reposition_legend"):
            mw._reposition_legend()

    # ----------------------------------------------------------------
    # Pin helpers
    # ----------------------------------------------------------------
    def _nearest_pin_at(self, vx: float, vy: float):
        best_pin  = None
        best_dist = float("inf")
        for pin in self.pins:
            px, py = self._tile_to_vp(pin["x"], pin["y"])
            d = math.hypot(vx - px, vy - py)
            if d < best_dist:
                best_dist = d
                best_pin  = pin
        return best_pin, best_dist

    def pin_at_vp(self, vx, vy):
        pin, dist = self._nearest_pin_at(vx, vy)
        return pin if dist <= self.PIN_HIT_PX else None


# ---------------------------------------------------------------------------
# Pin overlay (painted directly via QPainter)
# ---------------------------------------------------------------------------
class _PinOverlayItem(QGraphicsPixmapItem if False else QGraphicsPixmapItem.__bases__[0]):
    # We subclass QObject indirectly; use QGraphicsItem approach instead
    pass

from PyQt6.QtWidgets import QGraphicsItem

class _PinOverlayItem(QGraphicsItem):
    def __init__(self, canvas: "MapCanvas"):
        super().__init__()
        self._canvas = canvas
        self._rect   = QRectF(0, 0, 100, 100)

    def boundingRect(self):
        return self._rect

    def paint(self, painter: QPainter, option, widget=None):
        c = self._canvas
        vw = c.viewport().width()
        vh = c.viewport().height()

        tx0 = int(c._view_x)
        ty0 = int(c._view_y)
        tx1 = min(MAP_W, int(c._view_x + vw / c._zoom) + 2)
        ty1 = min(MAP_H, int(c._view_y + vh / c._zoom) + 2)

        zoom = c._zoom
        pulse_sin = math.sin(c._pulse_phase * math.pi * 2)
        r = max(6, min(14, int(zoom * 10)))

        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        show_labels = getattr(c, '_show_labels', True)

        for pin in c.pins:
            px, py = pin["x"], pin["y"]
            if not (tx0 - 80 <= px <= tx1 + 80 and ty0 - 80 <= py <= ty1 + 80):
                continue

            cx_p = int((px - tx0) * zoom)
            cy_p = int((py - ty0) * zoom)

            fill_hex, text_hex = DECAY_COLORS.get(
                pin["decay"], ("#888888", "#ffffff"))
            fill_col = QColor(fill_hex)
            text_col = QColor(text_hex)
            is_sel   = pin["id"] == c.selected

            # Pulse ring for IDOC pins
            if pin["decay"] == "In Danger of Collapsing":
                pr    = r + 4 + int((pulse_sin + 1) * 5)
                alpha = int(160 * (0.5 + 0.5 * pulse_sin))
                pulse_col = QColor(220, 30, 30, alpha)
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(pulse_col))
                painter.drawEllipse(QPointF(cx_p, cy_p), pr, pr)

            # Selection ring
            if is_sel:
                painter.setPen(QPen(QColor(255, 255, 255), 2.5))
                painter.setBrush(Qt.BrushStyle.NoBrush)
                painter.drawEllipse(QPointF(cx_p, cy_p), r + 4, r + 4)

            # Pin circle
            painter.setPen(QPen(QColor(0, 0, 0), 1))
            painter.setBrush(QBrush(fill_col))
            painter.drawEllipse(QPointF(cx_p, cy_p), r, r)

            # Label
            if show_labels and (zoom >= 0.12 or is_sel):
                label = pin.get("label") or pin["house_type"].split()[0]
                painter.setFont(QFont("Segoe UI", 8))
                fm    = painter.fontMetrics()
                tw    = fm.horizontalAdvance(label)
                lx    = cx_p + r + 4
                ly    = cy_p + fm.ascent() // 2
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QBrush(QColor(0, 0, 0, 160)))
                painter.drawRoundedRect(lx - 2, ly - fm.ascent() - 1,
                                        tw + 6, fm.height() + 2, 3, 3)
                painter.setPen(QPen(QColor(255, 255, 255)))
                painter.drawText(lx + 1, ly, label)


# ---------------------------------------------------------------------------
# Sidebar widgets
# ---------------------------------------------------------------------------
class DecayRow(QWidget):
    clicked = pyqtSignal(object)

    def __init__(self, pin: dict, parent=None):
        super().__init__(parent)
        self._pin = pin
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))

        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 10, 12, 10)
        lay.setSpacing(4)

        # Top row: label + coords
        top = QHBoxLayout()
        top.setSpacing(6)
        label = pin.get("label") or pin["house_type"].split()[0]
        name_lbl = QLabel(label, objectName="idoc_name")
        top.addWidget(name_lbl)
        top.addStretch()
        coord_lbl = QLabel(f"{pin['x']}, {pin['y']}")
        coord_lbl.setStyleSheet(f"color: {TEXT_DIM}; font-size: 11px; font-family: Consolas;")
        top.addWidget(coord_lbl)
        lay.addLayout(top)

        # Stage badge
        fill_hex, _ = DECAY_COLORS.get(pin["decay"], ("#888888", "#ffffff"))
        self.stage_lbl = QLabel(pin["decay"])
        self.stage_lbl.setStyleSheet(
            f"color: {fill_hex}; font-size: 10px; font-weight: 600; letter-spacing: 0.5px;")
        lay.addWidget(self.stage_lbl)

        # Timer row
        self.timer_lbl = QLabel("calculating...", objectName="idoc_timer")
        lay.addWidget(self.timer_lbl)

        self._normal_style  = (
            f"DecayRow {{ background: {CARD}; border: 1px solid {BORDER}; "
            f"border-radius: 10px; }}")
        self._hover_style   = (
            f"DecayRow {{ background: #20205a; border: 1px solid rgba(39,152,246,64); "
            f"border-radius: 10px; }}")
        self._expired_style = (
            f"DecayRow {{ background: #2a0818; border: 1px solid rgba(247,13,55,64); "
            f"border-radius: 10px; }}")
        self.setStyleSheet(self._normal_style)

    def update_timer(self, now: float):
        set_at = self._pin.get("decay_set_at") or self._pin.get("idoc_set_at")
        decay  = self._pin["decay"]
        duration = STAGE_DURATION.get(decay, 0)
        next_st  = NEXT_STAGE.get(decay)

        if not set_at:
            self.timer_lbl.setText("⚠  no timer set — edit pin to start")
            self.timer_lbl.setStyleSheet(
                f"color: {TEXT_DIM}; font-family: Consolas; font-size: 12px;")
            return

        remaining = (set_at + duration) - now

        if remaining <= 0:
            if next_st is None:
                self.timer_lbl.setText("⚠  COLLAPSED — house may be gone")
                self.timer_lbl.setStyleSheet(
                    f"color: {RED}; font-family: Consolas; font-size: 12px; font-weight: 600;")
                self.setStyleSheet(self._expired_style)
            else:
                # Show how long overdue
                overdue = abs(remaining)
                h = int(overdue // 3600)
                m = int((overdue % 3600) // 60)
                self.timer_lbl.setText(f"⚠  {h:02d}:{m:02d} past → {next_st}")
                self.timer_lbl.setStyleSheet(
                    f"color: #ff8800; font-family: Consolas; font-size: 12px; font-weight: 600;")
                self.setStyleSheet(self._expired_style)
        else:
            h = int(remaining // 3600)
            m = int((remaining % 3600) // 60)
            s = int(remaining % 60)
            if next_st is None:
                label = "until collapse"
            else:
                label = f"→ {next_st}"
            if remaining < 7200:
                col = RED
            elif remaining < 14400:
                col = ORANGE
            else:
                col = GREEN
            self.timer_lbl.setText(f"⏱  {h:02d}:{m:02d}:{s:02d} {label}")
            self.timer_lbl.setStyleSheet(
                f"color: {col}; font-family: Consolas; font-size: 12px; font-weight: 600;")
            self.setStyleSheet(self._normal_style)

    def enterEvent(self, ev):
        self.setStyleSheet(self._hover_style)

    def leaveEvent(self, ev):
        self.setStyleSheet(self._normal_style)

    def mousePressEvent(self, ev):
        if ev.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._pin)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("⚔  Britannia House Tracker")
        self.resize(1440, 860)
        self.setMinimumSize(900, 600)

        self.pins:      list  = []
        self.landmarks: list  = []
        self._filtered_pins:  list = []
        self._filtered_lm:    list = []
        self._idoc_rows:      list[DecayRow] = []
        self._show_labels = True

        self._build_ui()
        self._load()

        # Timers
        self._idoc_timer = QTimer(self)
        self._idoc_timer.timeout.connect(self._idoc_tick)
        self._idoc_timer.start(1000)

    # ----------------------------------------------------------------
    # Build UI
    # ----------------------------------------------------------------
    def _build_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root_lay = QHBoxLayout(central)
        root_lay.setContentsMargins(0, 0, 0, 0)
        root_lay.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root_lay.addWidget(splitter)

        # Map
        self.canvas = MapCanvas()
        self.canvas.tile_clicked.connect(self._on_tile_clicked)
        self.canvas.pin_requested.connect(self._drop_pin)
        self.canvas.pin_context.connect(self._pin_context_menu)
        self.canvas._show_labels = True
        splitter.addWidget(self.canvas)

        # Sidebar
        sidebar_wrap = QWidget()
        sidebar_wrap.setFixedWidth(280)
        sidebar_wrap.setStyleSheet(f"background: {SIDEBAR};")
        sw_lay = QVBoxLayout(sidebar_wrap)
        sw_lay.setContentsMargins(0, 0, 0, 0)
        sw_lay.setSpacing(0)

        # Sidebar header
        hdr = QWidget()
        hdr.setFixedHeight(52)
        hdr.setStyleSheet(
            f"background: {BG}; border-bottom: 1px solid {BORDER};")
        hdr_lay = QHBoxLayout(hdr)
        hdr_lay.setContentsMargins(16, 0, 16, 0)
        title_lbl = QLabel("⚔  BRITANNIA")
        title_lbl.setStyleSheet(
            f"color: {TEXT}; font-size: 12px; font-weight: 700; letter-spacing: 3px;")
        hdr_lay.addWidget(title_lbl)
        hdr_lay.addStretch()
        sw_lay.addWidget(hdr)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        inner = QWidget()
        inner.setStyleSheet(f"background: {SIDEBAR};")
        inner_lay = QVBoxLayout(inner)
        inner_lay.setContentsMargins(0, 4, 0, 16)
        inner_lay.setSpacing(0)
        inner_lay.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(inner)
        sw_lay.addWidget(scroll)

        def add_section(title, expanded=True):
            acc = Accordion(title, expanded=expanded)
            inner_lay.addWidget(acc)
            return acc

        def card_pad(w, h=12, v=4):
            wrap = QWidget()
            wrap.setStyleSheet("background: transparent;")
            l = QHBoxLayout(wrap)
            l.setContentsMargins(h, v, h, v)
            l.addWidget(w)
            return wrap

        # ---- 1. GO TO TILE ----
        goto_acc = add_section("Go To Tile", expanded=True)
        goto_w = QWidget()
        goto_w.setStyleSheet("background: transparent;")
        goto_lay = QHBoxLayout(goto_w)
        goto_lay.setContentsMargins(12, 4, 12, 8)
        goto_lay.setSpacing(6)
        self.goto_x = QLineEdit(); self.goto_x.setPlaceholderText("X")
        self.goto_y = QLineEdit(); self.goto_y.setPlaceholderText("Y")
        go_btn = QPushButton("Go"); go_btn.setObjectName("primary")
        go_btn.setFixedWidth(56)
        goto_lay.addWidget(self.goto_x)
        goto_lay.addWidget(self.goto_y)
        goto_lay.addWidget(go_btn)
        go_btn.clicked.connect(self._goto)
        self.goto_x.returnPressed.connect(self._goto)
        self.goto_y.returnPressed.connect(self._goto)
        goto_acc.add_widget(goto_w)

        # ---- 2. DECAY TIMERS ----
        self._idoc_acc = add_section("Decay Timers", expanded=True)
        self._idoc_container = QWidget()
        self._idoc_container.setStyleSheet("background: transparent;")
        self._idoc_cl = QVBoxLayout(self._idoc_container)
        self._idoc_cl.setContentsMargins(10, 4, 10, 8)
        self._idoc_cl.setSpacing(6)
        self._idoc_acc.add_widget(self._idoc_container)

        # ---- 3. PINS ----
        pins_acc = add_section("Pins", expanded=True)
        self.pin_search = QLineEdit()
        self.pin_search.setPlaceholderText("Search pins…")
        self.pin_search.textChanged.connect(self._on_pin_search)
        pins_acc.add_widget(card_pad(self.pin_search))
        self.pin_list = QListWidget()
        self.pin_list.setFixedHeight(190)
        self.pin_list.itemClicked.connect(self._on_pin_list_click)
        pins_acc.add_widget(card_pad(self.pin_list))

        # ---- 4. SELECTED PIN ----
        sel_acc = add_section("Selected Pin", expanded=True)
        self.info_lbl = QLabel("Click a pin or right-click map to drop one",
                               objectName="pin_info")
        self.info_lbl.setWordWrap(True)
        self.info_lbl.setContentsMargins(14, 6, 14, 10)
        sel_acc.add_widget(self.info_lbl)

        # ---- 5. LANDMARKS ----
        lm_acc = add_section("Landmarks", expanded=False)
        self.lm_search = QLineEdit()
        self.lm_search.setPlaceholderText("Search landmarks…")
        self.lm_search.textChanged.connect(self._on_lm_search)
        lm_acc.add_widget(card_pad(self.lm_search))
        self.lm_list = QListWidget()
        self.lm_list.setFixedHeight(160)
        self.lm_list.itemClicked.connect(self._on_lm_click)
        lm_acc.add_widget(card_pad(self.lm_list))

        # ---- 6. DISPLAY ----
        disp_acc = add_section("Display", expanded=False)
        self.show_labels_cb = QCheckBox("Show pin labels")
        self.show_labels_cb.setChecked(True)
        self.show_labels_cb.stateChanged.connect(self._toggle_labels)
        disp_acc.add_widget(card_pad(self.show_labels_cb))

        inner_lay.addStretch()
        splitter.addWidget(sidebar_wrap)
        splitter.setSizes([1160, 280])

        # Status bar
        self.statusBar().setStyleSheet(
            f"QStatusBar {{ padding: 3px 10px; background: #0a0a0c; "
            f"color: {TEXT_DIM}; font-size: 11px; border-top: 1px solid {BORDER}; }}")
        self._status_lbl = QLabel("")
        self.statusBar().addPermanentWidget(self._status_lbl)

        # Floating Reset button — top-left of map
        self._reset_btn = QPushButton("⟳  Reset", self.canvas)
        self._reset_btn.setStyleSheet(f"""
            QPushButton {{
                background: #1c1c1e;
                color: {TEXT_MID};
                border: 1px solid {BORDER};
                border-radius: 7px;
                padding: 6px 14px;
                font-size: 12px;
            }}
            QPushButton:hover {{
                background: {BLUE};
                color: #ffffff;
                border-color: {GOLD};
            }}
        """)
        self._reset_btn.setFixedSize(100, 32)
        self._reset_btn.move(12, 12)
        self._reset_btn.raise_()
        self._reset_btn.clicked.connect(self.canvas.reset_view)

        # Floating decay legend — bottom-right of map
        self._legend_card = QWidget(self.canvas)
        self._legend_card.setStyleSheet(
            "QWidget { background: rgba(20,20,22,200); border: 1px solid rgba(255,255,255,30); "
            "border-radius: 10px; }")
        leg_lay = QVBoxLayout(self._legend_card)
        leg_lay.setContentsMargins(12, 10, 12, 10)
        leg_lay.setSpacing(4)
        hdr_lbl = QLabel("DECAY")
        hdr_lbl.setStyleSheet(
            f"color: {TEXT_DIM}; font-size: 9px; font-weight: 700; letter-spacing: 2px; "
            "background: transparent; border: none;")
        leg_lay.addWidget(hdr_lbl)
        for stage, (fill, _) in DECAY_COLORS.items():
            row_w = QWidget()
            row_w.setStyleSheet("background: transparent; border: none;")
            row_l = QHBoxLayout(row_w)
            row_l.setContentsMargins(0, 0, 0, 0)
            row_l.setSpacing(6)
            dot = QLabel("●")
            dot.setStyleSheet(f"color: {fill}; font-size: 11px; background: transparent; border: none;")
            dot.setFixedWidth(14)
            row_l.addWidget(dot)
            lbl = QLabel(stage)
            lbl.setStyleSheet(f"color: {TEXT_MID}; font-size: 11px; background: transparent; border: none;")
            row_l.addWidget(lbl)
            row_l.addStretch()
            leg_lay.addWidget(row_w)
        self._legend_card.adjustSize()
        self._legend_card.raise_()

        # Keyboard shortcuts
        QAction("Reset", self, shortcut=QKeySequence("R"),
                triggered=self.canvas.reset_view).setParent(self)
        self.addAction(QAction("Reset", self, shortcut=QKeySequence("R"),
                               triggered=self.canvas.reset_view))
        del_action = QAction("Delete", self, shortcut=QKeySequence("Delete"),
                             triggered=self._delete_selected)
        self.addAction(del_action)
        search_action = QAction("Search", self, shortcut=QKeySequence("Ctrl+F"),
                                triggered=lambda: self.pin_search.setFocus())
        self.addAction(search_action)

    def _pad(self, w, h=12, v=4):
        wrap = QWidget()
        wrap.setStyleSheet("background: transparent;")
        l = QHBoxLayout(wrap)
        l.setContentsMargins(h, v, h, v)
        l.addWidget(w)
        return wrap

    # ----------------------------------------------------------------
    # Load data
    # ----------------------------------------------------------------
    def _load(self):
        self._status("Loading map tiles…")
        for scale in (8, 4):
            p = UOAM_BMPS.get(scale)
            if p and os.path.exists(p):
                self._status(f"Loading MAP0-{scale}.BMP…")
                QApplication.processEvents()
                self.canvas.load_tile(scale, p)

        self._status("Loading landmarks…")
        QApplication.processEvents()
        self.landmarks = load_landmarks()
        self.canvas.landmarks = self.landmarks
        self._filtered_lm = self.landmarks[:]
        self._fill_lm_list()

        self._load_pins()
        self._refresh_pin_list()
        self._refresh_idoc_list()

        n = len(self.pins)
        self._status(
            f"{n} pin{'s' if n != 1 else ''}  │  "
            f"Right-click = drop pin  │  Left-click pin = select  │  "
            f"Scroll = zoom  │  Drag = pan  │  Ctrl+F = search"
        )
        self.canvas.reset_view()
        self._legend_card.adjustSize()
        self._reposition_legend()

    def _load_pins(self):
        if os.path.exists(PINS_FILE):
            try:
                with open(PINS_FILE, encoding="utf-8") as f:
                    self.pins = json.load(f)
            except Exception as e:
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(self, "pins.json", f"Could not load: {e}")
                self.pins = []
        else:
            self.pins = []
        # Migrate legacy idoc_set_at field
        for p in self.pins:
            if "decay_set_at" not in p and p.get("idoc_set_at"):
                p["decay_set_at"] = p.pop("idoc_set_at")
        self.canvas.pins = self.pins

    def _save_pins(self):
        with open(PINS_FILE, "w", encoding="utf-8") as f:
            json.dump(self.pins, f, indent=2, ensure_ascii=False)

    def _status(self, msg: str):
        self.statusBar().showMessage(msg)

    # ----------------------------------------------------------------
    # Pin ops
    # ----------------------------------------------------------------
    def _drop_pin(self, tx: float, ty: float):
        dlg = PinDialog(self, int(tx), int(ty))
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_pin:
            self.pins.append(dlg.result_pin)
            self._save_pins()
            self.canvas.selected = dlg.result_pin["id"]
            self._refresh_pin_list()
            self._refresh_idoc_list()
            self._show_pin_info(dlg.result_pin)
            self.canvas._render()

    def _edit_pin(self, pin: dict):
        dlg = PinDialog(self, pin["x"], pin["y"], pin=pin)
        if dlg.exec() == QDialog.DialogCode.Accepted and dlg.result_pin:
            idx = next((i for i, p in enumerate(self.pins)
                        if p["id"] == pin["id"]), None)
            if idx is not None:
                self.pins[idx] = dlg.result_pin
                self._save_pins()
                self._refresh_pin_list()
                self._refresh_idoc_list()
                self._show_pin_info(dlg.result_pin)
                self.canvas._render()

    def _delete_pin(self, pin: dict):
        from PyQt6.QtWidgets import QMessageBox
        label = pin.get("label") or pin["house_type"]
        if QMessageBox.question(self, "Delete pin", f"Delete '{label}'?") \
                != QMessageBox.StandardButton.Yes:
            return
        self.pins = [p for p in self.pins if p["id"] != pin["id"]]
        self.canvas.pins = self.pins
        self._save_pins()
        if self.canvas.selected == pin["id"]:
            self.canvas.selected = None
            self.info_lbl.setText("Click a pin or right-click to drop one")
        self._refresh_pin_list()
        self._refresh_idoc_list()
        self.canvas._render()

    def _delete_selected(self):
        if self.canvas.selected is None:
            return
        pin = next((p for p in self.pins if p["id"] == self.canvas.selected), None)
        if pin:
            self._delete_pin(pin)

    def _select_pin(self, pin: dict):
        self.canvas.selected = pin["id"]
        self._show_pin_info(pin)
        self.canvas._render()

    def _show_pin_info(self, pin: dict):
        lines = [
            f"Label:  {pin.get('label') or '(none)'}",
            f"Type:   {pin['house_type']}",
            f"Decay:  {pin['decay']}",
            f"Tile:   {pin['x']}, {pin['y']}",
        ]
        if pin.get("notes"):
            lines.append(f"Notes:  {pin['notes']}")
        self.info_lbl.setText("\n".join(lines))

    # ----------------------------------------------------------------
    # Canvas signals
    # ----------------------------------------------------------------
    def _on_tile_clicked(self, tx: float, ty: float):
        pin, dist = self.canvas._nearest_pin_at(
            (tx - self.canvas._view_x) * self.canvas._zoom,
            (ty - self.canvas._view_y) * self.canvas._zoom)
        if pin and dist <= MapCanvas.PIN_HIT_PX:
            self._select_pin(pin)

    def _pin_context_menu(self, pin: dict, global_pos):
        menu = QMenu(self)
        label = pin.get("label") or pin["house_type"]
        menu.addAction(f"Edit — {label}", lambda: self._edit_pin(pin))
        menu.addSeparator()
        menu.addAction("Delete", lambda: self._delete_pin(pin))
        menu.exec(global_pos)

    # ----------------------------------------------------------------
    # Pin list
    # ----------------------------------------------------------------
    def _refresh_pin_list(self):
        self._on_pin_search(self.pin_search.text())

    def _on_pin_search(self, q: str):
        q = q.strip().lower()
        self._filtered_pins = [
            p for p in self.pins
            if not q
            or q in (p.get("label") or "").lower()
            or q in p["house_type"].lower()
            or q in p["decay"].lower()
            or q in p.get("notes", "").lower()
        ]
        self.pin_list.clear()
        for p in self._filtered_pins:
            lbl  = p.get("label") or p["house_type"].split()[0]
            item = QListWidgetItem(f"{lbl}  [{p['decay'][:10]}]  ({p['x']},{p['y']})")
            item.setData(Qt.ItemDataRole.UserRole, p["id"])
            self.pin_list.addItem(item)

    def _on_pin_list_click(self, item: QListWidgetItem):
        pid = item.data(Qt.ItemDataRole.UserRole)
        pin = next((p for p in self.pins if p["id"] == pid), None)
        if pin:
            self._select_pin(pin)
            self.canvas.jump_to(pin["x"], pin["y"],
                                zoom=max(self.canvas._zoom, 1.0))

    # ----------------------------------------------------------------
    # IDOC list
    # ----------------------------------------------------------------
    def _refresh_idoc_list(self):
        while self._idoc_cl.count():
            item = self._idoc_cl.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self._idoc_rows = []

        # Sort: IDOC first, then by stage index descending (most decayed first)
        stage_order = {s: i for i, s in enumerate(DECAY_STAGES)}
        sorted_pins = sorted(self.pins,
                             key=lambda p: -stage_order.get(p["decay"], 0))

        if not sorted_pins:
            empty = QLabel("No pins tracked", objectName="idoc_empty")
            empty.setContentsMargins(10, 6, 10, 6)
            self._idoc_cl.addWidget(empty)
            return

        for pin in sorted_pins:
            row = DecayRow(pin)
            row.clicked.connect(lambda p: (self._select_pin(p),
                                           self.canvas.jump_to(p["x"], p["y"],
                                                               zoom=max(self.canvas._zoom, 1.0))))
            self._idoc_cl.addWidget(row)
            self._idoc_rows.append(row)

    def _idoc_tick(self):
        now = time.time()
        for row in self._idoc_rows:
            row.update_timer(now)

    # ----------------------------------------------------------------
    # Landmark list
    # ----------------------------------------------------------------
    def _fill_lm_list(self):
        self.lm_list.clear()
        for name, x, y, cat in self._filtered_lm[:400]:
            self.lm_list.addItem(f"{name}  ({x},{y})")

    def _on_lm_search(self, q: str):
        q = q.strip().lower()
        self._filtered_lm = (
            [lm for lm in self.landmarks
             if q in lm[0].lower() or q in lm[3].lower()]
            if q else self.landmarks[:]
        )
        self._fill_lm_list()

    def _on_lm_click(self, item: QListWidgetItem):
        idx = self.lm_list.row(item)
        if idx < len(self._filtered_lm):
            _, x, y, _ = self._filtered_lm[idx]
            self.canvas.jump_to(x, y, zoom=max(self.canvas._zoom, 0.5))

    # ----------------------------------------------------------------
    # Navigation
    # ----------------------------------------------------------------
    def _goto(self):
        try:
            tx = int(self.goto_x.text())
            ty = int(self.goto_y.text())
            self.canvas.jump_to(tx, ty, zoom=max(self.canvas._zoom, 0.5))
        except ValueError:
            pass

    # ----------------------------------------------------------------
    # Display toggles
    # ----------------------------------------------------------------
    def _toggle_labels(self):
        self.canvas._show_labels = self.show_labels_cb.isChecked()
        self.canvas._render()

    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        self._reposition_legend()

    def _reposition_legend(self):
        ch = self.canvas.height()
        lh = self._legend_card.height()
        self._legend_card.move(14, ch - lh - 14)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    if not os.path.exists(UOAM_BMPS[4]):
        print(f"ERROR: {UOAM_BMPS[4]} not found.")
        sys.exit(1)

    app = QApplication(sys.argv)
    app.setStyleSheet(QSS)
    app.setStyle("Fusion")

    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
