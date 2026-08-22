from __future__ import annotations

from enum import Enum

from PySide6.QtCore import QObject

from core.project_manager import ProjectManager
from core.settings_store import SettingsStore
from ui.project_hub import ProjectHubWindow


class ApplicationState(str, Enum):
    PROJECT_HUB = "PROJECT_HUB"
    EDITOR = "EDITOR"
    EXITING = "EXITING"


class ApplicationController(QObject):
    """Owns the lightweight Hub and at most one heavy editor window."""

    def __init__(self, application, root, main_window_factory=None, parent=None):
        super().__init__(parent); self.application = application; self.root = root
        self.application.setQuitOnLastWindowClosed(False); self.state = ApplicationState.PROJECT_HUB
        self.settings = SettingsStore(root); self.project_manager = ProjectManager(root, self.settings)
        self.main_window_factory = main_window_factory; self.hub = ProjectHubWindow(self.project_manager); self.editor = None
        self.hub._controller_managed = True
        self.hub.createProjectRequested.connect(self.create_project); self.hub.openProjectRequested.connect(self.open_project); self.hub.closeRequested.connect(self.close_application)

    def show_project_hub(self):
        if self.state == ApplicationState.EXITING: return
        self.state = ApplicationState.PROJECT_HUB
        self.settings.load(); self.hub.refresh(); self.hub.show(); self.hub.raise_(); self.hub.activateWindow()

    def create_project(self, name):
        record = self.project_manager.create_project(name); self.open_project(record.project_path)

    def _editor_factory(self):
        if self.main_window_factory is not None: return self.main_window_factory
        from app import MainWindow
        return MainWindow

    def open_project(self, path):
        if self.state == ApplicationState.EXITING: return False
        if self.editor is not None:
            self.editor.show(); self.editor.raise_(); self.editor.activateWindow(); return False
        editor = self._editor_factory()(settings_root=self.root)
        editor.returnToProjectsRequested.connect(self.return_to_project_hub)
        if not editor.load_project_file(str(path), show_message=False):
            editor.close(); self.show_project_hub(); return False
        self.project_manager.touch_project(path)
        editor.show(); self.hub.hide(); self.editor = editor; self.state = ApplicationState.EDITOR
        return True

    def return_to_project_hub(self):
        if self.state == ApplicationState.EXITING: return
        editor = self.editor; self.editor = None
        self.show_project_hub()
        if editor is not None: editor.deleteLater()

    def close_application(self):
        if self.state == ApplicationState.EXITING: return
        self.state = ApplicationState.EXITING
        if self.editor is not None:
            self.editor._application_exiting = True; self.editor.close(); self.editor = None
        self.hub._allow_close = True; self.application.quit()
