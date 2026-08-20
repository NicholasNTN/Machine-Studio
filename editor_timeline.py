from __future__ import annotations

from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import QWidget

from core import editor_engine


class BasicTimelineWidget(QWidget):
    clipSelected = Signal(int)
    clipTrimChanged = Signal(int, float, float)
    clipReordered = Signal(int, int)
    playheadChanged = Signal(float)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.clips: list[dict] = []
        self.zoom = 24.0
        self.selected_index = -1
        self.playhead = 0.0
        self.drag_mode = ""
        self.press_pos = QPointF()
        self.drag_index = -1
        self.temp_start = None
        self.temp_end = None
        self.setMinimumHeight(118)
        self.setMouseTracking(True)

    def set_clips(self, clips):
        self.clips = [dict(c) for c in clips]
        if self.selected_index >= len(self.clips):
            self.selected_index = len(self.clips) - 1
        self._update_width()
        self.update()

    def set_zoom(self, value):
        self.zoom = max(6.0, min(120.0, float(value)))
        self._update_width()
        self.update()

    def set_selected(self, index):
        self.selected_index = int(index)
        self.update()

    def set_playhead(self, second):
        self.playhead = max(0.0, float(second or 0.0))
        self.update()

    def _update_width(self):
        duration = editor_engine.total_duration(self.clips)
        width = max(700, int(70 + duration * self.zoom))
        self.setMinimumWidth(width)
        self.resize(width, max(118, self.height()))

    def _clip_rects(self):
        # Geometry uses the exact same global-time scale as the red playhead.
        # The old fixed 52px minimum + 4px gap made the playhead drift away
        # from clip boundaries after several clips.
        rects = []
        cursor = 0.0
        top = 35.0
        height = 58.0
        for clip in self.clips:
            dur = editor_engine.clip_duration(clip)
            raw_x = 44.0 + cursor * self.zoom
            raw_w = max(2.0, dur * self.zoom)
            # 1px visual separation without changing the timeline scale.
            rects.append(
                QRectF(raw_x + 1.0, top, max(2.0, raw_w - 2.0), height)
            )
            cursor += dur
        return rects

    def _time_at_x(self, x):
        total = editor_engine.total_duration(self.clips)
        return max(
            0.0,
            min(total, (float(x) - 44.0) / max(0.1, self.zoom)),
        )

    def _handle_rect(self, rect, left=True):
        w = 9.0
        if left:
            return QRectF(rect.left(), rect.top(), w, rect.height())
        return QRectF(rect.right() - w, rect.top(), w, rect.height())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        palette = self.palette()
        bg = palette.window().color()
        fg = palette.windowText().color()
        p.fillRect(self.rect(), bg)

        # ruler
        p.setPen(QPen(QColor(fg.red(), fg.green(), fg.blue(), 110), 1))
        total = editor_engine.total_duration(self.clips)
        major = 5.0 if self.zoom < 18 else 2.0 if self.zoom < 45 else 1.0
        t = 0.0
        while t <= total + major:
            x = 44.0 + t * self.zoom
            p.drawLine(int(x), 18, int(x), 28)
            p.drawText(int(x + 2), 15, f"{t:.0f}s")
            t += major

        rects = self._clip_rects()
        for i, (clip, rect) in enumerate(zip(self.clips, rects)):
            selected = i == self.selected_index
            base = QColor(46, 112, 188) if not selected else QColor(53, 170, 110)
            if not clip.get("enabled", True):
                base = QColor(90, 90, 90)
            p.setPen(QPen(QColor(210, 220, 235), 2 if selected else 1))
            p.setBrush(base)
            p.drawRoundedRect(rect, 5, 5)

            p.setPen(Qt.white)
            font = QFont()
            font.setPointSize(9)
            font.setBold(selected)
            p.setFont(font)
            name = str(clip.get("name", "Clip"))
            p.drawText(
                rect.adjusted(13, 6, -13, -26),
                Qt.AlignLeft | Qt.AlignVCenter,
                name,
            )
            dur = editor_engine.clip_duration(clip)
            p.drawText(
                rect.adjusted(13, 28, -13, -3),
                Qt.AlignLeft | Qt.AlignVCenter,
                f"{dur:.2f}s  [{float(clip.get('source_start',0)):.2f} → {float(clip.get('source_end',0)):.2f}]",
            )

            # trim handles
            p.fillRect(self._handle_rect(rect, True), QColor(255, 211, 70))
            p.fillRect(self._handle_rect(rect, False), QColor(255, 211, 70))

        # playhead
        x = 44.0 + self.playhead * self.zoom
        p.setPen(QPen(QColor(255, 70, 70), 2))
        p.drawLine(int(x), 20, int(x), self.height() - 6)
        p.setBrush(QColor(255, 70, 70))
        p.drawPolygon([
            QPointF(x - 6, 20),
            QPointF(x + 6, 20),
            QPointF(x, 29),
        ])
        p.end()

    def mousePressEvent(self, event):
        pos = event.position()
        self.press_pos = QPointF(pos)
        self.drag_mode = ""
        self.drag_index = -1
        self.setCursor(Qt.ArrowCursor)
        self.temp_start = None
        self.temp_end = None

        # Ruler/playhead area always scrubs the global timeline.
        if pos.y() <= 34:
            self.drag_mode = "playhead"
            self.playhead = self._time_at_x(pos.x())
            self.playheadChanged.emit(self.playhead)
            self.setCursor(Qt.SizeHorCursor)
            self.update()
            return

        rects = self._clip_rects()
        for i, rect in enumerate(rects):
            if self._handle_rect(rect, True).contains(pos):
                self.selected_index = i
                self.drag_index = i
                self.drag_mode = "trim_left"
                self.temp_start = float(self.clips[i].get("source_start", 0.0))
                self.temp_end = float(self.clips[i].get("source_end", 0.0))
                self.clipSelected.emit(i)
                self.update()
                return
            if self._handle_rect(rect, False).contains(pos):
                self.selected_index = i
                self.drag_index = i
                self.drag_mode = "trim_right"
                self.temp_start = float(self.clips[i].get("source_start", 0.0))
                self.temp_end = float(self.clips[i].get("source_end", 0.0))
                self.clipSelected.emit(i)
                self.update()
                return
            if rect.contains(pos):
                self.selected_index = i
                self.drag_index = i
                self.drag_mode = "move_clip"
                self.setCursor(Qt.ClosedHandCursor)
                self.clipSelected.emit(i)
                self.update()
                return

        self.playhead = self._time_at_x(pos.x())
        self.playheadChanged.emit(self.playhead)
        self.update()

    def mouseMoveEvent(self, event):
        if self.drag_mode == "playhead":
            self.playhead = self._time_at_x(event.position().x())
            self.playheadChanged.emit(self.playhead)
            self.setCursor(Qt.SizeHorCursor)
            self.update()
            return

        if self.drag_index < 0 or not self.drag_mode:
            pos = event.position()
            cursor = Qt.ArrowCursor
            for rect in self._clip_rects():
                if (
                    self._handle_rect(rect, True).contains(pos)
                    or self._handle_rect(rect, False).contains(pos)
                ):
                    cursor = Qt.SizeHorCursor
                    break
                if rect.contains(pos):
                    cursor = Qt.OpenHandCursor
                    break
            self.setCursor(cursor)
            return
        dx = event.position().x() - self.press_pos.x()
        delta = dx / max(0.1, self.zoom)
        clip = self.clips[self.drag_index]
        full = float(clip.get("source_duration", clip.get("source_end", 0.0)) or 0.0)
        start0 = float(clip.get("source_start", 0.0))
        end0 = float(clip.get("source_end", 0.0))

        if self.drag_mode == "trim_left":
            new_start = max(0.0, min(end0 - 0.05, start0 + delta))
            self.temp_start = new_start
            preview = dict(clip)
            preview["source_start"] = new_start
            temp = list(self.clips)
            temp[self.drag_index] = preview
            self.clips = temp
            self.press_pos = QPointF(event.position())
            self.update()
        elif self.drag_mode == "trim_right":
            new_end = max(start0 + 0.05, min(full, end0 + delta))
            self.temp_end = new_end
            preview = dict(clip)
            preview["source_end"] = new_end
            temp = list(self.clips)
            temp[self.drag_index] = preview
            self.clips = temp
            self.press_pos = QPointF(event.position())
            self.update()

    def mouseReleaseEvent(self, event):
        if self.drag_mode == "playhead":
            self.playhead = self._time_at_x(event.position().x())
            self.playheadChanged.emit(self.playhead)
            self.drag_mode = ""
            self.setCursor(Qt.ArrowCursor)
            self.update()
            return

        if self.drag_index < 0:
            self.drag_mode = ""
            return

        index = self.drag_index
        if self.drag_mode in ("trim_left", "trim_right"):
            clip = self.clips[index]
            self.clipTrimChanged.emit(
                index,
                float(clip.get("source_start", 0.0)),
                float(clip.get("source_end", 0.0)),
            )

        elif self.drag_mode == "move_clip":
            moved = abs(event.position().x() - self.press_pos.x())
            if moved > 12:
                rects = self._clip_rects()
                x = event.position().x()
                target = index
                best = None
                for i, rect in enumerate(rects):
                    distance = abs(x - rect.center().x())
                    if best is None or distance < best:
                        best = distance
                        target = i
                if target != index:
                    self.clipReordered.emit(index, target)
            else:
                # A simple click on a clip is a seek, not a reorder.
                self.playhead = self._time_at_x(event.position().x())
                self.playheadChanged.emit(self.playhead)

        self.drag_mode = ""
        self.drag_index = -1
        self.temp_start = None
        self.temp_end = None
        self.update()
