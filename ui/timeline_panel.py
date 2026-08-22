from PySide6.QtWidgets import QVBoxLayout, QWidget


class TimelinePanel(QWidget):
    def __init__(self, timeline=None, parent=None):
        super().__init__(parent)
        self.setObjectName("timelineSurface")
        self.setMinimumHeight(180)
        layout = QVBoxLayout(self); layout.setContentsMargins(8, 6, 8, 8)
        if timeline is not None:
            layout.addWidget(timeline)
