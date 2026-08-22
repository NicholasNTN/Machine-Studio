from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel
from .icons import icon
from .widgets import MachineButton, MachineNavButton


class TopBar(QFrame):
    sectionRequested = Signal(str)
    exportRequested = Signal()

    SECTIONS = (
        ("editor", "editor", "Video Editor"),
        ("ai", "ai", "AI Studio"),
        ("download", "download", "Download"),
        ("settings", "settings", "Settings"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topBar")
        self.setFixedHeight(46)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 3, 8, 3)
        layout.setSpacing(3)

        brand_mark = QLabel(); brand_mark.setObjectName("brandMark"); brand_mark.setPixmap(icon("brand", "accent").pixmap(19, 19)); layout.addWidget(brand_mark)
        brand = QLabel("Machine Studio")
        brand.setObjectName("brandLabel")
        layout.addWidget(brand)
        self.buttons = {}
        for key, icon_name, label in self.SECTIONS:
            button = MachineNavButton(label, icon_name)
            button.setFixedHeight(32)
            button.clicked.connect(lambda checked=False, value=key: self.sectionRequested.emit(value))
            self.buttons[key] = button
            layout.addWidget(button)
        layout.addStretch(1)

        self.saved_dot = QLabel("●"); self.saved_dot.setObjectName("savedDot"); layout.addWidget(self.saved_dot)
        self.project_status = QLabel("Autosaved")
        self.project_status.setObjectName("projectStatus")
        layout.addWidget(self.project_status)
        export = MachineButton("Export", variant="primary", icon_name="export")
        export.setObjectName("topExport")
        export.setFixedHeight(34)
        export.clicked.connect(self.exportRequested)
        layout.addWidget(export)

    def set_active(self, key: str) -> None:
        for name, button in self.buttons.items():
            if button.isCheckable():
                button.setChecked(name == key)

    def set_project_status(self, text: str) -> None:
        self.project_status.setText(str(text))
