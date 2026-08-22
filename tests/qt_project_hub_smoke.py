"""Offscreen Project Hub and editor lifecycle smoke."""

import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.application_controller import ApplicationController, ApplicationState
from core.models import AIProject
from core.project_manager import ProjectManager
from ui.project_hub import ProjectCard, ProjectHubWindow


def main():
    qt = QApplication.instance() or QApplication([])
    with tempfile.TemporaryDirectory() as folder:
        test_root = Path(folder); settings = {"recent_project_paths": []}; manager = ProjectManager(test_root, settings)
        alpha = manager.create_project("Alpha Factory"); beta = manager.create_project("Beta Machines"); gamma = manager.create_project("Gamma Line")
        hub = ProjectHubWindow(manager); hub.resize(1180, 760); hub.show(); qt.processEvents()
        assert hub.create_button.isVisible()
        assert len(hub.cards) == 3 and hub._columns >= 3
        for width, height in ((1366, 768), (1600, 900), (1920, 1080), (2560, 1440)):
            hub.resize(width, height); qt.processEvents()
            assert hub._columns >= 4 and hub.scroll.horizontalScrollBar().maximum() == 0
        hub.search.setText("beta"); qt.processEvents(); assert [card.record.name for card in hub.cards] == ["Beta Machines"]
        hub.search.clear(); qt.processEvents(); assert len(hub.cards) == 3
        assert ProjectCard.context_action_labels(True) == ("Open / Edit", "Rename", "Delete Project")
        assert ProjectCard.context_action_labels(False)[-1] == "Remove from Projects"
        opened = []; hub.openProjectRequested.connect(opened.append)
        QTest.mouseDClick(hub.cards[0], Qt.LeftButton); assert opened
        original_folder = Path(beta.project_path).parent
        manager.rename_project(beta.project_path, "Beta Renamed"); hub.refresh(); qt.processEvents()
        assert any(card.record.name == "Beta Renamed" for card in hub.cards)
        assert Path(beta.project_path).parent == original_folder
        manager.delete_project(gamma.project_path); hub.refresh(); qt.processEvents(); assert len(hub.cards) == 2
        external = test_root / "external-projects"; external.mkdir()
        for index in range(48):
            path = external / f"project-{index}.json"; AIProject(name=f"Simulated {index:02d}").save(path); manager.register_project(path)
        hub.refresh(); qt.processEvents(); assert len(hub.cards) == 50
        hub.close()

        controller = ApplicationController(qt, test_root)
        assert controller.editor is None and not controller.hub.isVisible() and controller.state == ApplicationState.PROJECT_HUB
        assert not qt.quitOnLastWindowClosed()
        controller.show_project_hub(); qt.processEvents(); assert controller.hub.isVisible()
        cycle_records = [controller.project_manager.create_project(name) for name in ("Lifecycle A", "Lifecycle B", "Lifecycle C")]
        editor_type = None
        for record in cycle_records:
            assert controller.open_project(record.project_path); qt.processEvents()
            editor = controller.editor; editor_type = type(editor)
            assert controller.state == ApplicationState.EDITOR
            assert not controller.hub.isVisible() and editor.isVisible()
            assert Path(editor.workspace_project_path).resolve() == Path(record.project_path).resolve()
            assert editor.project.name == record.name and hasattr(editor, "editor_timeline")
            assert sum(isinstance(widget, editor_type) and widget.isVisible() for widget in qt.topLevelWidgets()) == 1
            editor.close(); qt.processEvents(); QCoreApplication.sendPostedEvents(None, QEvent.DeferredDelete); qt.processEvents()
            assert controller.editor is None and controller.hub.isVisible()
            assert controller.state == ApplicationState.PROJECT_HUB and not qt.closingDown()
            refreshed = next(card for card in controller.hub.cards if card.record.project_path == record.project_path)
            assert refreshed.edited.text() == "Edited just now"
            assert not any(isinstance(widget, editor_type) and widget.isVisible() for widget in qt.topLevelWidgets())
        controller.hub.close(); qt.processEvents()
        assert controller.state == ApplicationState.EXITING and not controller.hub.isVisible()
    print("qt-project-hub-smoke-ok")


if __name__ == "__main__":
    main()
