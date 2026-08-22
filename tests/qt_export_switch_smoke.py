"""Offscreen heartbeat smoke for sequence switching during a background Export."""

import sys
import time
from pathlib import Path

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

import app as app_module
from editor.sequence_manager import SequenceManager


def main():
    callback_errors = []
    sys.excepthook = lambda exc_type, exc, tb: callback_errors.append((exc_type, exc))
    app_module.MainWindow.restore_last_project = lambda self: None
    app_module.MainWindow.schedule_autosave = lambda self, *args: None
    original_extract = app_module.ffm.extract_preview_still
    app_module.ffm.extract_preview_still = lambda *args, **kwargs: (time.sleep(1.2) or str(args[1]))

    qt = QApplication.instance() or QApplication([])
    window = app_module.MainWindow()
    manager = SequenceManager(); timeline = manager.active; timeline.name = "Timeline"
    media = str((Path(__file__).resolve().parents[1] / "settings.json").resolve())
    timeline.state = {"editor_use_timeline": True, "editor_clips": [{"id": "a", "path": media,
                      "source_start": 0, "source_end": 2, "source_duration": 2, "enabled": True}]}
    simple = manager.create("Timeline 1")
    simple.state = {"editor_use_timeline": True, "editor_clips": [{"id": "b", "path": media,
                    "source_start": 0, "source_end": 2, "source_duration": 2, "enabled": True}]}
    rich = manager.create("fac")
    rich.state = {"editor_use_timeline": True, "editor_clips": [{"id": "c", "path": media,
                  "source_start": 0, "source_end": 2, "source_duration": 2, "enabled": True,
                  "transform": {"fit_mode": "fit", "position_x": 63, "position_y": 58}}],
                  "narration_path": media, "sub_enabled": True, "preview_cues": [(0, 1, "Subtitle")],
                  "blur_enabled": True, "blur_zones": [{"id": "z", "x": 10, "y": 70, "w": 80, "h": 10}],
                  "subtitle_groups": {"g": {"id": "g", "source_type": "srt", "source_path": media,
                                               "style": {}, "segment_ids": ["g:0"], "visible": True}}}
    manager.activate(timeline.id); window.sequence_manager = manager
    window._sequence_undo_stacks = {item.id: app_module.QUndoStack(window) for item in manager.sequences}
    window.refresh_sequence_tabs(); window.restore_active_sequence()

    heartbeat = [0]
    timer = QTimer(); timer.setInterval(50); timer.timeout.connect(lambda: heartbeat.__setitem__(0, heartbeat[0] + 1)); timer.start()
    # First exercise narration/no-narration replacement without Export.
    before_export = [timeline.id, simple.id, rich.id, timeline.id, rich.id] * 4
    for index, sequence_id in enumerate(before_export):
        QTimer.singleShot(60 + index * 45, lambda sid=sequence_id: window._sequence_tab_changed(sid))

    def start_export_switches():
        worker = app_module.Worker(lambda progress, log: (time.sleep(1.8) or ["synthetic.mp4"]))
        window.export_worker = worker; window._retain_worker(worker); worker.start()
        during_export = [rich.id, timeline.id, simple.id, rich.id] * 3
        for index, sequence_id in enumerate(during_export):
            QTimer.singleShot(index * 65, lambda sid=sequence_id: window._sequence_tab_changed(sid))

    QTimer.singleShot(1100, start_export_switches)
    QTimer.singleShot(3300, qt.quit)
    qt.exec()
    app_module.ffm.extract_preview_still = original_extract
    if heartbeat[0] < 50:
        raise AssertionError(f"GUI heartbeat stalled: {heartbeat[0]}")
    if window.sequence_manager.active_sequence_id != rich.id:
        raise AssertionError("Final rich sequence was not active")
    if callback_errors:
        raise AssertionError(f"Qt callback failed: {callback_errors[0]}")
    print(f"qt-export-switch-heartbeat-ok heartbeats={heartbeat[0]}")


if __name__ == "__main__":
    main()
