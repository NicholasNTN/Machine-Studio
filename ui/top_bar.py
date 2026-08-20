from __future__ import annotations

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QPushButton


class TopBar(QFrame):
    sectionRequested = Signal(str)
    exportRequested = Signal()

    SECTIONS = (
        ("editor", "Video Editor"),
        ("ai", "AI Studio"),
        ("download", "Download"),
        ("settings", "Settings"),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("topBar")
        self.setMinimumHeight(56)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 7, 12, 7)
        layout.setSpacing(5)

        brand = QLabel("MACHINE STUDIO")
        brand.setObjectName("brandLabel")
        layout.addWidget(brand)
        self.buttons = {}
        for key, label in self.SECTIONS:
            button = QPushButton(label)
            button.setObjectName("navButton")
            button.setCheckable(key != "menu")
            button.clicked.connect(lambda checked=False, value=key: self.sectionRequested.emit(value))
            self.buttons[key] = button
            layout.addWidget(button)
        layout.addStretch(1)

        self.project_status = QLabel("Project ready  •  Autosave on")
        self.project_status.setObjectName("projectStatus")
        layout.addWidget(self.project_status)
        export = QPushButton("Export")
        export.setObjectName("topExport")
        export.clicked.connect(self.exportRequested)
        layout.addWidget(export)

    def set_active(self, key: str) -> None:
        for name, button in self.buttons.items():
            if button.isCheckable():
                button.setChecked(name == key)

    def set_project_status(self, text: str) -> None:
        self.project_status.setText(str(text))
