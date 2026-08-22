from __future__ import annotations

import warnings
from functools import lru_cache
from pathlib import Path

from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

from .theme import tokens


ICON_ROOT = Path(__file__).resolve().parents[1] / "assets" / "icons" / "tabler"
_FILES = {
    "brand": "movie", "editor": "timeline", "ai": "sparkles", "download": "download",
    "settings": "settings", "export": "file-export", "media": "photo-video",
    "voice": "microphone", "subtitle": "captions", "text": "typography", "blur": "blur",
    "customize": "adjustments", "advanced": "tools", "import": "file-plus",
    "folder": "folder-open", "search": "search", "plus": "plus", "trash": "trash",
    "undo": "arrow-back-up", "redo": "arrow-forward-up", "split": "cut",
    "range": "brackets", "play": "player-play", "pause": "player-pause",
    "previous": "player-skip-back", "next": "player-skip-forward", "zoom_in": "zoom-in",
    "zoom_out": "zoom-out", "close": "x", "upload": "upload", "more": "dots",
    "lock": "lock", "visible": "eye", "hidden": "eye-off", "volume": "volume",
    "muted": "volume-off", "reset": "refresh", "chevron": "chevron-down",
}

REQUIRED_ICONS = tuple(_FILES)


def icon_path(name: str) -> Path:
    return ICON_ROOT / f"{_FILES.get(name, name)}.svg"


@lru_cache(maxsize=256)
def _pixmap(name: str, color: str, size: int) -> QPixmap:
    path = icon_path(name)
    if not path.is_file():
        warnings.warn(f"Machine Studio icon missing: {name} ({path})", RuntimeWarning)
        return QPixmap()
    try:
        svg = path.read_text(encoding="utf-8").replace("currentColor", color)
        renderer = QSvgRenderer(QByteArray(svg.encode("utf-8")))
        if not renderer.isValid():
            raise ValueError("invalid SVG")
        pixmap = QPixmap(size, size); pixmap.fill(Qt.transparent)
        painter = QPainter(pixmap); renderer.render(painter); painter.end()
        return pixmap
    except (OSError, ValueError) as exc:
        warnings.warn(f"Machine Studio icon failed to load: {name} ({exc})", RuntimeWarning)
        return QPixmap()


def machine_icon(name: str, color=None, size=None) -> QIcon:
    palette = tokens()["color"]
    resolved = palette.get(color, color) if color else palette["textSecondary"]
    return QIcon(_pixmap(name, str(resolved), int(size or 20)))


def machine_pixmap(name: str, color=None, size=None) -> QPixmap:
    palette = tokens()["color"]
    resolved = palette.get(color, color) if color else palette["textSecondary"]
    return _pixmap(name, str(resolved), int(size or 20))


icon = machine_icon
