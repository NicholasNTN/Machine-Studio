from PySide6.QtWidgets import QVBoxLayout, QWidget


class PreviewPanel(QWidget):
    def __init__(self, canvas=None, parent=None):
        super().__init__(parent)
        self.setMinimumSize(420, 260)
        layout = QVBoxLayout(self)
        if canvas is not None:
            layout.addWidget(canvas)
