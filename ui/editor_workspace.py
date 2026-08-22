from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QButtonGroup, QFrame, QHBoxLayout, QSplitter, QStackedWidget, QVBoxLayout, QWidget
from .widgets import MachineToolButton

from core.last_used_preferences import sanitize_workspace_splitter_sizes


class EditorWorkspace(QWidget):
    splitterSizesChanged = Signal()
    toolSelected = Signal(str)
    TOOLS = (("media", "media", "Media"), ("voice", "voice", "Voice"), ("subtitle", "subtitle", "Phụ đề"), ("text", "text", "Text"), ("blur", "blur", "Blur"), ("customize", "customize", "Tùy chỉnh"), ("advanced", "advanced", "Nâng cao"))

    def __init__(self, pages, preview, inspector, timeline, parent=None):
        super().__init__(parent); root = QVBoxLayout(self); root.setContentsMargins(0, 0, 0, 0)
        self.vertical_splitter = QSplitter(Qt.Vertical); self.vertical_splitter.setChildrenCollapsible(False); self.vertical_splitter.setHandleWidth(6)
        self.horizontal_splitter = QSplitter(Qt.Horizontal); self.horizontal_splitter.setChildrenCollapsible(False); self.horizontal_splitter.setHandleWidth(6)
        left = QFrame(); left.setObjectName("leftWorkspace"); left.setMinimumWidth(300); left_layout = QHBoxLayout(left); left_layout.setContentsMargins(0, 0, 0, 0); left_layout.setSpacing(0)
        nav = QFrame(); nav.setObjectName("toolNav"); nav.setFixedWidth(54); nav_layout = QVBoxLayout(nav); nav_layout.setContentsMargins(3, 8, 3, 8); nav_layout.setSpacing(4)
        self.page_stack = QStackedWidget(); self.page_stack.setMinimumWidth(246)
        self._tool_indexes = {key: index for index, key in enumerate(pages)}
        self._tool_buttons = {}
        for page in pages.values(): self.page_stack.addWidget(page)
        group = QButtonGroup(self); group.setExclusive(True)
        for index, (key, icon_name, label) in enumerate(self.TOOLS):
            button = MachineToolButton(label, icon_name); button.setFixedSize(48, 48); button.clicked.connect(lambda checked=False, i=index, k=key: (self.page_stack.setCurrentIndex(i), self.toolSelected.emit(k))); group.addButton(button); nav_layout.addWidget(button)
            self._tool_buttons[key] = button
            if index == 0: button.setChecked(True)
        nav_layout.addStretch(1); left_layout.addWidget(nav); left_layout.addWidget(self.page_stack, 1)
        preview.setMinimumWidth(420); inspector.setMinimumWidth(340); timeline.setMinimumHeight(220); self.horizontal_splitter.setMinimumHeight(300)
        self.horizontal_splitter.addWidget(left); self.horizontal_splitter.addWidget(preview); self.horizontal_splitter.addWidget(inspector)
        self.horizontal_splitter.setStretchFactor(1, 1); self.vertical_splitter.addWidget(self.horizontal_splitter); self.vertical_splitter.addWidget(timeline); self.vertical_splitter.setStretchFactor(0, 4); self.vertical_splitter.setStretchFactor(1, 2)
        self.horizontal_splitter.setSizes([320, 900, 360]); self.vertical_splitter.setSizes([650, 260])
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
        sizes = sanitize_workspace_splitter_sizes(values)
        self.horizontal_splitter.setSizes(sizes["workspace_horizontal"])
        self.vertical_splitter.setSizes(sizes["workspace_vertical"])
