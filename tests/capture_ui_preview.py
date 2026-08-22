"""Capture representative offscreen UI previews for developer review."""

import sys
import tempfile
from pathlib import Path

from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as app_module


def main():
    app_module.MainWindow.restore_last_project = lambda self: None
    app_module.MainWindow.schedule_autosave = lambda self, *args: None
    qt = QApplication.instance() or QApplication([])
    window = app_module.MainWindow()
    window.media_panel.set_media([
        str(ROOT / "Long factory production filename that should elide cleanly.mp4"),
        str(ROOT / "Interview Voice and Subtitle.mp4"),
    ])
    window.sequence_manager.create("Interview"); window.sequence_manager.create("Social Cut")
    window.refresh_sequence_tabs(); window.settings_panel.set_page("video_clip")
    window.context_inspector.stack.setCurrentWidget(window.context_inspector.pages["video"])
    output = Path(tempfile.gettempdir()) / "machine_studio_ui_previews"; output.mkdir(parents=True, exist_ok=True)
    for width, height in ((1920, 1080), (1600, 900), (1366, 768)):
        window.resize(width, height); window.show(); qt.processEvents()
        path = output / f"machine-studio-{width}x{height}.png"
        if not window.grab().save(str(path)): raise RuntimeError(f"Could not save {path}")
        print(path)
    window.close()


if __name__ == "__main__":
    main()
