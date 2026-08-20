"""Minimal Qt construction smoke test for the Machine Studio editor shell."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication
from app import MainWindow


def main() -> int:
    application = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    assert window.video_editor_tab.parent() is not window.export_tab
    assert window.legacy_preview_panel.parentWidget() is window.video_editor_tab.horizontal_splitter
    assert window.editor_panel.parentWidget() is window.video_editor_tab.vertical_splitter
    assert window.video_editor_tab.set_tool("audio")
    QTimer.singleShot(250, window.close)
    QTimer.singleShot(350, application.quit)
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
