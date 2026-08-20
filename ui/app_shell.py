from __future__ import annotations

from PySide6.QtWidgets import QVBoxLayout, QWidget

from .top_bar import TopBar


class AppShell(QWidget):
    """Stable outer chrome; feature panels can migrate independently."""

    def __init__(self, content: QWidget, parent=None):
        super().__init__(parent)
        self.setObjectName("appShell")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        self.top_bar = TopBar(self)
        layout.addWidget(self.top_bar)
        layout.addWidget(content, 1)
