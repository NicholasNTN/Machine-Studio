from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import QObject, QTimer, Signal


class AutosaveService(QObject):
    statusChanged = Signal(str)

    def __init__(self, save_callback: Callable[[], None], delay_ms: int = 700, parent=None):
        super().__init__(parent)
        self._save_callback = save_callback
        self.timer = QTimer(self)
        self.timer.setSingleShot(True)
        self.timer.setInterval(delay_ms)
        self.timer.timeout.connect(self._save)

    def schedule(self) -> None:
        self.statusChanged.emit("Saving…")
        self.timer.start()

    def _save(self) -> None:
        self._save_callback()
        self.statusChanged.emit("Autosaved")
