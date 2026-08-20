from PySide6.QtWidgets import QVBoxLayout, QWidget


class TimelinePanel(QWidget):
    def __init__(self, timeline=None, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(180)
        layout = QVBoxLayout(self)
        if timeline is not None:
            layout.addWidget(timeline)
