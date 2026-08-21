from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QLabel, QListWidget, QPushButton, QVBoxLayout, QWidget


class ActionListPanel(QWidget):
    primaryRequested = Signal(); secondaryRequested = Signal(); tertiaryRequested = Signal(); itemSelected = Signal(int); contextMenuRequested = Signal(int, object)

    def __init__(self, title: str, actions: tuple[str, ...], empty_text: str, parent=None):
        super().__init__(parent); self.setObjectName("toolPage")
        layout = QVBoxLayout(self); layout.setContentsMargins(10, 10, 10, 10)
        heading = QLabel(title); heading.setObjectName("panelTitle"); layout.addWidget(heading)
        signals = (self.primaryRequested, self.secondaryRequested, self.tertiaryRequested)
        self.action_buttons = []
        for index, label in enumerate(actions[:3]):
            button = QPushButton(label); button.clicked.connect(signals[index]); layout.addWidget(button); self.action_buttons.append(button)
        self.list = QListWidget(); self.list.setToolTip(empty_text); self.list.currentRowChanged.connect(self.itemSelected)
        self.list.setContextMenuPolicy(Qt.CustomContextMenu); self.list.customContextMenuRequested.connect(lambda pos: self.contextMenuRequested.emit(self.list.indexAt(pos).row(), self.list.viewport().mapToGlobal(pos)))
        layout.addWidget(self.list, 1)

    def set_items(self, labels: list[str]) -> None:
        selected = self.list.currentRow(); self.list.clear(); self.list.addItems(labels)
        if labels and 0 <= selected < len(labels): self.list.setCurrentRow(selected)
