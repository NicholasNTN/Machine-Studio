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
from PySide6.QtGui import QPixmap
from app import MainWindow
from core.ai_styles import AI_STYLES, VOICE_MODE_LABELS
from ui.export_dialog import ExportDialog


def main() -> int:
    application = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    assert window.video_editor_tab.parent() is not window.export_tab
    assert window.legacy_preview_panel.parentWidget() is window.video_editor_tab.horizontal_splitter
    assert window.editor_panel.parentWidget() is window.video_editor_tab.vertical_splitter
    for page in ("media", "voice", "subtitle", "text", "blur", "customize", "advanced", "video_clip"):
        assert window.settings_panel.has_page(page)
    for tool in ("voice", "subtitle", "text", "blur", "customize", "advanced"):
        assert window.video_editor_tab.set_tool(tool)
        assert window.settings_panel.current_page() == tool
    dialog = ExportDialog(QPixmap(), [], window.output_dir.text(), window.resolution.currentText(), window.codec.currentText(), window.encoder.currentText(), parent=window)
    assert dialog.tabs.count() == 4
    dialog.close()
    assert window.undo_shortcut is not None
    assert window.redo_shortcut is not None
    assert window.side_bg_type.findText("Hình ảnh") >= 0
    assert window.context_inspector._controls[("video", "fit_mode")].count() == 2
    assert window.url.placeholderText() == "Paste video link here..."
    headers = [window.script_style.itemText(i) for i in range(window.script_style.count()) if window.script_style.itemData(i) is None]
    assert all(VOICE_MODE_LABELS[mode] in headers for mode in ("single", "dual", "triple", "multi"))
    assert all(style.display_name_vi for style in AI_STYLES)
    window.script_style.setCurrentIndex(window.script_style.findData("before_after"))
    assert len(window.voice_selectors_by_role) == 2
    single = next(style for style in AI_STYLES if style.voice_mode == "single")
    window.script_style.setCurrentIndex(window.script_style.findData(single.id))
    assert len(window.voice_selectors_by_role) == 1
    assert window.analyze_voice_roles_btn is not None
    assert window.video_editor_tab.set_tool("text")
    assert window.settings_panel.current_page() == "text"
    assert window.narration_player.audioOutput() is window.narration_output
    assert window.editor_layer_key_mode.findText("Chroma Key") >= 0
    QTimer.singleShot(250, window.close)
    QTimer.singleShot(350, application.quit)
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
