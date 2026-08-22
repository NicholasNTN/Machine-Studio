"""Offscreen Project Hub and editor lifecycle smoke."""

import sys
import tempfile
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from core.application_controller import ApplicationController
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
        assert controller.editor is None and not controller.hub.isVisible()
        controller.show_project_hub(); qt.processEvents(); assert controller.hub.isVisible()
        record = controller.project_manager.create_project("Lifecycle")
        assert controller.open_project(record.project_path); qt.processEvents()
        assert not controller.hub.isVisible() and controller.editor.isVisible()
        assert Path(controller.editor.workspace_project_path).resolve() == Path(record.project_path).resolve()
        assert controller.editor.project.name == "Lifecycle"
        assert hasattr(controller.editor, "editor_timeline")
        controller.return_to_project_hub(); qt.processEvents()
        assert controller.editor is None and controller.hub.isVisible()
        controller.hub.close()
    print("qt-project-hub-smoke-ok")


if __name__ == "__main__":
    main()
