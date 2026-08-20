from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QStackedWidget, QVBoxLayout, QWidget


class SettingsPanel(QFrame):
    """Tool-driven settings surface containing the existing working controls."""
    def __init__(self, pages, parent=None):
        super().__init__(parent); self.setObjectName("inspectorPanel"); self.setMinimumWidth(340)
        layout = QVBoxLayout(self); layout.setContentsMargins(10, 10, 10, 10)
        title = QLabel("Settings"); title.setObjectName("panelTitle"); layout.addWidget(title)
        self.stack = QStackedWidget(); self._indexes = {}
        for key, content in pages.items():
            scroll = QScrollArea(); scroll.setWidgetResizable(True); holder = QWidget(); body = QVBoxLayout(holder); body.setContentsMargins(4, 4, 4, 4); body.addWidget(content); body.addStretch(1); scroll.setWidget(holder)
            self._indexes[key] = self.stack.addWidget(scroll)
        layout.addWidget(self.stack, 1)

    def set_page(self, key):
        if key not in self._indexes: return False
        self.stack.setCurrentIndex(self._indexes[key]); return True

    def has_page(self, key): return key in self._indexes
    def current_page(self):
        index = self.stack.currentIndex()
        return next((key for key, value in self._indexes.items() if value == index), "")
