from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import QMimeData, Qt, QUrl, Signal
from PySide6.QtGui import QDrag, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QLineEdit, QPushButton, QScrollArea, QVBoxLayout, QWidget


class MediaCard(QFrame):
    selected = Signal(str)
    addRequested = Signal(str)

    def __init__(self, path: str, duration: float = 0.0, thumbnail_path: str = "", parent=None):
        super().__init__(parent); self.path = str(path); self._press_pos = None
        self.setObjectName("mediaCard"); self.setCursor(Qt.PointingHandCursor); self.setMinimumHeight(78)
        row = QHBoxLayout(self); row.setContentsMargins(7, 7, 7, 7)
        thumb = QLabel("▶"); thumb.setObjectName("mediaThumb"); thumb.setAlignment(Qt.AlignCenter); thumb.setFixedSize(74, 54)
        pixmap = QPixmap(thumbnail_path)
        if not pixmap.isNull(): thumb.setPixmap(pixmap.scaled(74, 54, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        row.addWidget(thumb)
        text = QVBoxLayout(); name = QLabel(Path(self.path).name); name.setWordWrap(True); name.setObjectName("mediaName"); text.addWidget(name)
        seconds = max(0, int(duration or 0)); duration_label = QLabel(f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}" if seconds else "Video media")
        duration_label.setObjectName("hint"); text.addWidget(duration_label); row.addLayout(text, 1)
        button = QPushButton("+"); button.setObjectName("cardAdd"); button.setFixedSize(28, 28); button.clicked.connect(lambda: self.addRequested.emit(self.path)); row.addWidget(button)

    def mousePressEvent(self, event):
        self._press_pos = event.position(); self.selected.emit(self.path); super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.addRequested.emit(self.path); super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos is not None and (event.position() - self._press_pos).manhattanLength() > 10:
            mime = QMimeData(); mime.setUrls([QUrl.fromLocalFile(self.path)]); drag = QDrag(self); drag.setMimeData(mime); drag.exec(Qt.CopyAction)
        super().mouseMoveEvent(event)


class MediaPanel(QWidget):
    addFilesRequested = Signal()
    importFolderRequested = Signal()
    mediaAddRequested = Signal(str)
    mediaSelected = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent); self.setObjectName("toolPage"); self.setMinimumWidth(240); self._paths = []; self._metadata = {}
        layout = QVBoxLayout(self); layout.setContentsMargins(10, 10, 10, 10)
        title = QLabel("Media"); title.setObjectName("panelTitle"); layout.addWidget(title)
        self.drop_area = QFrame(); self.drop_area.setObjectName("mediaDropArea"); drop = QVBoxLayout(self.drop_area); drop.addStretch(1)
        drop_title = QLabel("Import media"); drop_title.setObjectName("emptyTitle"); drop_title.setAlignment(Qt.AlignCenter); drop.addWidget(drop_title)
        hint = QLabel("Drag video here"); hint.setObjectName("hint"); hint.setAlignment(Qt.AlignCenter); drop.addWidget(hint); drop.addStretch(1); self.drop_area.setMinimumHeight(112); layout.addWidget(self.drop_area)
        buttons = QHBoxLayout(); add = QPushButton("+ Add Media"); add.clicked.connect(self.addFilesRequested); folder = QPushButton("Import Folder"); folder.clicked.connect(self.importFolderRequested); buttons.addWidget(add); buttons.addWidget(folder); layout.addLayout(buttons)
        self.search = QLineEdit(); self.search.setPlaceholderText("Search media"); self.search.textChanged.connect(self._render); layout.addWidget(self.search)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.cards = QWidget(); self.card_layout = QVBoxLayout(self.cards); self.card_layout.setContentsMargins(0, 0, 0, 0); self.scroll.setWidget(self.cards); layout.addWidget(self.scroll, 1)

    def set_media(self, paths: list[str]) -> None:
        self._paths = list(dict.fromkeys(str(path) for path in paths if path)); self._render()

    def update_media_info(self, path: str, thumbnail_path: str, duration: float) -> None:
        self._metadata[str(path)] = (str(thumbnail_path), float(duration)); self._render()

    def _render(self) -> None:
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        query = self.search.text().strip().lower()
        for path in self._paths:
            if query and query not in Path(path).name.lower(): continue
            thumbnail, duration = self._metadata.get(path, ("", 0.0))
            card = MediaCard(path, duration, thumbnail); card.selected.connect(self.mediaSelected); card.addRequested.connect(self.mediaAddRequested); self.card_layout.addWidget(card)
        self.card_layout.addStretch(1); self.drop_area.setVisible(not self._paths)
