from __future__ import annotations

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QToolButton, QWidget


class SequenceTabButton(QWidget):
    """Compact sequence selector with a close affordance visible on hover."""

    activated = Signal(str)
    closeRequested = Signal(str)
    contextMenuRequested = Signal(str, QPoint)

    def __init__(self, sequence_id: str, name: str, active=False, closable=True, parent=None):
        super().__init__(parent)
        self.sequence_id = sequence_id
        self.setProperty("active", bool(active))
        self.setObjectName("sequenceTabButton")
        self.setFixedHeight(26)
        self.setCursor(Qt.PointingHandCursor)

        row = QHBoxLayout(self)
        row.setContentsMargins(8, 0, 4, 0)
        row.setSpacing(3)
        self.name_label = QLabel(name)
        self.name_label.setAttribute(Qt.WA_TransparentForMouseEvents)
        row.addWidget(self.name_label)
        self.close_button = QToolButton(self)
        self.close_button.setObjectName("sequenceTabClose")
        self.close_button.setText("×")
        self.close_button.setToolTip(f"Close {name}")
        self.close_button.setAutoRaise(True)
        self.close_button.setFixedSize(18, 18)
        self.close_button.setCursor(Qt.PointingHandCursor)
        self.close_button.clicked.connect(lambda: self.closeRequested.emit(self.sequence_id))
        self.close_button.setVisible(False)
        self._closable = bool(closable)
        row.addWidget(self.close_button)

    def enterEvent(self, event):
        self.close_button.setVisible(self._closable)
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.close_button.hide()
        super().leaveEvent(event)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.activated.emit(self.sequence_id)
            event.accept()
            return
        if event.button() == Qt.RightButton:
            self.contextMenuRequested.emit(self.sequence_id, event.globalPosition().toPoint())
            event.accept()
            return
        super().mousePressEvent(event)


class SequenceTabStrip(QWidget):
    """Integrated Timeline header containing real sequences and an inline + action."""

    sequenceActivated = Signal(str)
    newSequenceRequested = Signal()
    closeSequenceRequested = Signal(str)
    contextMenuRequested = Signal(str, QPoint)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sequenceTabStrip")
        self.setFixedHeight(28)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(2)
        self.plus_button = QToolButton(self)
        self.plus_button.setObjectName("sequenceTabPlus")
        self.plus_button.setText("+")
        self.plus_button.setToolTip("New Timeline")
        self.plus_button.setAutoRaise(True)
        self.plus_button.setFixedSize(24, 24)
        self.plus_button.setCursor(Qt.PointingHandCursor)
        self.plus_button.clicked.connect(self.newSequenceRequested.emit)
        self._layout.addWidget(self.plus_button)
        self._layout.addStretch(1)

    def set_sequences(self, sequences, active_sequence_id: str):
        while self._layout.count():
            item = self._layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        count = len(sequences)
        for sequence in sequences:
            button = SequenceTabButton(
                sequence.id, sequence.name, sequence.id == active_sequence_id,
                closable=count > 1, parent=self,
            )
            button.activated.connect(self.sequenceActivated)
            button.closeRequested.connect(self.closeSequenceRequested)
            button.contextMenuRequested.connect(self.contextMenuRequested)
            self._layout.addWidget(button)
        self.plus_button = QToolButton(self)
        self.plus_button.setObjectName("sequenceTabPlus")
        self.plus_button.setText("+")
        self.plus_button.setToolTip("New Timeline")
        self.plus_button.setAutoRaise(True)
        self.plus_button.setFixedSize(24, 24)
        self.plus_button.setCursor(Qt.PointingHandCursor)
        self.plus_button.clicked.connect(self.newSequenceRequested.emit)
        self._layout.addWidget(self.plus_button)
        self._layout.addStretch(1)

    def tab_buttons(self):
        return [
            self._layout.itemAt(index).widget()
            for index in range(self._layout.count())
            if isinstance(self._layout.itemAt(index).widget(), SequenceTabButton)
        ]
