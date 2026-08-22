from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QProgressBar, QWidget


class TaskProgress(QWidget):
    """Cheap, compact task status with a native thin progress indicator."""
    def __init__(self, parent=None):
        super().__init__(parent); self._value = 0; self._minimum = 0; self._maximum = 100; self.setFixedWidth(240); self.hide()
        layout = QHBoxLayout(self); layout.setContentsMargins(4, 2, 4, 2); layout.setSpacing(8)
        self.label = QLabel("Task"); self.label.setObjectName("hint"); layout.addWidget(self.label)
        self.bar = QProgressBar(); self.bar.setFixedHeight(6); self.bar.setTextVisible(False); layout.addWidget(self.bar, 1)
        self.percent = QLabel("0%"); self.percent.setMinimumWidth(32); layout.addWidget(self.percent)
    def setRange(self, minimum, maximum): self._minimum = int(minimum); self._maximum = int(maximum); self.bar.setRange(minimum, maximum)
    def setTask(self, label): self.label.setText(str(label or "Task")[:24])
    def setValue(self, value):
        raw = int(value); span = self._maximum - self._minimum
        self._value = max(0, min(100, round((raw - self._minimum) * 100 / span))) if span > 0 else 0
        self.bar.setValue(raw); self.percent.setText(f"{self._value}%"); self.show()
        if self._value >= 100: QTimer.singleShot(900, self.hide)
    def value(self): return self._value
