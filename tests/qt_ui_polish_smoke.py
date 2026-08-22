"""Offscreen interaction smoke for the polished Machine Studio workspace."""

import sys
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as app_module
from ui.export_dialog import ExportDialog
from ui.icons import REQUIRED_ICONS, icon, icon_path
from ui.media_panel import MediaCard


def main():
    callback_errors = []
    sys.excepthook = lambda exc_type, exc, tb: callback_errors.append((exc_type, exc))
    app_module.MainWindow.restore_last_project = lambda self: None
    app_module.MainWindow.schedule_autosave = lambda self, *args: None
    qt = QApplication.instance() or QApplication([])
    window = app_module.MainWindow(); window.show()
    for name in REQUIRED_ICONS:
        assert icon_path(name).is_file(), f"missing SVG: {name}"
        assert not icon(name).isNull(), f"null QIcon: {name}"

    for section in ("ai", "download", "settings", "editor"):
        window._open_top_section(section)
    for tool in ("media", "voice", "subtitle", "text", "blur", "customize", "advanced"):
        assert window.video_editor_tab.set_tool(tool)
        assert window.settings_panel.current_page() == tool

    first = window.sequence_manager.active
    second = window.sequence_manager.create("UI Smoke")
    window.refresh_sequence_tabs()
    window._sequence_tab_changed(second.id); window._sequence_tab_changed(first.id)

    card = MediaCard(str(ROOT / "sample.mp4"), 65.0, "", "Sample clip")
    assert card.path.endswith("sample.mp4")
    dialog = ExportDialog(QPixmap(), [card.path], ROOT / "exports", "1920x1080 (YouTube)", "H.264", "CPU")
    assert dialog.name.text() == "Machine_Export"
    dialog.show(); dialog.reject()
    window.app_shell.show_toast("UI smoke ready", 500)

    heartbeat = [0]
    timer = QTimer(); timer.setInterval(40); timer.timeout.connect(lambda: heartbeat.__setitem__(0, heartbeat[0] + 1)); timer.start()
    QTimer.singleShot(500, qt.quit); qt.exec()
    if heartbeat[0] < 8: raise AssertionError(f"UI heartbeat stalled: {heartbeat[0]}")
    if callback_errors: raise AssertionError(f"Qt callback failed: {callback_errors[0]}")
    print(f"qt-ui-polish-smoke-ok heartbeats={heartbeat[0]}")


if __name__ == "__main__":
    main()
