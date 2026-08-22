from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import QMimeData, Qt, QUrl, Signal
from PySide6.QtGui import QDrag, QFontMetrics, QPixmap
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget, QMenu, QInputDialog
from .icons import icon
from .widgets import MachineButton, MachineIconButton, MachinePanelHeader, MachineSearchField


class MediaCard(QFrame):
    selected = Signal(str)
    addRequested = Signal(str)
    renameRequested = Signal(str, str)
    removeRequested = Signal(str)
    revealRequested = Signal(str)

    def __init__(self, path: str, duration: float = 0.0, thumbnail_path: str = "", display_name="", parent=None):
        super().__init__(parent); self.path = str(path); self._press_pos = None; self._full_name = display_name or Path(self.path).name
        self.setObjectName("mediaCard"); self.setProperty("selected", False); self.setCursor(Qt.PointingHandCursor); self.setFixedHeight(62); self.setToolTip(f"{self._full_name}\n{self.path}")
        row = QHBoxLayout(self); row.setContentsMargins(7, 7, 6, 7); row.setSpacing(8)
        self.thumb = QLabel(); self.thumb.setObjectName("mediaThumb"); self.thumb.setAlignment(Qt.AlignCenter); self.thumb.setFixedSize(72, 44)
        self._thumbnail_source = QPixmap(thumbnail_path)
        self._apply_thumbnail()
        row.addWidget(self.thumb)
        details = QVBoxLayout(); details.setContentsMargins(0, 1, 0, 1); details.setSpacing(2)
        self.name_label = QLabel(self._full_name); self.name_label.setWordWrap(False); self.name_label.setObjectName("mediaName"); self.name_label.setToolTip(self._full_name); self.name_label.setMinimumWidth(0); self.name_label.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred); details.addWidget(self.name_label)
        seconds = max(0, int(duration or 0)); duration_text = f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}" if seconds else "00:00"
        extension = Path(self.path).suffix.lstrip(".").upper() or "MEDIA"
        metadata = QLabel(f"{duration_text}  ·  {extension}  ·  VIDEO"); metadata.setObjectName("mediaMetadata"); details.addWidget(metadata)
        row.addLayout(details, 1)
        button = MachineIconButton("plus", "Add to Active Timeline"); button.setObjectName("cardAdd"); button.setFixedSize(26, 26); button.clicked.connect(lambda: self.addRequested.emit(self.path)); row.addWidget(button, 0, Qt.AlignVCenter)

    def resizeEvent(self, event):
        super().resizeEvent(event); width = max(24, self.name_label.width())
        self.name_label.setText(QFontMetrics(self.name_label.font()).elidedText(self._full_name, Qt.ElideRight, width))

    def _apply_thumbnail(self):
        if self._thumbnail_source.isNull():
            self.thumb.setPixmap(icon("play").pixmap(20, 20)); return
        scaled = self._thumbnail_source.scaled(self.thumb.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        x = max(0, (scaled.width() - self.thumb.width()) // 2); y = max(0, (scaled.height() - self.thumb.height()) // 2)
        self.thumb.setPixmap(scaled.copy(x, y, self.thumb.width(), self.thumb.height()))

    def mousePressEvent(self, event):
        self._press_pos = event.position(); self.setProperty("selected", True); self.style().unpolish(self); self.style().polish(self); self.selected.emit(self.path); super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        self.addRequested.emit(self.path); super().mouseDoubleClickEvent(event)

    def mouseMoveEvent(self, event):
        if self._press_pos is not None and (event.position() - self._press_pos).manhattanLength() > 10:
            mime = QMimeData(); mime.setUrls([QUrl.fromLocalFile(self.path)]); drag = QDrag(self); drag.setMimeData(mime); drag.exec(Qt.CopyAction)
        super().mouseMoveEvent(event)

    def contextMenuEvent(self, event):
        menu = QMenu(self); add = menu.addAction("Add to Active Timeline"); rename = menu.addAction("Rename Display Name"); remove = menu.addAction("Remove from Media"); menu.addSeparator(); reveal = menu.addAction("Reveal in Explorer")
        chosen = menu.exec(event.globalPos())
        if chosen == add: self.addRequested.emit(self.path)
        elif chosen == rename:
            value, ok = QInputDialog.getText(self, "Rename Media", "Display name", text=Path(self.path).name)
            if ok and value.strip(): self.renameRequested.emit(self.path, value.strip())
        elif chosen == remove: self.removeRequested.emit(self.path)
        elif chosen == reveal: self.revealRequested.emit(self.path)


class MediaPanel(QWidget):
    addFilesRequested = Signal()
    importFolderRequested = Signal()
    mediaAddRequested = Signal(str)
    mediaSelected = Signal(str)
    mediaRenameRequested = Signal(str, str)
    mediaRemoveRequested = Signal(str)
    mediaRevealRequested = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent); self.setObjectName("toolPage"); self.setMinimumWidth(190); self._paths = []; self._metadata = {}; self._display_names = {}
        layout = QVBoxLayout(self); layout.setContentsMargins(12, 12, 12, 12); layout.setSpacing(6)
        header = MachinePanelHeader("Media", "Project assets"); more = MachineIconButton("more", "Media options"); header.actions.addWidget(more); layout.addWidget(header)
        self.drop_area = QFrame(); self.drop_area.setObjectName("mediaDropArea"); drop = QVBoxLayout(self.drop_area); drop.addStretch(1)
        upload = QLabel(); upload.setPixmap(icon("upload", "textMuted").pixmap(26, 26)); upload.setAlignment(Qt.AlignCenter); drop.addWidget(upload)
        drop_title = QLabel("Import media"); drop_title.setObjectName("emptyTitle"); drop_title.setAlignment(Qt.AlignCenter); drop.addWidget(drop_title)
        hint = QLabel("Drop video, audio, or images here"); hint.setObjectName("hint"); hint.setAlignment(Qt.AlignCenter); drop.addWidget(hint); drop.addStretch(1); self.drop_area.setMinimumHeight(124); layout.addWidget(self.drop_area)
        buttons = QHBoxLayout(); add = MachineButton("Import Media", variant="primary", icon_name="import"); add.clicked.connect(self.addFilesRequested); folder = MachineButton("Folder", icon_name="folder"); folder.setToolTip("Import Folder"); folder.clicked.connect(self.importFolderRequested); buttons.addWidget(add, 1); buttons.addWidget(folder); layout.addLayout(buttons)
        self.search = MachineSearchField("Search media"); self.search.textChanged.connect(self._render); layout.addWidget(self.search)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.cards = QWidget(); self.card_layout = QVBoxLayout(self.cards); self.card_layout.setContentsMargins(0, 0, 0, 0); self.card_layout.setSpacing(5); self.scroll.setWidget(self.cards); layout.addWidget(self.scroll, 1)

    def set_media(self, paths: list[str]) -> None:
        self._paths = list(dict.fromkeys(str(path) for path in paths if path)); self._render()

    def update_media_info(self, path: str, thumbnail_path: str, duration: float) -> None:
        self._metadata[str(path)] = (str(thumbnail_path), float(duration)); self._render()

    def set_display_name(self, path, name): self._display_names[str(path)] = str(name); self._render()

    def _render(self) -> None:
        while self.card_layout.count():
            item = self.card_layout.takeAt(0)
            if item.widget(): item.widget().deleteLater()
        query = self.search.text().strip().lower()
        for path in self._paths:
            if query and query not in Path(path).name.lower(): continue
            thumbnail, duration = self._metadata.get(path, ("", 0.0))
            card = MediaCard(path, duration, thumbnail, self._display_names.get(path, "")); card.selected.connect(self.mediaSelected); card.addRequested.connect(self.mediaAddRequested); card.renameRequested.connect(self.mediaRenameRequested); card.removeRequested.connect(self.mediaRemoveRequested); card.revealRequested.connect(self.mediaRevealRequested); self.card_layout.addWidget(card)
        self.card_layout.addStretch(1); self.drop_area.setVisible(not self._paths)
