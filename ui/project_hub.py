from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from PySide6.QtCore import QEvent, QTimer, Qt, Signal
from PySide6.QtGui import QFontMetrics, QMouseEvent, QPixmap
from PySide6.QtWidgets import (
    QComboBox, QDialog, QDialogButtonBox, QFrame, QGridLayout, QHBoxLayout, QLabel,
    QLineEdit, QMainWindow, QMenu, QMessageBox, QScrollArea, QSizePolicy, QVBoxLayout, QWidget,
)

from core.project_manager import ProjectManager, ProjectRecord
from services.thumbnail_service import ThumbnailService
from ui.icons import icon
from ui.theme import apply_theme
from ui.widgets import MachineButton, MachineEmptyState, MachineIconButton, MachineSearchField


def edited_label(value: str) -> str:
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        if moment.tzinfo is None: moment = moment.replace(tzinfo=timezone.utc)
        seconds = max(0, int((datetime.now(timezone.utc) - moment.astimezone(timezone.utc)).total_seconds()))
        if seconds < 60: return "Edited just now"
        if seconds < 3600: return f"Edited {seconds // 60} min ago"
        if seconds < 86400: return f"Edited {seconds // 3600} hr ago"
        if seconds < 172800: return "Edited yesterday"
        return f"Edited {moment.astimezone().strftime('%b %d')}"
    except (TypeError, ValueError):
        return "Edited recently"


class ProjectNameDialog(QDialog):
    def __init__(self, title, value, accept_label, parent=None):
        super().__init__(parent); self.setWindowTitle(title); self.setModal(True); self.setMinimumWidth(390)
        layout = QVBoxLayout(self); layout.setContentsMargins(16, 16, 16, 16); layout.setSpacing(12)
        layout.addWidget(QLabel("Project name:")); self.name = QLineEdit(value); self.name.selectAll(); layout.addWidget(self.name)
        buttons = QDialogButtonBox(); cancel = buttons.addButton("Cancel", QDialogButtonBox.RejectRole); accept = buttons.addButton(accept_label, QDialogButtonBox.AcceptRole); accept.setProperty("variant", "primary")
        cancel.clicked.connect(self.reject); accept.clicked.connect(self._accept); layout.addWidget(buttons); self.name.returnPressed.connect(self._accept)

    def _accept(self):
        if self.name.text().strip(): self.accept()

    @classmethod
    def get_name(cls, title, value, accept_label, parent=None):
        dialog = cls(title, value, accept_label, parent)
        return (dialog.name.text().strip(), True) if dialog.exec() == QDialog.Accepted else (value, False)


class ProjectCard(QFrame):
    openRequested = Signal(str)
    renameRequested = Signal(str)
    deleteRequested = Signal(str)

    def __init__(self, record: ProjectRecord, parent=None):
        super().__init__(parent); self.record = record; self.setObjectName("projectCard"); self.setProperty("selected", False)
        self.setMinimumWidth(180); self.setMaximumWidth(230); self.setFixedHeight(220); self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed); self.setCursor(Qt.PointingHandCursor)
        layout = QVBoxLayout(self); layout.setContentsMargins(8, 8, 8, 8); layout.setSpacing(7)
        self.thumbnail = QLabel(); self.thumbnail.setObjectName("projectThumbnail"); self.thumbnail.setFixedHeight(118); self.thumbnail.setAlignment(Qt.AlignCenter)
        self.thumbnail.setPixmap(icon("editor", "textMuted", 34).pixmap(34, 34)); layout.addWidget(self.thumbnail)
        self.name_label = QLabel(record.name); self.name_label.setObjectName("projectName"); self.name_label.setWordWrap(False); self.name_label.setToolTip(record.name); layout.addWidget(self.name_label)
        self.edited = QLabel(edited_label(record.updated_at)); self.edited.setObjectName("projectMeta"); layout.addWidget(self.edited)
        footer = QHBoxLayout(); footer.setContentsMargins(0, 0, 0, 0)
        count = QLabel(f"{record.media_count} media"); count.setObjectName("projectMeta"); footer.addWidget(count); footer.addStretch(1)
        self.more = MachineIconButton("more", "Project actions"); self.more.setFixedSize(28, 28); self.more.setVisible(False); self.more.clicked.connect(self._show_menu); footer.addWidget(self.more); layout.addLayout(footer)

    @staticmethod
    def context_action_labels(managed=True):
        return ("Open / Edit", "Rename", "Delete Project" if managed else "Remove from Projects")

    def set_thumbnail(self, path: str):
        pixmap = QPixmap(path)
        if pixmap.isNull(): return
        target = self.thumbnail.size(); scaled = pixmap.scaled(target, Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        x = max(0, (scaled.width() - target.width()) // 2); y = max(0, (scaled.height() - target.height()) // 2)
        self.thumbnail.setPixmap(scaled.copy(x, y, target.width(), target.height()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.name_label.setText(QFontMetrics(self.name_label.font()).elidedText(self.record.name, Qt.ElideRight, max(40, self.name_label.width())))

    def enterEvent(self, event): self.more.setVisible(True); super().enterEvent(event)
    def leaveEvent(self, event):
        if not self.more.underMouse(): self.more.setVisible(False)
        super().leaveEvent(event)

    def _show_menu(self):
        menu = QMenu(self); labels = self.context_action_labels(self.record.managed)
        open_action = menu.addAction(labels[0]); rename_action = menu.addAction(labels[1]); menu.addSeparator(); delete_action = menu.addAction(labels[2])
        chosen = menu.exec(self.more.mapToGlobal(self.more.rect().bottomLeft()))
        if chosen == open_action: self.openRequested.emit(self.record.project_path)
        elif chosen == rename_action: self.renameRequested.emit(self.record.project_path)
        elif chosen == delete_action: self.deleteRequested.emit(self.record.project_path)

    def mousePressEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton:
            self.setProperty("selected", True); self.style().unpolish(self); self.style().polish(self)
        super().mousePressEvent(event)

    def mouseDoubleClickEvent(self, event: QMouseEvent):
        if event.button() == Qt.LeftButton: self.openRequested.emit(self.record.project_path)
        super().mouseDoubleClickEvent(event)

    def contextMenuEvent(self, event):
        self._show_menu(); event.accept()


class ProjectHubWindow(QMainWindow):
    createProjectRequested = Signal(str)
    openProjectRequested = Signal(str)
    closeRequested = Signal()

    SORTS = (("Last modified", "modified"), ("Name A–Z", "name_asc"), ("Name Z–A", "name_desc"), ("Created date", "created"))

    def __init__(self, manager: ProjectManager, parent=None):
        super().__init__(parent); self.manager = manager; self.records = []; self.cards = []; self._columns = 0; self._controller_managed = False; self._allow_close = False
        self.setObjectName("projectHub"); self.setWindowTitle("Machine Studio — Projects"); self.resize(1180, 760); self.setMinimumSize(900, 600)
        central = QWidget(); self.setCentralWidget(central); root = QVBoxLayout(central); root.setContentsMargins(24, 20, 24, 20); root.setSpacing(16)
        top = QHBoxLayout(); mark = QLabel(); mark.setPixmap(icon("brand", "accent", 20).pixmap(20, 20)); top.addWidget(mark)
        brand = QLabel("MACHINE STUDIO"); brand.setObjectName("hubBrand"); top.addWidget(brand); top.addStretch(1)
        settings = MachineIconButton("settings", "Settings"); settings.setFixedSize(30, 30); top.addWidget(settings); root.addLayout(top)
        title = QLabel("Projects"); title.setObjectName("hubTitle"); root.addWidget(title)
        subtitle = QLabel("Manage and continue your editing work"); subtitle.setObjectName("hubSubtitle"); root.addWidget(subtitle)
        self.create_button = MachineButton("Create New Project", variant="primary", icon_name="plus"); self.create_button.setObjectName("projectHero"); self.create_button.setFixedHeight(58); self.create_button.clicked.connect(self._request_create); root.addWidget(self.create_button)
        controls = QHBoxLayout(); heading = QLabel("Recent Projects"); heading.setObjectName("hubSectionTitle"); controls.addWidget(heading); controls.addStretch(1)
        self.search = MachineSearchField("Search projects"); self.search.setMaximumWidth(260); self.search.textChanged.connect(self._filter); controls.addWidget(self.search)
        self.sort = QComboBox(); self.sort.setObjectName("projectSort"); self.sort.setMinimumWidth(145)
        for label, value in self.SORTS: self.sort.addItem(label, value)
        stored_sort = self.manager._settings_data.get("project_hub_sort", "modified"); index = self.sort.findData(stored_sort); self.sort.setCurrentIndex(max(0, index)); self.sort.currentIndexChanged.connect(self._sort_changed); controls.addWidget(self.sort); root.addLayout(controls)
        self.scroll = QScrollArea(); self.scroll.setWidgetResizable(True); self.scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff); self.scroll.viewport().installEventFilter(self)
        self.grid_host = QWidget(); self.grid = QGridLayout(self.grid_host); self.grid.setContentsMargins(0, 0, 0, 0); self.grid.setHorizontalSpacing(12); self.grid.setVerticalSpacing(12); self.grid.setAlignment(Qt.AlignTop | Qt.AlignLeft); self.scroll.setWidget(self.grid_host); root.addWidget(self.scroll, 1)
        self.empty = MachineEmptyState("No projects yet", "Create your first Machine Studio project.", "folder", self.grid_host)
        self.empty_button = MachineButton("Create Project", variant="primary", icon_name="plus", parent=self.empty); self.empty.layout().addWidget(self.empty_button, 0, Qt.AlignCenter); self.empty_button.clicked.connect(self._request_create)
        self.thumbnail_service = ThumbnailService(self.manager.root / ".cache" / "project-thumbnails", self); self.thumbnail_service.ready.connect(self._thumbnail_ready)
        apply_theme(self); self.refresh()

    def _request_create(self):
        name, ok = ProjectNameDialog.get_name("Create New Project", "Untitled Project", "Create", self)
        if ok and name.strip(): self.createProjectRequested.emit(name.strip())

    def refresh(self):
        self.records = self.manager.discover_projects(self.sort.currentData() or "modified"); self._filter()

    def _sort_changed(self):
        self.manager._settings_data["project_hub_sort"] = self.sort.currentData(); self.manager._save_settings(); self.refresh()

    def _filter(self):
        query = self.search.text().strip().casefold()
        records = [record for record in self.records if not query or query in record.name.casefold()]
        self._set_records(records)

    def _set_records(self, records):
        for card in self.cards: card.deleteLater()
        self.cards = []
        self.empty.setVisible(not records)
        for record in records:
            card = ProjectCard(record, self.grid_host); card.openRequested.connect(self.openProjectRequested); card.renameRequested.connect(self._rename); card.deleteRequested.connect(self._delete); self.cards.append(card)
            source = record.thumbnail_source
            if source:
                if Path(source).suffix.lower() in (".png", ".jpg", ".jpeg", ".webp", ".bmp"): card.set_thumbnail(source)
                else: self.thumbnail_service.request(source)
        self._columns = 0; self._reflow()

    def _reflow(self):
        width = max(1, self.scroll.viewport().width()); columns = max(1, (width + 12) // (200 + 12))
        if columns == self._columns and all(self.grid.indexOf(card) >= 0 for card in self.cards): return
        self._columns = columns
        while self.grid.count(): self.grid.takeAt(0)
        if not self.cards:
            self.grid.addWidget(self.empty, 0, 0, 1, columns); return
        for index, card in enumerate(self.cards): self.grid.addWidget(card, index // columns, index % columns)
        for column in range(columns): self.grid.setColumnStretch(column, 1)

    def eventFilter(self, watched, event):
        if watched is self.scroll.viewport() and event.type() == QEvent.Resize: QTimer.singleShot(0, self._reflow)
        return super().eventFilter(watched, event)

    def _thumbnail_ready(self, source, thumbnail, _duration):
        for card in self.cards:
            if card.record.thumbnail_source == source: card.set_thumbnail(thumbnail)

    def _rename(self, path):
        record = next((item for item in self.records if item.project_path == path), None)
        if not record: return
        name, ok = ProjectNameDialog.get_name("Rename Project", record.name, "Rename", self)
        if ok and name.strip():
            try: self.manager.rename_project(path, name.strip()); self.refresh()
            except Exception as exc: QMessageBox.critical(self, "Rename Project", str(exc))

    def _delete(self, path):
        record = next((item for item in self.records if item.project_path == path), None)
        if not record: return
        title = "Delete Project" if record.managed else "Remove from Projects"
        detail = "The project editing data will be moved to Project Trash.\nOriginal source media will not be deleted." if record.managed else "The external project file will remain untouched."
        box = QMessageBox(QMessageBox.Warning, title, f'{title} "{record.name}"?\n\n{detail}', parent=self)
        cancel = box.addButton("Cancel", QMessageBox.RejectRole); confirm = box.addButton(title, QMessageBox.AcceptRole); confirm.setProperty("variant", "danger"); box.setDefaultButton(cancel); box.exec()
        if box.clickedButton() == confirm:
            try: self.manager.delete_project(path); self.refresh()
            except Exception as exc: QMessageBox.critical(self, title, str(exc))

    def closeEvent(self, event):
        if self._controller_managed and not self._allow_close:
            event.ignore(); self.closeRequested.emit()
            if self._allow_close: event.accept()
            return
        event.accept()
