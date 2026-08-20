from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QWidget


class TaskProgress(QWidget):
    """Compact dark circular task progress shown only while work is active."""
    def __init__(self, parent=None):
        super().__init__(parent); self._value = 0; self._minimum = 0; self._maximum = 100; self._label = "Task"; self.setFixedSize(104, 86); self.hide()
    def setRange(self, minimum, maximum): self._minimum = int(minimum); self._maximum = int(maximum)
    def setTask(self, label): self._label = str(label or "Task")[:16]; self.update()
    def setValue(self, value):
        raw = int(value); span = self._maximum - self._minimum
        self._value = max(0, min(100, round((raw - self._minimum) * 100 / span))) if span > 0 else 0
        self.show(); self.update()
        if self._value >= 100: QTimer.singleShot(900, self.hide)
    def value(self): return self._value
    def paintEvent(self, _event):
        painter = QPainter(self); painter.setRenderHint(QPainter.Antialiasing); rect = self.rect().adjusted(25, 4, -25, -28)
        painter.setPen(QPen(QColor("#263a54"), 6)); painter.drawEllipse(rect)
        painter.setPen(QPen(QColor("#3f8ce8"), 6, Qt.SolidLine, Qt.RoundCap)); painter.drawArc(rect, 90 * 16, -int(360 * 16 * self._value / 100))
        painter.setPen(QColor("#eef5ff")); font = QFont(); font.setBold(True); painter.setFont(font); painter.drawText(rect, Qt.AlignCenter, f"{self._value}%")
        painter.setPen(QColor("#91a6c2")); painter.drawText(self.rect().adjusted(2, 62, -2, -2), Qt.AlignCenter, self._label)
