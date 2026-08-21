from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QPushButton, QSplitter, QStackedWidget, QVBoxLayout, QWidget


class EditorWorkspace(QWidget):
    splitterSizesChanged = Signal()
    toolSelected = Signal(str)
    TOOLS = (("media", "▣", "Media"), ("voice", "♫", "Voice"), ("subtitle", "CC", "Phụ đề"), ("text", "T", "Text"), ("blur", "◉", "Blur"), ("customize", "◆", "Tùy chỉnh"), ("advanced", "⚙", "Nâng cao"))

    def __init__(self, pages, preview, inspector, timeline, parent=None):
        super().__init__(parent); root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        self.vertical_splitter = QSplitter(Qt.Vertical); self.vertical_splitter.setChildrenCollapsible(False); self.vertical_splitter.setHandleWidth(6)
        self.horizontal_splitter = QSplitter(Qt.Horizontal); self.horizontal_splitter.setChildrenCollapsible(False); self.horizontal_splitter.setHandleWidth(6)
        left = QFrame(); left.setObjectName("leftWorkspace"); left.setMinimumWidth(240); left_layout = QHBoxLayout(left); left_layout.setContentsMargins(0, 0, 0, 0); left_layout.setSpacing(0)
        nav = QFrame(); nav.setObjectName("toolNav"); nav.setFixedWidth(62); nav_layout = QVBoxLayout(nav); nav_layout.setContentsMargins(3, 6, 3, 6); nav_layout.setSpacing(3)
        self.page_stack = QStackedWidget(); self.page_stack.setMinimumWidth(176)
        self._tool_indexes = {key: index for index, key in enumerate(pages)}
        self._tool_buttons = {}
        for page in pages.values(): self.page_stack.addWidget(page)
        group = QButtonGroup(self); group.setExclusive(True)
        for index, (key, icon, label) in enumerate(self.TOOLS):
            button = QPushButton(f"{icon}\n{label}"); button.setObjectName("toolButton"); button.setToolTip(label); button.setCheckable(True); button.setFixedSize(56, 52); button.clicked.connect(lambda checked=False, i=index, k=key: (self.page_stack.setCurrentIndex(i), self.toolSelected.emit(k))); group.addButton(button); nav_layout.addWidget(button)
            self._tool_buttons[key] = button
            if index == 0: button.setChecked(True)
        nav_layout.addStretch(1); left_layout.addWidget(nav); left_layout.addWidget(self.page_stack, 1)
        preview.setMinimumWidth(420); inspector.setMinimumWidth(280); timeline.setMinimumHeight(180)
        self.horizontal_splitter.addWidget(left); self.horizontal_splitter.addWidget(preview); self.horizontal_splitter.addWidget(inspector)
        self.horizontal_splitter.setStretchFactor(1, 1); self.vertical_splitter.addWidget(self.horizontal_splitter); self.vertical_splitter.addWidget(timeline); self.vertical_splitter.setStretchFactor(0, 4); self.vertical_splitter.setStretchFactor(1, 2)
        self.horizontal_splitter.setSizes([300, 900, 320]); self.vertical_splitter.setSizes([650, 300])
        self.horizontal_splitter.splitterMoved.connect(lambda *_: self.splitterSizesChanged.emit()); self.vertical_splitter.splitterMoved.connect(lambda *_: self.splitterSizesChanged.emit()); root.addWidget(self.vertical_splitter)

    def sizes(self): return {"workspace_horizontal": self.horizontal_splitter.sizes(), "workspace_vertical": self.vertical_splitter.sizes()}
    def set_tool(self, key):
        """Switch left tools through the workspace's stable public API."""
        if key not in self._tool_indexes: return False
        self.page_stack.setCurrentIndex(self._tool_indexes[key])
        self._tool_buttons[key].setChecked(True)
        self.toolSelected.emit(key)
        return True
    def restore_sizes(self, values):
        if not isinstance(values, dict): return
        if values.get("workspace_horizontal"): self.horizontal_splitter.setSizes(values["workspace_horizontal"])
        if values.get("workspace_vertical"): self.vertical_splitter.setSizes(values["workspace_vertical"])
