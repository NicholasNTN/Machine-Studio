from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from .top_bar import TopBar
from .widgets import MachineToast


class AppShell(QWidget):
    """Stable outer chrome; feature panels can migrate independently."""

    def __init__(self, content: QWidget, parent=None):
        super().__init__(parent)
        self.setObjectName("appShell")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(6)
        self.top_bar = TopBar(self)
        layout.addWidget(self.top_bar)
        layout.addWidget(content, 1)
        self.toast = MachineToast(self)

    def show_toast(self, message, timeout=2800):
        self.toast.showMessage(message, timeout)
        self.toast.move(max(12, self.width() - self.toast.width() - 20), 58)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.toast.isVisible():
            self.toast.move(max(12, self.width() - self.toast.width() - 20), 58)
