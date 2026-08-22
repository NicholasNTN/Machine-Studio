"""Offscreen responsive timeline viewport and manual-zoom smoke."""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication, QScrollArea

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from editor_timeline import BasicTimelineWidget


def clip(name, duration):
    return {"name": name, "source_start": 0.0, "source_end": float(duration), "source_duration": float(duration), "enabled": True}


def main():
    qt = QApplication.instance() or QApplication([])
    scroll = QScrollArea(); scroll.setWidgetResizable(False); timeline = BasicTimelineWidget(); scroll.setWidget(timeline)
    timeline.attach_viewport(scroll.viewport()); timeline.set_clips([clip("A", 60), clip("B", 25)])
    scroll.resize(900, 150); scroll.show(); qt.processEvents()
    narrow_duration = timeline.visible_duration
    assert timeline.auto_fit and timeline._clip_rects()[-1].right() < timeline.width()

    scroll.resize(1500, 150); qt.processEvents()
    assert timeline.visible_duration > narrow_duration
    wide_duration = timeline.visible_duration
    assert timeline._clip_rects()[-1].right() < timeline.width()

    timeline.set_zoom(30, user_modified=True); manual_zoom = timeline.zoom
    scroll.resize(1100, 150); qt.processEvents()
    assert not timeline.auto_fit and timeline.zoom == manual_zoom
    assert scroll.horizontalScrollBar().maximum() > 0
    print(f"qt-timeline-responsive-ok narrow={narrow_duration:.2f} wide={wide_duration:.2f}")


if __name__ == "__main__":
    main()
