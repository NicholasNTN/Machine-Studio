"""Minimal Qt construction smoke test for the Machine Studio editor shell."""
from __future__ import annotations

import os
import sys
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from PySide6.QtCore import QPointF, QTimer
from PySide6.QtGui import QImage
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap
from app import MainWindow
from core.ai_styles import AI_STYLES, VOICE_MODE_LABELS
from ui.export_dialog import ExportDialog
from ui.media_panel import MediaCard


def main() -> int:
    application = QApplication.instance() or QApplication(sys.argv)
    window = MainWindow()
    window.show()
    assert window.video_editor_tab.parent() is not window.export_tab
    assert window.legacy_preview_panel.parentWidget() is window.video_editor_tab.horizontal_splitter
    assert window.editor_panel.parentWidget() is window.video_editor_tab.vertical_splitter
    assert window.video_editor_tab.vertical_splitter.count() == 2
    assert window.video_editor_tab.vertical_splitter.widget(1) is window.editor_panel
    assert window.editor_panel.minimumHeight() >= 180
    window.video_editor_tab.restore_sizes({"workspace_vertical": [900, 0]})
    application.processEvents()
    assert window.video_editor_tab.vertical_splitter.sizes()[1] >= 180
    assert window.editor_panel.isVisible()
    overlay = window.live_overlay; overlay.resize(500, 500); overlay.set_video_image(QImage(1080, 1920, QImage.Format_RGB32))
    overlay.set_blur_state(True, "Trong mờ", 50, [{"x": 40, "y": 40, "w": 20, "h": 20}])
    blur_center = overlay.pct_rect(overlay.blur_zones[0]).center()
    assert overlay.hit_test(blur_center) == ("blur", 0)
    overlay.set_editor_layers([{"id": "text-smoke", "type": "text", "text": "Text", "x": 50, "y": 50, "start": 0, "end": 10}], 1)
    assert overlay.hit_test(overlay.editor_layer_rect(0).center()) == ("editor_layer", 0)
    assert window.text_tool_panel.action_buttons[0].text() == "+ Add Text"
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
    assert len(window.sequence_manager.sequences) == 1
    window.refresh_sequence_tabs()
    assert [button.name_label.text() for button in window.sequence_strip.tab_buttons()] == ["Timeline"]
    assert not window.sequence_strip.tab_buttons()[0]._closable
    first_id = window.sequence_manager.active.id
    window.create_clean_sequence()
    assert len(window.sequence_manager.sequences) == 2
    window.refresh_sequence_tabs()
    assert [button.name_label.text() for button in window.sequence_strip.tab_buttons()] == ["Timeline", "Timeline 1"]
    assert all(button._closable for button in window.sequence_strip.tab_buttons())
    assert window.sequence_strip.plus_button.text() == "+"
    assert window.sequence_manager.active.id != first_id
    assert window.editor_clips == [] and window.preview_loaded_path == ""
    window.create_clean_sequence()
    assert [button.name_label.text() for button in window.sequence_strip.tab_buttons()] == ["Timeline", "Timeline 1", "Timeline 2"]
    window._sequence_tab_changed(first_id)
    assert window.sequence_manager.active.id == first_id
    window.rename_active_sequence("Timeline Smoke")
    duplicate = window.duplicate_sequence()
    assert duplicate.name.endswith("Copy")
    window.sequence_manager.close(duplicate.id); window.refresh_sequence_tabs(); window.restore_active_sequence()
    assert len(window._sequence_undo_stacks) >= 2
    card = MediaCard(str(ROOT / "missing-smoke.mp4"))
    assert card.addRequested is not None and card.removeRequested is not None
    assert "workspace_splitter_sizes" in window.last_used_preferences.values or window.video_editor_tab.sizes()
    assert window.editor_layer_key_mode.findText("Chroma Key") >= 0
    QTimer.singleShot(250, window.close)
    QTimer.singleShot(350, application.quit)
    return application.exec()


if __name__ == "__main__":
    raise SystemExit(main())
