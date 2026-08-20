from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class InspectorPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(260)
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel("Select an item to edit its properties."))
