from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class MediaPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(240)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Media panel foundation"))
