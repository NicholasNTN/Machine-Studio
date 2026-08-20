from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QRectF, QPointF, Signal
from PySide6.QtGui import (
    QColor, QPainter, QPen, QBrush, QFont, QPixmap, QImage, QFontMetricsF
)
from PySide6.QtWidgets import QWidget


class InteractivePreviewOverlay(QWidget):
    """Single-surface Live Video Canvas.

    v1.0 no longer stacks QWidget overlays over QVideoWidget.
    QVideoSink sends decoded video frames here, and this widget paints:
      video frame -> real-time blur/black mask -> logo -> overlay text -> subtitle
    on the SAME surface.

    This avoids Windows native video-surface z-order problems and means visual
    settings appear immediately without swapping/reloading the media source.
    """

    blurZoneChanged = Signal(int, dict)
    subtitleGeometryChanged = Signal(float, float, float, int)
    logoGeometryChanged = Signal(float, float, float)
    overlayTextGeometryChanged = Signal(float, float, int)
    editorLayerGeometryChanged = Signal(int, dict)
    interactionFinished = Signal()
    selectionChanged = Signal(str, int)

    HANDLE = 12

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.StrongFocus)
        self.setMinimumSize(360, 360)

        self._frame_image = QImage()
        self._source_crop = QRectF()

        self.blur_enabled = False
        self.blur_style = "Trong mờ"
        self.blur_opacity = 20
        self.blur_zones: list[dict] = []

        self.sub_enabled = False
        self.sub_text = ""
        self.sub_style = None
        self.sub_effect = "Không"
        self.sub_elapsed = 0.0
        self.sub_duration = 1.0

        self.logo_enabled = False
        self.logo_path = ""
        self.logo_x = 88.0
        self.logo_y = 10.0
        self.logo_scale = 12.0
        self.logo_opacity = 100
        self._logo_pixmap = QPixmap()
        self._logo_loaded_path = ""

        self.text_enabled = False
        self.overlay_text = ""
        self.overlay_x = 12.0
        self.overlay_y = 8.0
        self.overlay_font_name = "Arial"
        self.overlay_font_size = 34
        self.overlay_color = "#FFFFFF"

        # Basic Editor extra layers (multiple text/image overlays).
        self.editor_layers: list[dict] = []
        self.editor_time = 0.0
        self._editor_pixmaps: dict[str, QPixmap] = {}
        self.start_editor_layer = None

        self.output_aspect = 9 / 16
        self.preview_zoom = 1.0
        self.preview_pan_x = 0.0
        self.preview_pan_y = 0.0
        self._pan_start = QPointF()
        self._pan_origin = QPointF()

        self.selected_type = ""
        self.selected_index = -1
        self.drag_mode = ""
        self.press_pos = QPointF()
        self.start_zone = None
        self.start_sub = None
        self.start_logo = None
        self.start_text = None

        # Smart alignment guides.
        self.snap_threshold_pct = 1.35
        self.snap_x_active = False
        self.snap_y_active = False

    def _snap_center_xy(self, x: float, y: float):
        """Snap an object's CENTER to the video X/Y center axes."""
        self.snap_x_active = abs(float(x) - 50.0) <= self.snap_threshold_pct
        self.snap_y_active = abs(float(y) - 50.0) <= self.snap_threshold_pct
        if self.snap_x_active:
            x = 50.0
        if self.snap_y_active:
            y = 50.0
        return x, y

    def _snap_zone_xy(self, zone: dict):
        """Snap a rectangular blur zone by its center."""
        z = dict(zone)
        w = float(z.get("w", 10))
        h = float(z.get("h", 10))
        cx = float(z.get("x", 0)) + w / 2.0
        cy = float(z.get("y", 0)) + h / 2.0
        cx, cy = self._snap_center_xy(cx, cy)
        z["x"] = max(0.0, min(100.0 - w, cx - w / 2.0))
        z["y"] = max(0.0, min(100.0 - h, cy - h / 2.0))
        return z

    # ==========================================================
    # VIDEO FRAME
    # ==========================================================
    def set_video_frame(self, frame):
        """Receive a QVideoFrame from QVideoSink.

        Convert immediately to QImage and do not retain QVideoFrame resources.
        """
        try:
            if frame is None or not frame.isValid():
                return
            image = frame.toImage()
            if image is None or image.isNull():
                return
            self._frame_image = image
            self.update()
        except Exception:
            # A malformed/unsupported frame must never close the editor.
            return

    def set_video_image(self, image):
        """Set a static QImage used before playback starts."""
        try:
            if image is None or image.isNull():
                return
            self._frame_image = image.copy()
            self.update()
        except Exception:
            return

    def clear_video_frame(self):
        self._frame_image = QImage()
        self.update()

    # ==========================================================
    # STATE
    # ==========================================================
    def set_output_aspect(self, aspect: float):
        if aspect and aspect > 0:
            self.output_aspect = float(aspect)
            self.update()

    def set_preview_zoom(self, zoom: float, reset_pan: bool = False):
        self.preview_zoom = max(0.5, min(3.0, float(zoom or 1.0)))
        if reset_pan or self.preview_zoom <= 1.001:
            self.preview_pan_x = 0.0
            self.preview_pan_y = 0.0
        self.update()

    def reset_preview_view(self):
        self.preview_zoom = 1.0
        self.preview_pan_x = 0.0
        self.preview_pan_y = 0.0
        self.update()

    def set_blur_state(self, enabled, style, opacity, zones):
        self.blur_enabled = bool(enabled)
        self.blur_style = str(style or "Trong mờ")
        self.blur_opacity = int(opacity or 20)
        self.blur_zones = [dict(z) for z in (zones or [])]
        if self.selected_type == "blur" and self.selected_index >= len(self.blur_zones):
            self.selected_type = ""
            self.selected_index = -1
        self.update()

    def set_subtitle_state(
        self,
        enabled,
        text,
        style,
        effect=None,
        elapsed=0.0,
        duration=1.0,
    ):
        self.sub_enabled = bool(enabled)
        self.sub_text = str(text or "")
        self.sub_style = style
        self.sub_effect = str(
            effect
            if effect is not None
            else getattr(style, "animation", "Không")
        )
        self.sub_elapsed = max(0.0, float(elapsed or 0.0))
        self.sub_duration = max(0.01, float(duration or 1.0))
        self.update()

    def set_logo_state(self, enabled, path, x, y, scale, opacity=100):
        self.logo_enabled = bool(enabled) and bool(path)
        self.logo_path = str(path or "")
        self.logo_x = float(x)
        self.logo_y = float(y)
        self.logo_scale = float(scale)
        self.logo_opacity = int(opacity)
        if self.logo_path != self._logo_loaded_path:
            self._logo_loaded_path = self.logo_path
            self._logo_pixmap = (
                QPixmap(self.logo_path)
                if self.logo_path and Path(self.logo_path).exists()
                else QPixmap()
            )
        self.update()

    def set_overlay_text_state(self, enabled, text, x, y, font_name, font_size, color):
        self.text_enabled = bool(enabled) and bool(str(text).strip())
        self.overlay_text = str(text or "")
        self.overlay_x = float(x)
        self.overlay_y = float(y)
        self.overlay_font_name = str(font_name or "Arial")
        self.overlay_font_size = int(font_size or 34)
        self.overlay_color = str(color or "#FFFFFF")
        self.update()


    def set_editor_layers(self, layers, current_time=0.0):
        self.editor_layers = [dict(x) for x in (layers or []) if isinstance(x, dict)]
        self.editor_time = max(0.0, float(current_time or 0.0))
        if (
            self.selected_type == "editor_layer"
            and not (0 <= self.selected_index < len(self.editor_layers))
        ):
            self.selected_type = ""
            self.selected_index = -1
        self.update()

    def editor_layer_active(self, layer):
        if not layer.get("enabled", True):
            return False
        start = float(layer.get("start", 0.0) or 0.0)
        end = float(layer.get("end", 1e12) or 1e12)
        return start <= self.editor_time < end

    def editor_layer_rect(self, index):
        if not (0 <= index < len(self.editor_layers)):
            return QRectF()
        layer = self.editor_layers[index]
        vr = self.video_rect()
        cx = vr.left() + vr.width() * float(layer.get("x", 50.0)) / 100
        cy = vr.top() + vr.height() * float(layer.get("y", 50.0)) / 100

        if layer.get("type") == "image":
            scale_pct = max(2.0, min(80.0, float(layer.get("scale", 20.0))))
            width = vr.width() * scale_pct / 100.0
            path = str(layer.get("path", "") or "")
            pix = self._editor_pixmaps.get(path)
            if pix is None:
                pix = QPixmap(path) if path and Path(path).exists() else QPixmap()
                self._editor_pixmaps[path] = pix
            ratio = 1.0
            if not pix.isNull() and pix.height() > 0:
                ratio = pix.width() / pix.height()
            height = width / max(0.1, ratio)
            return QRectF(cx - width/2, cy - height/2, width, height)

        # text
        text = str(layer.get("text", "Text") or "Text")
        scale = max(0.45, vr.height() / 1920 * 1.6)
        px = max(12, int(float(layer.get("font_size", 52)) * scale))
        width = min(vr.width() * 0.92, max(90, len(text) * px * 0.62))
        height = max(34, px * 1.65)
        return QRectF(cx - width/2, cy - height/2, width, height)

    # ==========================================================
    # GEOMETRY
    # ==========================================================
    def video_rect(self) -> QRectF:
        w = max(1.0, float(self.width()))
        h = max(1.0, float(self.height()))
        a = max(0.1, float(self.output_aspect))
        frame_aspect = w / h
        if frame_aspect > a:
            base_h = h
            base_w = base_h * a
        else:
            base_w = w
            base_h = base_w / a

        zoom = max(0.5, min(3.0, float(self.preview_zoom)))
        vw = base_w * zoom
        vh = base_h * zoom
        return QRectF(
            (w - vw) / 2.0 + self.preview_pan_x,
            (h - vh) / 2.0 + self.preview_pan_y,
            vw,
            vh,
        )

    def source_crop_rect(self) -> QRectF:
        if self._frame_image.isNull():
            return QRectF()
        sw = float(self._frame_image.width())
        sh = float(self._frame_image.height())
        target_a = max(0.1, float(self.output_aspect))
        src_a = sw / max(1.0, sh)

        # Live output preview follows centered Crop, matching default exporter.
        if src_a > target_a:
            crop_w = sh * target_a
            return QRectF((sw - crop_w) / 2, 0, crop_w, sh)
        crop_h = sw / target_a
        return QRectF(0, (sh - crop_h) / 2, sw, crop_h)

    def pct_rect(self, zone: dict) -> QRectF:
        vr = self.video_rect()
        x = vr.left() + vr.width() * float(zone.get("x", 0)) / 100
        y = vr.top() + vr.height() * float(zone.get("y", 0)) / 100
        w = vr.width() * float(zone.get("w", 100)) / 100
        h = vr.height() * float(zone.get("h", 20)) / 100
        return QRectF(x, y, w, h)

    def source_zone_rect(self, zone: dict) -> QRectF:
        src = self.source_crop_rect()
        if src.isNull():
            return QRectF()
        return QRectF(
            src.left() + src.width() * float(zone.get("x", 0)) / 100,
            src.top() + src.height() * float(zone.get("y", 0)) / 100,
            src.width() * float(zone.get("w", 100)) / 100,
            src.height() * float(zone.get("h", 20)) / 100,
        )

    def subtitle_rect(self) -> QRectF:
        vr = self.video_rect()
        st = self.sub_style
        if st is None:
            return QRectF()

        x_pct = float(getattr(st, "x_percent", 50))
        y_pct = float(getattr(st, "y_percent", 86))
        width_pct = float(getattr(st, "width_percent", 80))
        font_size = int(getattr(st, "font_size", 48))

        cx = vr.left() + vr.width() * x_pct / 100
        cy = vr.top() + vr.height() * y_pct / 100
        box_w = vr.width() * max(0.15, min(0.98, width_pct / 100))

        scale = max(0.45, vr.height() / 1920 * 1.6)
        visual_font = max(
            int(getattr(st, "min_font_size", 24) * scale),
            int(font_size * scale),
        )

        # One-line editor box only. Text is auto-fit during paint.
        box_h = max(38, visual_font * 1.75)
        return QRectF(
            cx - box_w / 2,
            cy - box_h / 2,
            box_w,
            box_h,
        )

    def _fit_subtitle_font_px(self, text: str, rect: QRectF, st) -> int:
        """One fixed subtitle size for the whole project."""
        vr = self.video_rect()
        scale = max(0.45, vr.height() / 1920 * 1.6)
        return max(12, int(getattr(st, "font_size", 48) * scale))

    def logo_rect(self) -> QRectF:
        vr = self.video_rect()
        if not self.logo_enabled:
            return QRectF()
        width = vr.width() * max(0.03, min(0.50, self.logo_scale / 100))
        ratio = 1.0
        if not self._logo_pixmap.isNull() and self._logo_pixmap.height() > 0:
            ratio = self._logo_pixmap.width() / self._logo_pixmap.height()
        height = width / max(0.1, ratio)
        cx = vr.left() + vr.width() * self.logo_x / 100
        cy = vr.top() + vr.height() * self.logo_y / 100
        return QRectF(cx - width / 2, cy - height / 2, width, height)

    def overlay_text_rect(self) -> QRectF:
        vr = self.video_rect()
        if not self.text_enabled:
            return QRectF()
        scale = max(0.45, vr.height() / 1920 * 1.6)
        px = max(14, int(self.overlay_font_size * scale))
        width = min(
            vr.width() * 0.80,
            max(130, len(self.overlay_text) * px * 0.60)
        )
        height = max(38, px * 1.7)
        cx = vr.left() + vr.width() * self.overlay_x / 100
        cy = vr.top() + vr.height() * self.overlay_y / 100
        return QRectF(cx - width / 2, cy - height / 2, width, height)

    def handle_rect(self, rect: QRectF) -> QRectF:
        s = self.HANDLE
        return QRectF(
            rect.right() - s, rect.bottom() - s, s * 1.7, s * 1.7
        )

    # ==========================================================
    # PAINT HELPERS
    # ==========================================================
    def _paint_video(self, p: QPainter):
        p.fillRect(self.rect(), QColor("#000000"))
        if self._frame_image.isNull():
            p.setPen(QColor("#72839a"))
            p.drawText(self.rect(), Qt.AlignCenter, "Chưa có frame video")
            return

        vr = self.video_rect()
        src = self.source_crop_rect()
        self._source_crop = src
        p.drawImage(vr, self._frame_image, src)

    def _paint_realtime_blur(self, p: QPainter, zone: dict, dst: QRectF):
        if self.blur_style == "Đen mờ":
            alpha = max(8, min(245, round(255 * self.blur_opacity / 100)))
            p.fillRect(dst, QColor(0, 0, 0, alpha))
            return

        # "Trong mờ": cheap real-time blur by downsample -> upscale.
        # Only the selected zones are processed, not the entire frame.
        if self._frame_image.isNull():
            return
        src_zone = self.source_zone_rect(zone)
        if src_zone.isNull():
            return

        sr = src_zone.toAlignedRect().intersected(self._frame_image.rect())
        if sr.width() < 2 or sr.height() < 2:
            return

        try:
            patch = self._frame_image.copy(sr)
            strength = max(5, min(30, 5 + int(self.blur_opacity * 0.22)))
            tiny_w = max(2, patch.width() // strength)
            tiny_h = max(2, patch.height() // strength)

            tiny = patch.scaled(
                tiny_w,
                tiny_h,
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation,
            )
            blurred = tiny.scaled(
                max(2, int(dst.width())),
                max(2, int(dst.height())),
                Qt.IgnoreAspectRatio,
                Qt.SmoothTransformation,
            )
            p.drawImage(dst, blurred)
        except Exception:
            # Visual fallback must still show the privacy mask.
            p.fillRect(dst, QColor(120, 125, 130, 100))

    def subtitle_animation_state(self):
        """Return scale, y_offset_px, opacity, visible_fraction."""
        effect = self.sub_effect or "Không"
        st = self.sub_style
        anim_ms = max(
            60,
            min(
                1200,
                int(getattr(st, "animation_duration_ms", 220))
                if st is not None
                else 220,
            ),
        )
        strength = max(
            10,
            min(
                200,
                int(getattr(st, "animation_strength", 100))
                if st is not None
                else 100,
            ),
        )
        amount = strength / 100.0
        intro = max(0.001, anim_ms / 1000.0)
        t = max(0.0, min(1.0, self.sub_elapsed / intro))
        remaining = max(0.0, self.sub_duration - self.sub_elapsed)

        scale = 1.0
        offset_y = 0.0
        opacity = 1.0
        visible_fraction = 1.0

        if effect == "Fade":
            opacity = t
            if remaining < 0.16:
                opacity *= max(0.0, remaining / 0.16)

        elif effect == "Slide Up":
            offset_y = (1.0 - t) * 45.0 * amount
            opacity = min(1.0, t * 1.6)

        elif effect == "Pop":
            if t < 0.72:
                u = t / 0.72
                scale = 0.62 + (1.12 - 0.62) * u
            else:
                u = (t - 0.72) / 0.28
                scale = 1.12 + (1.0 - 1.12) * u
            opacity = min(1.0, t * 2.2)

        elif effect == "Bounce":
            if t < 0.65:
                u = t / 0.65
                scale = 0.80 + 0.35 * u
                offset_y = (1.0 - u) * 55.0 * amount
            else:
                u = (t - 0.65) / 0.35
                scale = 1.15 - 0.15 * u
                offset_y = -8.0 * (1.0 - u) * amount
            opacity = min(1.0, t * 2.0)

        elif effect == "Typewriter":
            visible_fraction = max(0.04, t)

        # Karaoke uses progress across the whole cue, not only intro.
        elif effect == "Karaoke":
            visible_fraction = max(
                0.0,
                min(1.0, self.sub_elapsed / self.sub_duration),
            )

        elif effect == "Word Pop Sync":
            pop_ms = max(
                60,
                min(
                    260,
                    int(getattr(st, "word_pop_ms", 110))
                    if st is not None else 110,
                ),
            )
            peak = max(
                1.01,
                min(
                    1.25,
                    (
                        int(getattr(st, "word_pop_scale", 108))
                        if st is not None else 108
                    ) / 100.0,
                ),
            )
            t_pop = max(
                0.0,
                min(
                    1.0,
                    self.sub_elapsed / max(0.001, pop_ms / 1000.0),
                ),
            )

            if t_pop < 0.68:
                u = t_pop / 0.68
                scale = 0.88 + (peak - 0.88) * u
            else:
                u = (t_pop - 0.68) / 0.32
                scale = peak + (1.0 - peak) * u

            opacity = min(1.0, t_pop * 3.0)

            # A tiny tail fade avoids a hard visual cut when the next word arrives.
            remaining = max(0.0, self.sub_duration - self.sub_elapsed)
            if remaining < 0.040:
                opacity *= max(0.0, remaining / 0.040)

        return scale, offset_y, opacity, visible_fraction

    # ==========================================================
    # PAINT
    # ==========================================================
    def paintEvent(self, event):
        p = None
        try:
            p = QPainter(self)
            p.setRenderHint(QPainter.Antialiasing, True)

            # VIDEO AND EFFECTS ARE ON THE SAME SURFACE.
            self._paint_video(p)
            vr = self.video_rect()

            # Real-time blur/masks.
            if self.blur_enabled:
                for zone in self.blur_zones:
                    self._paint_realtime_blur(p, zone, self.pct_rect(zone))

            # Blur edit boundaries/handles.
            if self.blur_enabled:
                for i, zone in enumerate(self.blur_zones):
                    rect = self.pct_rect(zone)
                    is_auto = bool(zone.get("auto"))
                    selected = (
                        self.selected_type == "blur"
                        and self.selected_index == i
                    )
                    border = QColor("#FFD54A") if is_auto else QColor("#26D97F")
                    p.setBrush(Qt.NoBrush)
                    p.setPen(
                        QPen(
                            border if selected else QColor(240, 240, 240, 115),
                            2 if selected else 1,
                        )
                    )
                    p.drawRoundedRect(rect, 4, 4)
                    if is_auto:
                        p.setPen(QColor("#FFD54A"))
                        p.drawText(
                            rect.adjusted(5, 2, -5, -2),
                            Qt.AlignLeft | Qt.AlignTop,
                            "AUTO SUB",
                        )
                    if selected:
                        p.setBrush(border)
                        p.setPen(Qt.NoPen)
                        p.drawRect(self.handle_rect(rect))

            # User logo.
            if self.logo_enabled:
                rect = self.logo_rect()
                p.save()
                p.setOpacity(
                    max(0.05, min(1.0, self.logo_opacity / 100))
                )
                if not self._logo_pixmap.isNull():
                    p.drawPixmap(rect.toRect(), self._logo_pixmap)
                else:
                    p.fillRect(rect, QColor(80, 150, 230, 120))
                    p.setPen(Qt.white)
                    p.drawText(rect, Qt.AlignCenter, "LOGO")
                p.restore()

                if self.selected_type == "logo":
                    p.setBrush(Qt.NoBrush)
                    p.setPen(QPen(QColor("#33C4FF"), 2, Qt.DashLine))
                    p.drawRect(rect)
                    p.setBrush(QColor("#33C4FF"))
                    p.setPen(Qt.NoPen)
                    p.drawRect(self.handle_rect(rect))

            # Overlay text.
            if self.text_enabled:
                rect = self.overlay_text_rect()
                scale = max(0.45, vr.height() / 1920 * 1.6)
                px = max(14, int(self.overlay_font_size * scale))
                font = QFont(self.overlay_font_name)
                font.setPixelSize(px)
                font.setBold(True)
                p.setFont(font)
                p.setPen(QColor("#000000"))
                p.drawText(
                    rect.translated(2, 2),
                    Qt.AlignCenter | Qt.TextWordWrap,
                    self.overlay_text,
                )
                p.setPen(QColor(self.overlay_color))
                p.drawText(
                    rect,
                    Qt.AlignCenter | Qt.TextWordWrap,
                    self.overlay_text,
                )
                if self.selected_type == "text":
                    p.setBrush(Qt.NoBrush)
                    p.setPen(QPen(QColor("#FF9A3D"), 2, Qt.DashLine))
                    p.drawRect(rect)
                    p.setBrush(QColor("#FF9A3D"))
                    p.setPen(Qt.NoPen)
                    p.drawRect(self.handle_rect(rect))

            # Basic Editor extra text/image layers.
            for layer_index, layer in enumerate(self.editor_layers):
                if not self.editor_layer_active(layer):
                    continue
                rect = self.editor_layer_rect(layer_index)
                if rect.isNull():
                    continue

                p.save()
                p.setOpacity(
                    max(0.01, min(1.0, float(layer.get("opacity", 100)) / 100.0))
                )

                if layer.get("type") == "image":
                    path = str(layer.get("path", "") or "")
                    pix = self._editor_pixmaps.get(path)
                    if pix is None:
                        pix = QPixmap(path) if path and Path(path).exists() else QPixmap()
                        self._editor_pixmaps[path] = pix
                    if not pix.isNull():
                        p.drawPixmap(rect.toRect(), pix)
                    else:
                        p.fillRect(rect, QColor(70, 120, 170, 130))
                        p.setPen(Qt.white)
                        p.drawText(rect, Qt.AlignCenter, "IMAGE")
                else:
                    text = str(layer.get("text", "Text") or "Text")
                    vr_scale = max(0.45, vr.height() / 1920 * 1.6)
                    px = max(12, int(float(layer.get("font_size", 52)) * vr_scale))
                    font = QFont(str(layer.get("font_name", "Arial") or "Arial"))
                    font.setPixelSize(px)
                    font.setBold(True)
                    p.setFont(font)
                    p.setPen(QColor("#000000"))
                    p.drawText(
                        rect.translated(2, 2),
                        Qt.AlignCenter | Qt.TextWordWrap,
                        text,
                    )
                    p.setPen(QColor(str(layer.get("color", "#FFFFFF") or "#FFFFFF")))
                    p.drawText(
                        rect,
                        Qt.AlignCenter | Qt.TextWordWrap,
                        text,
                    )

                p.restore()

                if (
                    self.selected_type == "editor_layer"
                    and self.selected_index == layer_index
                ):
                    p.setBrush(Qt.NoBrush)
                    p.setPen(QPen(QColor("#D47CFF"), 2, Qt.DashLine))
                    p.drawRect(rect)
                    p.setBrush(QColor("#D47CFF"))
                    p.setPen(Qt.NoPen)
                    p.drawRect(self.handle_rect(rect))

            # Subtitle last.
            if (
                self.sub_enabled
                and self.sub_text
                and self.sub_style is not None
            ):
                st = self.sub_style
                rect = self.subtitle_rect()
                text = (
                    self.sub_text.upper()
                    if getattr(st, "uppercase", False)
                    else self.sub_text
                )
                if getattr(st, "single_line_auto", True):
                    text = " ".join(text.replace("\n", " ").split())

                scale_anim, offset_y, opacity_anim, visible_fraction = (
                    self.subtitle_animation_state()
                )

                # Typewriter reveals a growing prefix.
                if self.sub_effect == "Typewriter":
                    chars = max(
                        1,
                        min(
                            len(text),
                            round(len(text) * visible_fraction),
                        ),
                    )
                    text = text[:chars]

                p.save()
                center = rect.center()
                p.translate(center.x(), center.y() + offset_y)
                p.scale(scale_anim, scale_anim)
                p.translate(-center.x(), -center.y())
                p.setOpacity(max(0.0, min(1.0, opacity_anim)))

                if bool(getattr(st, "background_box", False)):
                    c = QColor(
                        getattr(st, "background_color", "#000000")
                    )
                    c.setAlpha(
                        int(
                            255
                            * max(
                                0,
                                min(
                                    100,
                                    int(
                                        getattr(
                                            st,
                                            "background_opacity",
                                            65,
                                        )
                                    ),
                                ),
                            )
                            / 100
                        )
                    )
                    p.setBrush(c)
                    p.setPen(Qt.NoPen)
                    p.drawRoundedRect(rect, 6, 6)

                px = self._fit_subtitle_font_px(text, rect, st)
                font = QFont(getattr(st, "font_name", "Arial"))
                font.setPixelSize(px)
                font.setBold(bool(getattr(st, "bold", True)))
                font.setItalic(bool(getattr(st, "italic", False)))
                p.setFont(font)

                flags = Qt.AlignCenter
                if not getattr(st, "single_line_auto", True):
                    flags |= Qt.TextWordWrap

                ow = max(
                    0,
                    int(round(float(getattr(st, "outline", 3.0)))),
                )

                def draw_caption(target_rect, color):
                    if ow:
                        p.setPen(
                            QColor(
                                getattr(
                                    st,
                                    "outline_color",
                                    "#000000",
                                )
                            )
                        )
                        for dx, dy in [
                            (-ow, 0), (ow, 0), (0, -ow), (0, ow),
                            (-ow, -ow), (ow, -ow),
                            (-ow, ow), (ow, ow),
                        ]:
                            p.drawText(
                                target_rect.translated(dx, dy),
                                flags,
                                text,
                            )
                    p.setPen(QColor(color))
                    p.drawText(target_rect, flags, text)

                # Base subtitle.
                draw_caption(
                    rect,
                    getattr(st, "primary_color", "#FFFFFF"),
                )

                # Karaoke overlay: clip a left-to-right highlight over the same text.
                if self.sub_effect == "Karaoke":
                    p.save()
                    clip = QRectF(
                        rect.left(),
                        rect.top(),
                        rect.width() * visible_fraction,
                        rect.height(),
                    )
                    p.setClipRect(clip)
                    # Avoid drawing outline twice for karaoke highlight.
                    old_ow = ow
                    ow = 0
                    draw_caption(
                        rect,
                        getattr(st, "karaoke_color", "#FFE600"),
                    )
                    ow = old_ow
                    p.restore()

                if self.selected_type == "sub":
                    p.setBrush(Qt.NoBrush)
                    p.setPen(QPen(QColor("#1FB6FF"), 2, Qt.DashLine))
                    p.drawRect(rect)
                    p.setBrush(QColor("#1FB6FF"))
                    p.setPen(Qt.NoPen)
                    p.drawRect(self.handle_rect(rect))

                p.restore()

            # Smart X/Y snapping guides.
            if self.snap_x_active or self.snap_y_active:
                p.save()
                guide_pen = QPen(QColor("#00FF66"), 1, Qt.DashLine)
                p.setPen(guide_pen)
                if self.snap_x_active:
                    xg = vr.center().x()
                    p.drawLine(int(xg), int(vr.top()), int(xg), int(vr.bottom()))
                if self.snap_y_active:
                    yg = vr.center().y()
                    p.drawLine(int(vr.left()), int(yg), int(vr.right()), int(yg))
                p.restore()

            # output-frame guide
            p.setBrush(Qt.NoBrush)
            p.setPen(QPen(QColor(80, 130, 200, 60), 1))
            p.drawRect(vr)

        except Exception:
            # Paint errors are logged by caller state, but never crash Qt UI.
            pass
        finally:
            if p is not None and p.isActive():
                p.end()

    # ==========================================================
    # MOUSE INTERACTION
    # ==========================================================
    def mousePressEvent(self, event):
        try:
            pos = event.position()
            if event.button() == Qt.MiddleButton:
                self.drag_mode = "preview_pan"
                self._pan_start = QPointF(pos)
                self._pan_origin = QPointF(
                    self.preview_pan_x, self.preview_pan_y
                )
                self.setCursor(Qt.ClosedHandCursor)
                return
            self.press_pos = QPointF(pos)

            if (
                self.selected_type == "blur"
                and 0 <= self.selected_index < len(self.blur_zones)
            ):
                rect = self.pct_rect(
                    self.blur_zones[self.selected_index]
                )
                if self.handle_rect(rect).contains(pos):
                    self.drag_mode = "resize_blur"
                    self.start_zone = dict(
                        self.blur_zones[self.selected_index]
                    )
                    return

            if self.selected_type == "sub" and self.sub_enabled:
                rect = self.subtitle_rect()
                if self.handle_rect(rect).contains(pos):
                    st = self.sub_style
                    self.drag_mode = "resize_sub"
                    self.start_sub = {
                        "x": float(getattr(st, "x_percent", 50)),
                        "y": float(getattr(st, "y_percent", 86)),
                        "w": float(getattr(st, "width_percent", 80)),
                        "font": int(getattr(st, "font_size", 48)),
                    }
                    return

            if self.selected_type == "logo" and self.logo_enabled:
                rect = self.logo_rect()
                if self.handle_rect(rect).contains(pos):
                    self.drag_mode = "resize_logo"
                    self.start_logo = {
                        "x": self.logo_x,
                        "y": self.logo_y,
                        "scale": self.logo_scale,
                    }
                    return

            if self.selected_type == "text" and self.text_enabled:
                rect = self.overlay_text_rect()
                if self.handle_rect(rect).contains(pos):
                    self.drag_mode = "resize_text"
                    self.start_text = {
                        "x": self.overlay_x,
                        "y": self.overlay_y,
                        "font": self.overlay_font_size,
                    }
                    return

            if (
                self.selected_type == "editor_layer"
                and 0 <= self.selected_index < len(self.editor_layers)
            ):
                rect = self.editor_layer_rect(self.selected_index)
                if self.handle_rect(rect).contains(pos):
                    self.drag_mode = "resize_editor_layer"
                    self.start_editor_layer = dict(
                        self.editor_layers[self.selected_index]
                    )
                    return

            # Extra editor layers are top-most interactive overlays.
            for i in reversed(range(len(self.editor_layers))):
                layer = self.editor_layers[i]
                if (
                    self.editor_layer_active(layer)
                    and self.editor_layer_rect(i).contains(pos)
                ):
                    self.selected_type = "editor_layer"
                    self.selected_index = i
                    self.drag_mode = "move_editor_layer"
                    self.start_editor_layer = dict(layer)
                    self.selectionChanged.emit("editor_layer", i)
                    self.update()
                    return

            if (
                self.sub_enabled
                and self.subtitle_rect().contains(pos)
            ):
                st = self.sub_style
                self.selected_type = "sub"
                self.selected_index = -1
                self.drag_mode = "move_sub"
                self.start_sub = {
                    "x": float(getattr(st, "x_percent", 50)),
                    "y": float(getattr(st, "y_percent", 86)),
                    "w": float(getattr(st, "width_percent", 80)),
                    "font": int(getattr(st, "font_size", 48)),
                }
                self.selectionChanged.emit("sub", -1)
                self.update()
                return

            if (
                self.text_enabled
                and self.overlay_text_rect().contains(pos)
            ):
                self.selected_type = "text"
                self.drag_mode = "move_text"
                self.start_text = {
                    "x": self.overlay_x,
                    "y": self.overlay_y,
                    "font": self.overlay_font_size,
                }
                self.selectionChanged.emit("text", -1)
                self.update()
                return

            if self.logo_enabled and self.logo_rect().contains(pos):
                self.selected_type = "logo"
                self.drag_mode = "move_logo"
                self.start_logo = {
                    "x": self.logo_x,
                    "y": self.logo_y,
                    "scale": self.logo_scale,
                }
                self.selectionChanged.emit("logo", -1)
                self.update()
                return

            if self.blur_enabled:
                for i in reversed(range(len(self.blur_zones))):
                    if self.pct_rect(self.blur_zones[i]).contains(pos):
                        self.selected_type = "blur"
                        self.selected_index = i
                        self.drag_mode = "move_blur"
                        self.start_zone = dict(self.blur_zones[i])
                        self.selectionChanged.emit("blur", i)
                        self.update()
                        return

            self.selected_type = ""
            self.selected_index = -1
            self.drag_mode = ""
            self.update()
        except Exception:
            self.drag_mode = ""

    def mouseMoveEvent(self, event):
        if not self.drag_mode:
            return
        try:
            if self.drag_mode == "preview_pan":
                delta = event.position() - self._pan_start
                self.preview_pan_x = self._pan_origin.x() + delta.x()
                self.preview_pan_y = self._pan_origin.y() + delta.y()
                self.update()
                return

            vr = self.video_rect()
            if vr.width() <= 1 or vr.height() <= 1:
                return

            self.snap_x_active = False
            self.snap_y_active = False

            dx = (
                event.position().x() - self.press_pos.x()
            ) / vr.width() * 100
            dy = (
                event.position().y() - self.press_pos.y()
            ) / vr.height() * 100

            if (
                self.drag_mode in ("move_editor_layer", "resize_editor_layer")
                and self.start_editor_layer is not None
                and 0 <= self.selected_index < len(self.editor_layers)
            ):
                layer = dict(self.start_editor_layer)

                if self.drag_mode == "move_editor_layer":
                    layer["x"] = max(
                        1.0, min(99.0, float(layer.get("x", 50.0)) + dx)
                    )
                    layer["y"] = max(
                        1.0, min(99.0, float(layer.get("y", 50.0)) + dy)
                    )
                    layer["x"], layer["y"] = self._snap_center_xy(
                        layer["x"], layer["y"]
                    )
                else:
                    if layer.get("type") == "image":
                        layer["scale"] = max(
                            2.0,
                            min(
                                80.0,
                                float(layer.get("scale", 20.0)) + dx * 1.4,
                            ),
                        )
                    else:
                        layer["font_size"] = max(
                            10,
                            min(
                                220,
                                int(
                                    round(
                                        float(layer.get("font_size", 52))
                                        + dx * 1.15
                                    )
                                ),
                            ),
                        )

                self.editor_layers[self.selected_index] = layer
                self.editorLayerGeometryChanged.emit(
                    self.selected_index, dict(layer)
                )
                self.update()
                return

            if self.drag_mode in ("move_blur", "resize_blur"):
                i = self.selected_index
                if (
                    not (0 <= i < len(self.blur_zones))
                    or not self.start_zone
                ):
                    return
                z = dict(self.start_zone)

                if self.drag_mode == "move_blur":
                    z["x"] = max(
                        0,
                        min(
                            100 - float(z.get("w", 10)),
                            float(z.get("x", 0)) + dx,
                        ),
                    )
                    z["y"] = max(
                        0,
                        min(
                            100 - float(z.get("h", 10)),
                            float(z.get("y", 0)) + dy,
                        ),
                    )
                    z = self._snap_zone_xy(z)
                else:
                    z["w"] = max(
                        3,
                        min(
                            100 - float(z.get("x", 0)),
                            float(z.get("w", 10)) + dx,
                        ),
                    )
                    z["h"] = max(
                        3,
                        min(
                            100 - float(z.get("y", 0)),
                            float(z.get("h", 10)) + dy,
                        ),
                    )

                self.blur_zones[i] = z
                self.blurZoneChanged.emit(i, z)
                self.update()
                return

            if (
                self.drag_mode in ("move_sub", "resize_sub")
                and self.start_sub
            ):
                x = self.start_sub["x"]
                y = self.start_sub["y"]
                w = self.start_sub["w"]
                font = self.start_sub["font"]

                if self.drag_mode == "move_sub":
                    x = max(5, min(95, x + dx))
                    y = max(5, min(95, y + dy))
                    x, y = self._snap_center_xy(x, y)
                else:
                    w = max(20, min(96, w + dx * 2))
                    font = max(
                        12,
                        min(
                            120,
                            int(round(font + dy * 1.15)),
                        ),
                    )

                self.subtitleGeometryChanged.emit(x, y, w, font)
                return

            if (
                self.drag_mode in ("move_logo", "resize_logo")
                and self.start_logo
            ):
                x = self.start_logo["x"]
                y = self.start_logo["y"]
                scale = self.start_logo["scale"]

                if self.drag_mode == "move_logo":
                    x = max(2, min(98, x + dx))
                    y = max(2, min(98, y + dy))
                    x, y = self._snap_center_xy(x, y)
                else:
                    scale = max(3, min(50, scale + dx))

                self.logoGeometryChanged.emit(x, y, scale)
                return

            if (
                self.drag_mode in ("move_text", "resize_text")
                and self.start_text
            ):
                x = self.start_text["x"]
                y = self.start_text["y"]
                font = self.start_text["font"]

                if self.drag_mode == "move_text":
                    x = max(2, min(98, x + dx))
                    y = max(2, min(98, y + dy))
                    x, y = self._snap_center_xy(x, y)
                else:
                    font = max(
                        12,
                        min(
                            120,
                            int(round(font + dy * 1.15)),
                        ),
                    )

                self.overlayTextGeometryChanged.emit(x, y, font)
                return

        except Exception:
            self.drag_mode = ""

    def mouseReleaseEvent(self, event):
        try:
            if self.drag_mode == "preview_pan":
                self.setCursor(Qt.ArrowCursor)
            elif self.drag_mode:
                self.interactionFinished.emit()
        finally:
            self.drag_mode = ""
            self.start_zone = None
            self.start_sub = None
            self.start_logo = None
            self.start_text = None
            self.start_editor_layer = None
            self.snap_x_active = False
            self.snap_y_active = False
            self.update()
