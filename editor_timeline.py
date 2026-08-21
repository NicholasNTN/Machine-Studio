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
    itemSelected = Signal(str, str, int)
    trackStateChanged = Signal(str, str, bool)
    mediaDropped = Signal(str, float, str)
    HEADER_WIDTH = 132.0

    TRACKS = (("video", "Video"),)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.clips: list[dict] = []
        self.timeline_items = []
        self.tracks = []
        self.zoom = 14.0
        self.selected_index = -1
        self.selected_item_id = ""
        self.playhead = 0.0
        self.drag_mode = ""
        self.press_pos = QPointF()
        self.drag_index = -1
        self.temp_start = None
        self.temp_end = None
        self.setMinimumHeight(96)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

    def set_clips(self, clips):
        self.clips = [dict(c) for c in clips]
        if self.selected_index >= len(self.clips):
            self.selected_index = len(self.clips) - 1
        self._update_width()
        self.update()

    def set_timeline_items(self, items):
        self.timeline_items = list(items or [])
        self._update_width()
        self.update()

    def set_tracks(self, tracks):
        self.tracks = list(tracks or [])
        self.update()

    def set_zoom(self, value):
        self.zoom = max(6.0, min(120.0, float(value)))
        self._update_width()
        self.update()

    def set_selected(self, index):
        self.selected_index = int(index)
        self.update()

    def set_selected_item(self, item_id):
        self.selected_item_id = str(item_id or "")
        self.update()

    def set_playhead(self, second):
        self.playhead = max(0.0, float(second or 0.0))
        self.update()

    def _update_width(self):
        duration = max(70.0,
            editor_engine.total_duration(self.clips),
            max((float(getattr(item, "end", 0.0)) for item in self.timeline_items), default=0.0),
        )
        width = max(700, int(70 + duration * self.zoom))
        self.setMinimumWidth(width)
        self.resize(width, max(96, self.height()))

    def _track_top(self, kind):
        index = next((i for i, (key, _) in enumerate(self.TRACKS) if key == kind), 3)
        return 34.0 + index * 40.0

    def _clip_rects(self):
        # Geometry uses the exact same global-time scale as the red playhead.
        # The old fixed 52px minimum + 4px gap made the playhead drift away
        # from clip boundaries after several clips.
        rects = []
        cursor = 0.0
        top = self._track_top("video") + 3.0
        height = 34.0
        for clip in self.clips:
            dur = editor_engine.clip_duration(clip)
            raw_x = self.HEADER_WIDTH + cursor * self.zoom
            raw_w = max(2.0, dur * self.zoom)
            # 1px visual separation without changing the timeline scale.
            rects.append(
                QRectF(raw_x + 1.0, top, max(2.0, raw_w - 2.0), height)
            )
            cursor += dur
        return rects

    def _item_rects(self):
        return []

    def _time_at_x(self, x):
        total = max(70.0, editor_engine.total_duration(self.clips), max((float(getattr(item, "end", 0.0)) for item in self.timeline_items), default=0.0))
        return max(
            0.0,
            min(total, (float(x) - self.HEADER_WIDTH) / max(0.1, self.zoom)),
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

        # Professional fixed-order track lanes and compact headers.
        for index, (key, label) in enumerate(self.TRACKS):
            top = 34 + index * 40
            p.fillRect(QRectF(0, top, self.width(), 39), QColor(15, 26, 42) if index % 2 == 0 else QColor(18, 31, 50))
            p.setPen(QColor(108, 132, 164)); p.drawLine(0, top + 39, self.width(), top + 39)
            p.setPen(QColor(210, 222, 238)); p.drawText(QRectF(8, top, 72, 39), Qt.AlignVCenter | Qt.AlignLeft, label)
            track = next((track for track in self.tracks if getattr(getattr(track, "kind", ""), "value", "") == key), None)
            states = ("🔒" if track and track.locked else "🔓", "👁" if not track or track.visible else "○", "🔇" if track and track.muted else "🔊")
            p.setPen(QColor(128, 151, 181))
            for state_index, state in enumerate(states):
                p.drawText(QRectF(84 + state_index * 15, top, 15, 39), Qt.AlignCenter, state)

        # ruler
        p.setPen(QPen(QColor(fg.red(), fg.green(), fg.blue(), 110), 1))
        total = max(70.0, editor_engine.total_duration(self.clips), max((float(getattr(item, "end", 0.0)) for item in self.timeline_items), default=0.0))
        major = 5.0 if self.zoom < 10 else 2.0 if self.zoom < 45 else 1.0
        t = 0.0
        while t <= total + major:
            x = self.HEADER_WIDTH + t * self.zoom
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

        colors = {"text": QColor(124, 87, 214), "subtitle": QColor(24, 168, 178), "effect": QColor(194, 104, 43), "audio": QColor(39, 143, 95)}
        for item, rect, lane in self._item_rects():
            selected = str(getattr(item, "id", "")) == self.selected_item_id
            p.setPen(QPen(QColor(107, 181, 255) if selected else QColor(214, 225, 239), 3 if selected else 1)); p.setBrush(colors.get(lane, QColor(86, 105, 132))); p.drawRoundedRect(rect, 4, 4)
            label = str(getattr(item, "metadata", {}).get("text") or getattr(item, "metadata", {}).get("name") or getattr(getattr(item, "kind", "item"), "value", "item"))
            p.setPen(Qt.white); p.drawText(rect.adjusted(5, 0, -4, 0), Qt.AlignVCenter | Qt.AlignLeft, label[:36])

        # playhead
        x = self.HEADER_WIDTH + self.playhead * self.zoom
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

        if pos.x() < self.HEADER_WIDTH:
            lane_index = int((pos.y() - 34) // 40)
            if 0 <= lane_index < len(self.TRACKS):
                key = self.TRACKS[lane_index][0]
                track = next((track for track in self.tracks if getattr(getattr(track, "kind", ""), "value", "") == key), None)
                if track is not None:
                    state_index = min(2, max(0, int((pos.x() - 84) // 15)))
                    if pos.x() < 84: return
                    field = ("locked", "visible", "muted")[state_index]
                    setattr(track, field, not getattr(track, field))
                    self.trackStateChanged.emit(track.id, field, getattr(track, field))
                    self.update()
            return

        for item, rect, _lane in reversed(self._item_rects()):
            if rect.contains(pos):
                kind = getattr(getattr(item, "kind", "effect"), "value", str(getattr(item, "kind", "effect")))
                metadata = getattr(item, "metadata", {})
                legacy_index = -1
                if metadata in [getattr(candidate, "metadata", None) for candidate in self.timeline_items]:
                    try: legacy_index = self.timeline_items.index(item)
                    except ValueError: pass
                self.itemSelected.emit(kind, str(getattr(item, "id", "")), legacy_index)
                self.selected_item_id = str(getattr(item, "id", ""))
                self.update(); return

        rects = self._clip_rects()
        for i, rect in enumerate(rects):
            if self._handle_rect(rect, True).contains(pos):
                self.selected_index = i
                if self.clips[i].get("locked", False):
                    self.clipSelected.emit(i); self.update(); return
                self.drag_index = i
                self.drag_mode = "trim_left"
                self.temp_start = float(self.clips[i].get("source_start", 0.0))
                self.temp_end = float(self.clips[i].get("source_end", 0.0))
                self.clipSelected.emit(i)
                self.update()
                return
            if self._handle_rect(rect, False).contains(pos):
                self.selected_index = i
                if self.clips[i].get("locked", False):
                    self.clipSelected.emit(i); self.update(); return
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
                self.drag_mode = "" if self.clips[i].get("locked", False) else "move_clip"
                self.setCursor(Qt.ClosedHandCursor)
                self.clipSelected.emit(i)
                self.update()
                return

        self.playhead = self._time_at_x(pos.x())
        self.playheadChanged.emit(self.playhead)
        self.update()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls() and any(url.isLocalFile() for url in event.mimeData().urls()): event.acceptProposedAction()
        else: event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.acceptProposedAction()

    def dropEvent(self, event):
        urls = [url for url in event.mimeData().urls() if url.isLocalFile()]
        if not urls: event.ignore(); return
        lane_index = int((event.position().y() - 34) // 40)
        track_kind = self.TRACKS[lane_index][0] if 0 <= lane_index < len(self.TRACKS) else "video"
        global_time = self._time_at_x(event.position().x())
        for url in urls: self.mediaDropped.emit(url.toLocalFile(), global_time, track_kind)
        event.acceptProposedAction()

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
