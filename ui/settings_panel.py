from PySide6.QtWidgets import QFrame, QLabel, QScrollArea, QStackedWidget, QVBoxLayout, QWidget


class SettingsPanel(QFrame):
    """Tool-driven settings surface containing the existing working controls."""
    TITLES = {"media": ("Media", "Clip and library details"), "voice": ("Voice", "Narration and audio preview"), "subtitle": ("Phụ đề", "Subtitle content and appearance"), "text": ("Text", "Manual text layer properties"), "blur": ("Blur", "Detection and blur zones"), "customize": ("Tùy chỉnh", "Logo, speed, and canvas"), "advanced": ("Nâng cao", "Background and overlay controls"), "video_clip": ("Video", "Selected clip properties")}
    def __init__(self, pages, parent=None):
        super().__init__(parent); self.setObjectName("inspectorPanel"); self.setMinimumWidth(340)
        layout = QVBoxLayout(self); layout.setContentsMargins(12, 12, 12, 12); layout.setSpacing(8)
        self.title = QLabel("Media"); self.title.setObjectName("panelTitle"); layout.addWidget(self.title)
        self.description = QLabel("Clip and library details"); self.description.setObjectName("panelDescription"); self.description.setWordWrap(True); layout.addWidget(self.description)
        self.stack = QStackedWidget(); self._indexes = {}
        for key, content in pages.items():
            if key == "video_clip":
                self._indexes[key] = self.stack.addWidget(content)
            else:
                scroll = QScrollArea(); scroll.setWidgetResizable(True); holder = QWidget(); body = QVBoxLayout(holder); body.setContentsMargins(4, 4, 4, 4); body.addWidget(content); body.addStretch(1); scroll.setWidget(holder)
                self._indexes[key] = self.stack.addWidget(scroll)
        layout.addWidget(self.stack, 1)

    def set_page(self, key):
        if key not in self._indexes: return False
        self.stack.setCurrentIndex(self._indexes[key])
        title, description = self.TITLES.get(key, (key.replace("_", " ").title(), ""))
        self.title.setText(title); self.description.setText(description); return True

    def has_page(self, key): return key in self._indexes
    def current_page(self):
        index = self.stack.currentIndex()
        return next((key for key, value in self._indexes.items() if value == index), "")
