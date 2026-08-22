from __future__ import annotations

from PySide6.QtCore import QEvent, Qt, QRectF, QPointF, Signal
from PySide6.QtGui import QColor, QPainter, QPen, QFont
from PySide6.QtWidgets import QWidget
from ui.icons import machine_pixmap
from ui.theme import tokens

from core import editor_engine
from editor.timeline_view import compute_auto_timeline_view


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
        self.visible_duration = 70.0
        self.major_tick_interval = 5.0
        self.auto_fit = True
        self._viewport = None
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

    def set_zoom(self, value, user_modified=True):
        self.zoom = max(6.0, min(120.0, float(value)))
        if user_modified: self.auto_fit = False
        self._update_width()
        self.update()

    def fit_to_viewport(self):
        self.auto_fit = True; self._update_width(); self.update()

    def attach_viewport(self, viewport):
        if self._viewport is viewport: return
        if self._viewport is not None: self._viewport.removeEventFilter(self)
        self._viewport = viewport; viewport.installEventFilter(self); self._update_width()

    def eventFilter(self, watched, event):
        if watched is self._viewport and event.type() == QEvent.Resize and self.auto_fit:
            self._update_width(); self.update()
        return super().eventFilter(watched, event)

    def content_duration(self):
        return max(editor_engine.total_duration(self.clips), max((float(getattr(item, "end", 0.0)) for item in self.timeline_items), default=0.0))

    def time_to_x(self, seconds): return self.HEADER_WIDTH + max(0.0, float(seconds)) * self.zoom
    def x_to_time(self, x): return max(0.0, min(self.visible_duration, (float(x) - self.HEADER_WIDTH) / max(0.1, self.zoom)))

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
        content = self.content_duration()
        viewport_width = max(1, self._viewport.width()) if self._viewport is not None else max(700, self.width())
        if self.auto_fit:
            view = compute_auto_timeline_view(viewport_width, content, header_width=self.HEADER_WIDTH)
            self.visible_duration = view.visible_duration; self.zoom = view.pixels_per_second; self.major_tick_interval = view.major_tick_interval
            width = viewport_width
        else:
            minimum_span = max(5.0, content + max(5.0, content * 0.05))
            viewport_span = max(1.0, viewport_width - self.HEADER_WIDTH) / self.zoom
            self.visible_duration = max(minimum_span, viewport_span)
            width = max(viewport_width, int(self.HEADER_WIDTH + self.visible_duration * self.zoom))
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
            raw_x = self.time_to_x(cursor)
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
        return self.x_to_time(x)

    def _handle_rect(self, rect, left=True):
        w = 9.0
        if left:
            return QRectF(rect.left(), rect.top(), w, rect.height())
        return QRectF(rect.right() - w, rect.top(), w, rect.height())

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing, True)

        colors = tokens()["color"]
        p.fillRect(self.rect(), QColor(colors["timeline"]))
        p.fillRect(QRectF(0, 0, self.width(), 34), QColor(colors["ruler"]))
        p.setPen(QPen(QColor("#293543"), 1)); p.drawLine(0, 33, self.width(), 33)
        # Professional fixed-order track lanes and compact headers.
        for index, (key, label) in enumerate(self.TRACKS):
            top = 34 + index * 40
            p.fillRect(QRectF(0, top, self.width(), 39), QColor(colors["timeline"]))
            p.fillRect(QRectF(0, top, self.HEADER_WIDTH, 39), QColor(colors["input"]))
            p.setPen(QColor(colors["border"])); p.drawLine(int(self.HEADER_WIDTH), top, int(self.HEADER_WIDTH), top + 39)
            p.setPen(QColor(colors["border"])); p.drawLine(0, top + 39, self.width(), top + 39)
            p.setPen(QColor(colors["textSecondary"])); p.drawText(QRectF(8, top, 72, 39), Qt.AlignVCenter | Qt.AlignLeft, label)
            track = next((track for track in self.tracks if getattr(getattr(track, "kind", ""), "value", "") == key), None)
            states = (
                ("lock", "accent" if track and track.locked else "textMuted"),
                ("visible" if not track or track.visible else "hidden", "textMuted"),
                ("muted" if track and track.muted else "volume", "textMuted"),
            )
            for state_index, (state, color) in enumerate(states):
                p.drawPixmap(84 + state_index * 15, top + 13, machine_pixmap(state, color, 14))

        # ruler
        total = self.visible_duration
        major = self.major_tick_interval if self.auto_fit else min((0.5, 1, 2, 5, 10, 15, 30, 60, 120, 300), key=lambda value: abs(value * self.zoom - 60))
        minor = major / 5.0
        t = minor
        p.setPen(QPen(QColor("#465260"), 1))
        while t <= total + major:
            if abs((t / major) - round(t / major)) > 0.001:
                x = self.time_to_x(t); p.drawLine(int(x), 23, int(x), 28)
            t += minor
        ruler_font = QFont(p.font()); ruler_font.setPixelSize(9); p.setFont(ruler_font)
        p.setPen(QPen(QColor("#687586"), 1))
        t = 0.0
        while t <= total + major:
            x = self.time_to_x(t)
            p.drawLine(int(x), 18, int(x), 28)
            p.setPen(QColor("#A9B3C0"))
            p.drawText(int(x + 2), 15, f"{t:.0f}s")
            p.setPen(QPen(QColor("#687586"), 1))
            t += major

        rects = self._clip_rects()
        for i, (clip, rect) in enumerate(zip(self.clips, rects)):
            selected = i == self.selected_index
            base = QColor(colors["accent"] if i % 2 == 0 else colors["success"])
            if not clip.get("enabled", True):
                base = QColor(colors["disabledSurface"])
            p.setPen(QPen(QColor(colors["textPrimary"] if selected else colors["borderStrong"]), 2 if selected else 1))
            p.setBrush(base)
            p.drawRoundedRect(rect, 4, 4)

            p.setPen(Qt.white)
            font = QFont(p.font())
            font.setPixelSize(10)
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
            p.fillRect(self._handle_rect(rect, True), QColor(colors["warning"]))
            p.fillRect(self._handle_rect(rect, False), QColor(colors["warning"]))

        lane_colors = {"text": QColor(colors["timelineText"]), "subtitle": QColor(colors["timelineSubtitle"]), "effect": QColor(colors["timelineEffect"]), "audio": QColor(colors["timelineAudio"])}
        for item, rect, lane in self._item_rects():
            selected = str(getattr(item, "id", "")) == self.selected_item_id
            p.setPen(QPen(QColor(colors["accentHover"]) if selected else QColor(colors["textSecondary"]), 3 if selected else 1)); p.setBrush(lane_colors.get(lane, QColor(colors["textMuted"]))); p.drawRoundedRect(rect, 4, 4)
            label = str(getattr(item, "metadata", {}).get("text") or getattr(item, "metadata", {}).get("name") or getattr(getattr(item, "kind", "item"), "value", "item"))
            p.setPen(Qt.white); p.drawText(rect.adjusted(5, 0, -4, 0), Qt.AlignVCenter | Qt.AlignLeft, label[:36])

        # playhead
        x = self.time_to_x(self.playhead)
        p.setPen(QPen(QColor(colors["playhead"]), 2))
        p.drawLine(int(x), 20, int(x), self.height() - 6)
        p.setBrush(QColor(colors["playhead"]))
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
