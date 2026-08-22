from __future__ import annotations

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QStyle
from .theme import tokens

try:
    import qtawesome as qta
except ImportError:  # Optional at runtime; packaged/legacy installs still start.
    qta = None


_NAMES = {
    "brand": "fa5s.play-circle", "editor": "fa5s.cut", "ai": "fa5s.magic",
    "download": "fa5s.download", "settings": "fa5s.cog", "media": "fa5s.photo-video",
    "voice": "fa5s.microphone", "subtitle": "fa5s.closed-captioning", "text": "fa5s.font",
    "blur": "fa5s.low-vision", "customize": "fa5s.sliders-h", "advanced": "fa5s.tools",
    "export": "fa5s.file-export", "plus": "fa5s.plus", "trash": "fa5s.trash-alt",
    "folder": "fa5s.folder-open", "search": "fa5s.search", "play": "fa5s.play",
    "pause": "fa5s.pause", "close": "fa5s.times", "upload": "fa5s.cloud-upload-alt",
}

_FALLBACK = {
    "folder": QStyle.SP_DirOpenIcon, "trash": QStyle.SP_TrashIcon,
    "play": QStyle.SP_MediaPlay, "pause": QStyle.SP_MediaPause,
    "close": QStyle.SP_DockWidgetCloseButton, "plus": QStyle.SP_FileIcon,
    "download": QStyle.SP_ArrowDown, "export": QStyle.SP_DialogSaveButton,
}


def icon(name: str, color=None) -> QIcon:
    palette = tokens()["color"]
    color = palette.get(color, color) if color else palette["textSecondary"]
    if qta is not None:
        try:
            return qta.icon(_NAMES.get(name, "fa5s.circle"), color=color)
        except Exception:
            pass
    app = QApplication.instance()
    return app.style().standardIcon(_FALLBACK.get(name, QStyle.SP_FileIcon)) if app else QIcon()
