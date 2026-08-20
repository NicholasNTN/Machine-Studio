from __future__ import annotations

import sys
import os
import shutil
import traceback
import hashlib
import re
import json
import faulthandler
import datetime
from dataclasses import replace
from pathlib import Path

from PySide6.QtCore import Qt, QThread, Signal, QUrl, QTimer
from PySide6.QtGui import (
    QDragEnterEvent, QDropEvent, QColor, QFont, QFontMetricsF,
    QCloseEvent, QDesktopServices, QImage
)
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QVideoSink
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QFileDialog, QMessageBox, QTabWidget, QStackedWidget,
    QGroupBox, QListWidget, QListWidgetItem, QComboBox as _QComboBox,
    QDoubleSpinBox as _QDoubleSpinBox, QSpinBox as _QSpinBox,
    QCheckBox, QPlainTextEdit, QProgressBar, QTableWidget,
    QTableWidgetItem, QHeaderView, QSplitter, QScrollArea, QFormLayout,
    QAbstractItemView, QDialog, QDialogButtonBox, QFontComboBox, QColorDialog,
    QSlider, QFrame, QInputDialog, QRadioButton, QButtonGroup
)

from core.models import AIProject, ExportOptions, SubtitleStyle
from core.settings_store import SettingsStore
from core import ffmpeg_engine as ffm
from core import gemini_engine as gem
from core import ai_provider as ai
from core import downloader, subtitle_engine, vocal_separator, tts_engine, piper_engine, editor_engine
from core import subtitle_detector
from core.system_info import get_system_summary
from live_overlay import InteractivePreviewOverlay
from editor_timeline import BasicTimelineWidget
from editor.document import EditorDocument
from ui.app_shell import AppShell
from ui.editor_workspace import EditorWorkspace
from ui.inspector_panel import InspectorPanel
from ui.media_panel import MediaPanel
from ui.tool_panels import ActionListPanel
from services.preview_service import PreviewService
from editor.timeline_item import TimelineItem, TimelineItemKind


APP_NAME = "Machine Studio"
VERSION = "v1.1.0 PRO FOUNDATION"
ROOT = Path(__file__).resolve().parent


AI_STYLE_LIBRARY = {
    "Factory documentary": "Phim tài liệu nhà máy — rõ ràng, chuyên nghiệp, tập trung quy trình.",
    "Fast viral explainer": "Giải thích nhanh kiểu viral — hook mạnh, nhịp nhanh, dễ giữ người xem.",
    "Calm documentary": "Tài liệu nhẹ nhàng — giọng kể chậm, tự nhiên, dễ nghe.",
    "Technical explainer": "Giải thích kỹ thuật — nhiều chi tiết cơ chế và thông số.",
    "How it works": "Cách nó hoạt động — giải thích từng bước từ nguyên lý đến kết quả.",
    "Engineering breakdown": "Phân tích kỹ thuật — bóc tách cấu tạo, cơ chế và lý do thiết kế.",
    "Mega machines": "Máy móc khổng lồ — nhấn mạnh quy mô, sức mạnh và con số ấn tượng.",
    "Manufacturing process": "Quy trình sản xuất — đi theo dây chuyền từ nguyên liệu đến thành phẩm.",
    "Satisfying process": "Quy trình mãn nhãn — ít lời hơn, mô tả đúng khoảnh khắc hình ảnh hấp dẫn.",
    "Invention showcase": "Giới thiệu phát minh — vấn đề, ý tưởng, cách hoạt động và lợi ích.",
    "Innovation story": "Câu chuyện đổi mới — từ nhu cầu thực tế đến giải pháp mới.",
    "Before and after": "Trước và sau — tập trung thay đổi, cải tiến và kết quả.",
    "Product teardown": "Mổ xẻ sản phẩm — cấu tạo bên trong, linh kiện và cách phối hợp.",
    "Science and discovery": "Khoa học & khám phá — giải thích hiện tượng bằng tư duy khoa học.",
    "History documentary": "Tài liệu lịch sử — bối cảnh, mốc thời gian, nguyên nhân và ảnh hưởng.",
    "News report": "Bản tin — ngắn gọn, trung tính, ưu tiên sự kiện và dữ kiện.",
    "Business case study": "Case study kinh doanh — vấn đề, chiến lược, kết quả và bài học.",
    "Motivational": "Truyền cảm hứng — năng lượng tích cực, nhấn mạnh nỗ lực và thành tựu.",
    "Storytelling documentary": "Tài liệu kể chuyện — có mở đầu, xung đột, cao trào và kết luận.",
    "Mystery and curiosity": "Bí ẩn & tò mò — mở bằng câu hỏi, giữ thông tin quan trọng đến sau.",
    "Top 10 countdown": "Đếm ngược Top — nhịp rõ, từng mục ngắn, tăng tò mò về vị trí cao nhất.",
    "Comparison": "So sánh — đối chiếu ưu nhược điểm, hiệu suất, giá trị hoặc quy mô.",
    "Educational lesson": "Bài học giáo dục — cấu trúc dễ học, định nghĩa trước rồi ví dụ.",
    "Beginner friendly": "Cho người mới — dùng từ đơn giản, giải thích thuật ngữ ngay khi xuất hiện.",
    "Expert deep dive": "Đào sâu chuyên gia — chi tiết cao, ít đơn giản hóa, thiên về người có nền tảng.",
    "Cinematic narration": "Thuyết minh điện ảnh — câu chữ giàu hình ảnh, nhịp có cao trào.",
    "High-energy shorts": "Shorts năng lượng cao — câu rất ngắn, hook dày, chuyển ý nhanh.",
    "Luxury documentary": "Tài liệu cao cấp — tinh tế, chậm hơn, nhấn mạnh chất lượng và craftsmanship.",
    "Agriculture and machinery": "Nông nghiệp & máy móc — thực tế đồng ruộng, năng suất và cơ giới hóa.",
    "Construction and heavy equipment": "Xây dựng & thiết bị nặng — công trường, tải trọng, an toàn và hiệu suất.",
    "Automotive engineering": "Kỹ thuật ô tô — động cơ, truyền động, khung gầm và công nghệ xe.",
    "Aerospace engineering": "Hàng không vũ trụ — thiết kế, vật liệu, khí động học và hệ thống bay.",
    "Technology innovation": "Đổi mới công nghệ — công nghệ mới, ứng dụng và tác động thực tế.",
    "Environmental documentary": "Tài liệu môi trường — tài nguyên, tác động, giải pháp và tính bền vững.",
    "Food production": "Sản xuất thực phẩm — nguyên liệu, chế biến, kiểm soát chất lượng và đóng gói.",
    "Travel documentary": "Tài liệu du lịch — địa điểm, trải nghiệm, văn hóa và câu chuyện địa phương.",
    "Human interest story": "Câu chuyện con người — tập trung nhân vật, cảm xúc và trải nghiệm thật.",
    "Problem solution explainer": "Vấn đề → giải pháp — nêu pain point rồi giải thích cách công nghệ xử lý.",
    "Myth vs fact": "Hiểu lầm vs sự thật — đặt quan niệm phổ biến cạnh dữ kiện thực tế.",
    "Data driven explainer": "Giải thích dựa dữ liệu — ưu tiên số liệu, tỷ lệ và so sánh định lượng.",
}


WHEEL_INPUT_LOCKED = True


def fmt_time(seconds: float) -> str:
    seconds = max(0, int(seconds or 0))
    return f"{seconds // 3600:02d}:{seconds // 60 % 60:02d}:{seconds % 60:02d}"


class _WheelSafeMixin:
    """Prevent accidental setting changes while scrolling the side panels.

    Rules:
    - global Wheel Lock ON: wheel NEVER changes this control;
    - Wheel Lock OFF: user must click this exact control first;
    - leaving the control disarms wheel again.
    """
    def _wheel_safe_init(self):
        self._wheel_armed = False

    def mousePressEvent(self, event):
        self._wheel_armed = True
        return super().mousePressEvent(event)

    def leaveEvent(self, event):
        self._wheel_armed = False
        return super().leaveEvent(event)

    def focusOutEvent(self, event):
        self._wheel_armed = False
        return super().focusOutEvent(event)

    def wheelEvent(self, event):
        if WHEEL_INPUT_LOCKED or not self._wheel_armed:
            event.ignore()
            return
        super().wheelEvent(event)


class QSpinBox(_WheelSafeMixin, _QSpinBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wheel_safe_init()


class QDoubleSpinBox(_WheelSafeMixin, _QDoubleSpinBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wheel_safe_init()


class QComboBox(_WheelSafeMixin, _QComboBox):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._wheel_safe_init()


class Worker(QThread):
    done = Signal(object)
    error = Signal(str)
    progress = Signal(int, int)
    log = Signal(str)

    def __init__(self, fn):
        super().__init__()
        self.fn = fn

    def run(self):
        try:
            result = self.fn(
                lambda a, b: self.progress.emit(a, b),
                lambda text: self.log.emit(str(text)),
            )
            self.done.emit(result)
        except Exception:
            self.error.emit(traceback.format_exc())


class SubtitlePresetDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Chọn mẫu phụ đề")
        self.resize(900, 620)
        self.selected_name = ""

        root = QVBoxLayout(self)
        title = QLabel("Chọn mẫu phụ đề")
        title.setObjectName("dialogTitle")
        root.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        holder = QWidget()
        grid = QGridLayout(holder)

        for i, name in enumerate(subtitle_engine.list_presets()):
            style = subtitle_engine.PRESETS[name]
            button = QPushButton(f"Phụ đề mẫu\n{name}")
            button.setMinimumSize(190, 86)
            bg = style.background_color if style.background_box else "#151d2b"
            weight = "700" if style.bold else "400"
            button.setStyleSheet(
                f"QPushButton{{background:{bg};color:{style.primary_color};"
                f"font-family:'{style.font_name}';font-size:16px;font-weight:{weight};"
                f"border:2px solid {style.outline_color};border-radius:5px;}}"
                "QPushButton:hover{border:2px solid #1db8ff;}"
            )
            button.clicked.connect(lambda checked=False, n=name: self.pick(n))
            grid.addWidget(button, i // 4, i % 4)

        scroll.setWidget(holder)
        root.addWidget(scroll, 1)

        close = QPushButton("Đóng")
        close.clicked.connect(self.reject)
        root.addWidget(close)

    def pick(self, name):
        self.selected_name = name
        self.accept()


class BlurZoneDialog(QDialog):
    def __init__(self, parent=None, zone=None):
        super().__init__(parent)
        self.setWindowTitle("Thiết lập vùng che")
        self.zone = dict(zone or {"x": 0, "y": 70, "w": 100, "h": 20})
        form = QFormLayout(self)

        self.x = QSpinBox(); self.x.setRange(0, 99); self.x.setSuffix(" %")
        self.y = QSpinBox(); self.y.setRange(0, 99); self.y.setSuffix(" %")
        self.w = QSpinBox(); self.w.setRange(1, 100); self.w.setSuffix(" %")
        self.h = QSpinBox(); self.h.setRange(1, 100); self.h.setSuffix(" %")

        self.x.setValue(int(self.zone.get("x", 0)))
        self.y.setValue(int(self.zone.get("y", 70)))
        self.w.setValue(int(self.zone.get("w", 100)))
        self.h.setValue(int(self.zone.get("h", 20)))

        form.addRow("X từ trái", self.x)
        form.addRow("Y từ trên", self.y)
        form.addRow("Chiều rộng", self.w)
        form.addRow("Chiều cao", self.h)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        form.addRow(buttons)

    def result_zone(self):
        return {
            "x": self.x.value(),
            "y": self.y.value(),
            "w": self.w.value(),
            "h": self.h.value(),
        }


class PiperVoiceDialog(QDialog):
    """Compact Piper voice browser; catalog is cached locally."""

    def __init__(self, parent, current_voice=""):
        super().__init__(parent)
        self.parent_window = parent
        self.selected_voice = current_voice or "en_US-lessac-medium"
        self.catalog = piper_engine.get_catalog(ROOT, online=False)

        self.setWindowTitle("Piper Voice Manager — Offline TTS")
        self.resize(900, 650)

        root = QVBoxLayout(self)

        title = QLabel("🎙 Piper Offline Voice Manager")
        title.setObjectName("dialogTitle")
        root.addWidget(title)

        top = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText(
            "Tìm voice: lessac, amy, en_US, Vietnamese..."
        )
        self.search.textChanged.connect(self.refresh_list)

        self.language = QComboBox()
        self.language.addItem("Tất cả ngôn ngữ")
        self.language.currentTextChanged.connect(self.refresh_list)

        refresh = QPushButton("↻ Catalog online")
        refresh.clicked.connect(self.refresh_online)

        top.addWidget(self.search, 1)
        top.addWidget(self.language)
        top.addWidget(refresh)
        root.addLayout(top)

        self.list = QListWidget()
        self.list.itemDoubleClicked.connect(
            lambda _item: self.accept_selected()
        )
        root.addWidget(self.list, 1)

        self.info = QLabel("")
        self.info.setWordWrap(True)
        self.info.setObjectName("hint")
        root.addWidget(self.info)

        warning = QLabel(
            "⚠ Mỗi Piper voice có license riêng. "
            "Hãy xem Model Card trước khi dùng cho nội dung thương mại."
        )
        warning.setWordWrap(True)
        warning.setObjectName("warnText")
        root.addWidget(warning)

        actions = QHBoxLayout()
        self.btn_download = QPushButton("⬇ Tải voice")
        self.btn_download.clicked.connect(self.download_selected)

        self.btn_try = QPushButton("▶ Nghe thử")
        self.btn_try.clicked.connect(self.try_selected)

        model_card = QPushButton("License / Model Card")
        model_card.clicked.connect(self.open_model_card)

        delete = QPushButton("Xóa offline")
        delete.setObjectName("danger")
        delete.clicked.connect(self.delete_selected)

        select = QPushButton("Chọn voice")
        select.setObjectName("success")
        select.clicked.connect(self.accept_selected)

        close = QPushButton("Đóng")
        close.clicked.connect(self.reject)

        actions.addWidget(self.btn_download)
        actions.addWidget(self.btn_try)
        actions.addWidget(model_card)
        actions.addWidget(delete)
        actions.addStretch(1)
        actions.addWidget(select)
        actions.addWidget(close)
        root.addLayout(actions)

        self.list.currentItemChanged.connect(
            lambda _cur, _prev: self.update_info()
        )

        self.populate_languages()
        self.refresh_list()

    def _selected_id(self):
        item = self.list.currentItem()
        return item.data(Qt.UserRole) if item else ""

    def populate_languages(self):
        current = self.language.currentText()
        languages = set()
        for voice_id, info in self.catalog.items():
            parsed = piper_engine.parse_voice_id(voice_id)
            languages.add(
                (info or {}).get("language")
                or parsed.get("language")
                or ""
            )

        self.language.blockSignals(True)
        self.language.clear()
        self.language.addItem("Tất cả ngôn ngữ")
        for lang in sorted(x for x in languages if x):
            label = piper_engine.LANGUAGE_NAMES.get(lang, lang)
            self.language.addItem(f"{label} [{lang}]", lang)

        if current and current != "Tất cả ngôn ngữ":
            idx = self.language.findText(current)
            if idx >= 0:
                self.language.setCurrentIndex(idx)
        self.language.blockSignals(False)

    def refresh_list(self):
        query = self.search.text().strip().lower()
        language = self.language.currentData()

        self.list.clear()
        installed = set(piper_engine.installed_voices(ROOT))

        candidates = dict(self.catalog)
        for voice_id in installed:
            candidates.setdefault(voice_id, {})

        for voice_id in sorted(candidates):
            info = candidates.get(voice_id) or {}
            parsed = piper_engine.parse_voice_id(voice_id)
            voice_lang = (
                info.get("language")
                or parsed.get("language")
                or ""
            )
            if language and voice_lang != language:
                continue

            label = piper_engine.voice_label(voice_id, info)
            haystack = f"{voice_id} {label}".lower()
            if query and query not in haystack:
                continue

            prefix = "✓ " if voice_id in installed else "⬇ "
            size = piper_engine.human_size(
                piper_engine.voice_size_bytes(info)
            )
            text = prefix + label
            if size:
                text += f" — {size}"

            item = QListWidgetItem(text)
            item.setData(Qt.UserRole, voice_id)
            if voice_id == self.selected_voice:
                item.setSelected(True)
            self.list.addItem(item)

        if self.list.count() and not self.list.currentItem():
            self.list.setCurrentRow(0)
        self.update_info()

    def update_info(self):
        voice_id = self._selected_id()
        if not voice_id:
            self.info.setText("Không có voice.")
            return

        info = self.catalog.get(voice_id, {}) or {}
        installed = piper_engine.is_voice_installed(
            ROOT, voice_id
        )
        size = piper_engine.human_size(
            piper_engine.voice_size_bytes(info)
        )
        parsed = piper_engine.parse_voice_id(voice_id)

        self.info.setText(
            f"ID: {voice_id} | "
            f"Language: {info.get('language') or parsed.get('language')} | "
            f"Quality: {info.get('quality') or parsed.get('quality')} | "
            f"{'✓ Offline' if installed else 'Chưa tải'}"
            + (f" | Download ~{size}" if size else "")
        )
        self.btn_download.setEnabled(not installed)
        self.btn_try.setEnabled(installed)

    def refresh_online(self):
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            self.catalog = piper_engine.fetch_catalog(ROOT)
            self.populate_languages()
            self.refresh_list()
            QMessageBox.information(
                self,
                "Piper",
                f"Đã tải catalog: {len(self.catalog)} voice.",
            )
        except Exception as e:
            QMessageBox.warning(self, "Piper", str(e))
        finally:
            QApplication.restoreOverrideCursor()

    def download_selected(self):
        voice_id = self._selected_id()
        if not voice_id:
            return

        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            piper_engine.download_voice(ROOT, voice_id)
            self.refresh_list()
            self.parent_window.refresh_piper_status()
            QMessageBox.information(
                self,
                "Piper",
                f"Đã tải voice offline:\n{voice_id}",
            )
        except Exception as e:
            QMessageBox.warning(self, "Piper", str(e))
        finally:
            QApplication.restoreOverrideCursor()

    def try_selected(self):
        voice_id = self._selected_id()
        if not voice_id:
            return
        self.parent_window.preview_piper_voice(
            voice_id,
            dialog_parent=self,
        )

    def open_model_card(self):
        voice_id = self._selected_id()
        if voice_id:
            QDesktopServices.openUrl(
                QUrl(piper_engine.model_card_url(voice_id))
            )

    def delete_selected(self):
        voice_id = self._selected_id()
        if not voice_id:
            return
        if not piper_engine.is_voice_installed(ROOT, voice_id):
            return

        answer = QMessageBox.question(
            self,
            "Xóa Piper voice",
            f"Xóa model offline?\n{voice_id}",
        )
        if answer != QMessageBox.Yes:
            return

        try:
            piper_engine.delete_voice(ROOT, voice_id)
            self.refresh_list()
            self.parent_window.refresh_piper_status()
        except Exception as e:
            QMessageBox.warning(self, "Piper", str(e))

    def accept_selected(self):
        voice_id = self._selected_id()
        if not voice_id:
            return
        self.selected_voice = voice_id
        self.accept()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        self.resize(1720, 980)
        self.setAcceptDrops(True)

        self.settings = SettingsStore(ROOT)
        self.project = AIProject()
        self.queue: list[str] = []
        self.worker = None
        self.preview_worker = None
        self.auto_detect_worker = None
        self._active_workers: list[Worker] = []
        self._restoring_state = False
        self._source_aspect_cache = {}
        self.stop_requested = False
        self.process_holder = {"process": None}
        self.editor_document = EditorDocument(self)
        self.preview_service = PreviewService()

        self.narration_path = ""
        self.accompaniment_path = ""
        self.vocals_path = ""
        self.preview_cues: list[tuple[float, float, str]] = []
        self.preview_sub_hidden = False
        self.processed_preview_path = ""
        self.preview_is_processed = False
        self.last_exported_path = ""
        self.preview_render_seq = 0
        self.preview_should_autoplay = False
        self.preview_previous_proxy = ""
        self.preview_loaded_path = ""
        self.preview_zoom_percent = 100

        # v1.0.12 Basic Video Editor state.
        # EditorDocument owns these lists.  The legacy names are compatibility
        # aliases until the remaining v1.0.13 handlers migrate panel by panel.
        self.editor_clips = self.editor_document.timeline.clips
        self.editor_layers = self.editor_document.timeline.layers
        self.editor_selected_clip = -1
        self.editor_selected_layer = -1
        self.editor_preview_path = ""
        self.editor_seamless_play = False
        self.editor_loading_clip = False
        self.editor_sync_guard = False
        self.editor_last_splitter_sizes = [760, 300]
        self.editor_document.replace_legacy_state(
            self.editor_clips, self.editor_layers
        )

        # v0.7.2 background-preview state
        self.preview_dirty = False
        self.preview_pending_path = ""
        self.preview_pending_position = 0
        self.preview_pending_was_playing = False

        self.preview_render_timer = QTimer(self)
        self.preview_render_timer.setSingleShot(True)
        self.preview_render_timer.setInterval(4200)
        self.preview_render_timer.timeout.connect(self.refresh_processed_preview)

        self.player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.player.setAudioOutput(self.audio_output)

        # v1.0: decoded frames go to our own QWidget canvas.
        # This avoids native video-surface z-order issues on Windows.
        self.video_sink = QVideoSink(self)
        if hasattr(self.player, "setVideoSink"):
            self.player.setVideoSink(self.video_sink)
        else:
            # Compatibility fallback for older PySide6 bindings.
            self.player.setVideoOutput(self.video_sink)

        # Live multi-track audio preview. These players stay synchronized with
        # the source video, so voice/music can be previewed without FFmpeg reload.
        self.narration_player = QMediaPlayer(self)
        self.narration_output = QAudioOutput(self)
        self.narration_player.setAudioOutput(self.narration_output)

        self.music_player = QMediaPlayer(self)
        self.music_output = QAudioOutput(self)
        self.music_player.setAudioOutput(self.music_output)

        self.accompaniment_player = QMediaPlayer(self)
        self.accompaniment_output = QAudioOutput(self)
        self.accompaniment_player.setAudioOutput(self.accompaniment_output)

        self._live_sync_guard = False

        self.autosave_timer = QTimer(self)
        self.autosave_timer.setSingleShot(True)
        self.autosave_timer.setInterval(700)
        self.autosave_timer.timeout.connect(self.autosave_project)

        self._build()
        self._style()
        self._load_settings_to_ui()

        self.player.positionChanged.connect(self.on_preview_position)
        self.player.durationChanged.connect(self.on_preview_duration)
        self.player.mediaStatusChanged.connect(self.on_preview_media_status)
        self.player.errorOccurred.connect(self.on_preview_player_error)
        self.player.playbackStateChanged.connect(self._preview_playback_state_changed)

        self.live_audio_sync_timer = QTimer(self)
        self.live_audio_sync_timer.setInterval(350)
        self.live_audio_sync_timer.timeout.connect(self.sync_live_audio_tracks)
        self.live_audio_sync_timer.start()
        self.music_player.mediaStatusChanged.connect(self.on_live_music_status)

        self.log_line(get_system_summary())
        self.status("Sẵn sàng")
        QTimer.singleShot(250, self.restore_last_project)

    # ==================================================================
    # BUILD UI
    # ==================================================================
    def _build(self):
        content = QWidget()
        main = QVBoxLayout(content)
        main.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        main.addWidget(self.tabs, 1)

        self.export_tab = QWidget()
        self.ai_tab = QWidget()
        self.download_tab = QWidget()
        self.settings_tab = QWidget()

        self.tabs.addTab(self.export_tab, "🎬 Video Exporter")
        self.tabs.addTab(self.ai_tab, "🧠 AI Studio")
        self.tabs.addTab(self.download_tab, "⬇ Downloader")
        self.tabs.addTab(self.settings_tab, "⚙ Settings")
        self.tabs.tabBar().hide()

        self._build_export_tab()
        self._build_ai_tab()
        self._build_download_tab()
        self._build_settings_tab()
        self._build_professional_editor_workspace()

        bottom = QHBoxLayout()
        self.status_label = QLabel("Ready")
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        bottom.addWidget(self.status_label)
        bottom.addWidget(self.progress, 1)
        main.addLayout(bottom)

        self.app_shell = AppShell(content)
        self.top_bar = self.app_shell.top_bar
        self.top_bar.sectionRequested.connect(self._open_top_section)
        self.top_bar.exportRequested.connect(self._top_export)
        self.top_bar.set_active("editor")
        self.setCentralWidget(self.app_shell)

    def _build_professional_editor_workspace(self):
        """Mount legacy working widgets in the new selection-driven NLE shell."""
        self.media_panel = MediaPanel()
        self.audio_tool_panel = ActionListPanel(
            "Audio", ("+ Add Background Music", "+ Add Audio File"),
            "Imported audio and AI narration appear here.",
        )
        self.text_tool_panel = ActionListPanel(
            "Text", ("+ Add Text", "Get Subtitle From Voice", "Choose SRT"),
            "Manual text and generated subtitles remain independent.",
        )
        self.blur_tool_panel = ActionListPanel(
            "Blur", ("+ Add Blur Zone",), "No blur zones yet.",
        )
        self.logo_tool_panel = ActionListPanel(
            "Logo", ("+ Add Logo / Image",), "No image overlays yet.",
        )
        self.context_inspector = InspectorPanel(self.editor_document.selection)
        self.context_inspector.propertyChanged.connect(
            self._apply_inspector_property
        )

        self.media_panel.addFilesRequested.connect(self.add_files)
        self.media_panel.importFolderRequested.connect(self._import_media_folder)
        self.media_panel.mediaAddRequested.connect(
            lambda path: self.editor_add_paths([path])
        )
        self.audio_tool_panel.primaryRequested.connect(self.choose_music_file)
        self.audio_tool_panel.secondaryRequested.connect(self._choose_audio_file)
        self.text_tool_panel.primaryRequested.connect(self.editor_add_text_layer)
        self.text_tool_panel.secondaryRequested.connect(self.get_sub_from_ai)
        self.text_tool_panel.tertiaryRequested.connect(self.choose_sub)
        self.blur_tool_panel.primaryRequested.connect(self.add_blur_zone)
        self.blur_tool_panel.itemSelected.connect(self._select_blur_from_tool)
        self.logo_tool_panel.primaryRequested.connect(self.editor_add_image_layer)
        self.logo_tool_panel.itemSelected.connect(self._select_image_from_tool)

        pages = {
            "media": self.media_panel,
            "audio": self.audio_tool_panel,
            "text": self.text_tool_panel,
            "blur": self.blur_tool_panel,
            "logo": self.logo_tool_panel,
        }
        self.video_editor_tab = EditorWorkspace(
            pages, self.legacy_preview_panel, self.context_inspector,
            self.editor_panel,
        )
        self.video_editor_tab.splitterSizesChanged.connect(self.schedule_autosave)
        self.editor_panel.setVisible(True)
        self.editor_panel.setTitle("Timeline")
        self.left_panel_btn.hide(); self.right_panel_btn.hide(); self.editor_toggle_btn.hide()
        self.tabs.insertTab(0, self.video_editor_tab, "Video Editor")
        self.tabs.setCurrentIndex(0)
        self._refresh_professional_panels()

    def _import_media_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Import Media Folder")
        if not folder:
            return
        extensions = {".mp4", ".mov", ".mkv", ".avi", ".webm", ".m4v"}
        paths = [str(path) for path in Path(folder).iterdir() if path.is_file() and path.suffix.lower() in extensions]
        if paths:
            self.add_paths(paths)

    def _choose_audio_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Add Audio", "", "Audio (*.wav *.mp3 *.m4a *.aac *.flac *.ogg)"
        )
        if path:
            self.music_file.setText(path)
            self._refresh_professional_panels()
            self.schedule_autosave()

    def _refresh_professional_panels(self):
        if not hasattr(self, "media_panel"):
            return
        self.media_panel.set_media(self.queue)
        audio = []
        for label, path in (("Background", self.music_file.text().strip()), ("AI narration", self.narration_path)):
            if path: audio.append(f"{label}: {Path(path).name}")
        self.audio_tool_panel.set_items(audio)
        self.blur_tool_panel.set_items([f"Blur {i + 1}" for i in range(len(self.blur_zones()))])
        images = [layer for layer in self.editor_layers if layer.get("type") == "image"]
        self.logo_tool_panel.set_items([Path(layer.get("path", "Image")).name for layer in images])

    def _select_blur_from_tool(self, index):
        if index < 0: return
        self.editor_document.selection.select("blur", f"blur:{index}")
        self.live_overlay.selected_type = "blur"; self.live_overlay.selected_index = index; self.live_overlay.update()
        self.context_inspector.load_properties("blur", {"strength": self.blur_opacity.value(), "opacity": self.blur_opacity.value()})

    def _select_image_from_tool(self, image_index):
        images = [(index, layer) for index, layer in enumerate(self.editor_layers) if layer.get("type") == "image"]
        if not (0 <= image_index < len(images)): return
        index, layer = images[image_index]
        self.editor_selected_layer = index
        self.editor_document.selection.select("image", str(layer.get("id")))
        self.live_overlay.selected_type = "editor_layer"; self.live_overlay.selected_index = index; self.live_overlay.update()
        self.context_inspector.load_properties("image", layer)

    def _apply_inspector_property(self, key, value):
        selection = self.editor_document.selection.current
        if selection is None: return
        if selection.kind == "video":
            item = next((clip for clip in self.editor_clips if clip.get("id") == selection.object_id), None)
            if item is not None:
                item[key] = value
                if key == "muted": item["muted"] = bool(value)
        elif selection.kind in ("text", "image", "logo"):
            layer = next((layer for layer in self.editor_layers if layer.get("id") == selection.object_id), None)
            if layer is not None:
                layer[key] = value
                if key == "text": layer["text"] = str(value)
            elif selection.object_id == "primary-overlay-text":
                widget_map = {"text": self.overlay_text, "font_size": self.overlay_size, "x": self.overlay_x, "y": self.overlay_y, "opacity": None}
                widget = widget_map.get(key)
                if widget is not None:
                    widget.setText(str(value)) if isinstance(widget, QLineEdit) else widget.setValue(value)
            elif selection.object_id == "primary-logo":
                widget_map = {"x": self.logo_x, "y": self.logo_y, "scale": self.logo_scale, "opacity": self.logo_opacity}
                if key in widget_map: widget_map[key].setValue(value)
        elif selection.kind == "subtitle":
            if key == "font_size": self.sub_size.setValue(int(value))
            elif key == "font_name": self.sub_font.setCurrentFont(QFont(str(value)))
            elif key == "text": return
        elif selection.kind == "blur":
            if key in ("strength", "opacity"): self.blur_opacity.setValue(int(value))
        self.editor_document.synchronize_legacy_items()
        self.update_live_overlay_state(); self.schedule_autosave()

    def _open_top_section(self, section):
        index_by_section = {
            "editor": 0,
            "voiceover": 1,
            "ai": 2,
            "download": 3,
            "settings": 4,
        }
        if section == "menu":
            self.status("Machine Studio v1.1.0 PRO FOUNDATION")
            return
        index = index_by_section.get(section)
        if index is not None:
            self.tabs.setCurrentIndex(index)
            self.top_bar.set_active(section)
            if section == "voiceover":
                self.status("Voiceover tools are available in the Video Editor audio panel.")

    def _top_export(self):
        self.tabs.setCurrentIndex(1)
        self.top_bar.set_active("editor")
        self.export_batch()

    # ------------------------------------------------------------------
    # VIDEO EXPORTER
    # ------------------------------------------------------------------
    def _build_export_tab(self):
        root = QVBoxLayout(self.export_tab)
        root.setSpacing(5)

        # 1. XUẤT VIDEO / BATCH — visually close to reference.
        batch = QGroupBox("Xuất Hàng Loạt")
        bl = QVBoxLayout(batch)
        top = QHBoxLayout()

        b_add = QPushButton("Chọn File")
        b_add.clicked.connect(self.add_files)
        b_merge = QPushButton("Ghép Video")
        b_merge.setObjectName("yellow")
        b_merge.clicked.connect(self.merge_selected)
        b_folder = QPushButton("Thư mục lưu")
        b_folder.clicked.connect(self.choose_output_dir)

        self.output_dir = QLineEdit()
        self.output_dir.setReadOnly(True)
        self.output_dir.setMinimumWidth(180)

        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(70)
        self.log.setObjectName("blackLog")
        self.log.setVisible(False)
        self.log_toggle_btn = QPushButton("▸ Log")
        self.log_toggle_btn.setCheckable(True)
        self.log_toggle_btn.setMaximumWidth(58)
        self.log_toggle_btn.toggled.connect(self.toggle_export_log)

        b_export = QPushButton("Xuất Video")
        b_export.setObjectName("success")
        b_export.setMinimumSize(120, 48)
        b_export.clicked.connect(self.export_batch)

        b_stop = QPushButton("Stop")
        b_stop.setObjectName("danger")
        b_stop.setMinimumSize(90, 48)
        b_stop.clicked.connect(self.stop_current)

        top.addWidget(b_add)
        top.addWidget(b_merge)
        top.addWidget(b_folder)
        top.addWidget(self.output_dir, 1)
        top.addWidget(self.log_toggle_btn)
        top.addWidget(self.log, 2)
        top.addWidget(b_export)
        top.addWidget(b_stop)
        bl.addLayout(top)

        queue_row = QHBoxLayout()
        self.queue_list = QListWidget()
        self.queue_list.setMaximumHeight(44)
        self.queue_list.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.queue_list.currentRowChanged.connect(self.queue_selection_changed)

        b_remove = QPushButton("Xóa")
        b_remove.setObjectName("dangerSmall")
        b_remove.clicked.connect(self.remove_selected_queue)
        queue_row.addWidget(self.queue_list, 1)
        queue_row.addWidget(b_remove)
        bl.addLayout(queue_row)
        root.addWidget(batch)

        # Main workspace is a vertical splitter: top = exporter/preview/voice,
        # bottom = Basic Editor. Hiding the editor now gives all height back
        # to the preview instead of leaving stale/overflowing geometry.
        self.export_vertical_splitter = QSplitter(Qt.Vertical)
        self.export_vertical_splitter.setChildrenCollapsible(False)
        self.export_vertical_splitter.setHandleWidth(7)
        root.addWidget(self.export_vertical_splitter, 1)

        body = QSplitter(Qt.Horizontal)
        self.export_body_splitter = body
        body.setChildrenCollapsible(False)
        body.setHandleWidth(7)
        self.export_vertical_splitter.addWidget(body)

        # ==============================================================
        # LEFT: CÀI ĐẶT XUẤT
        # ==============================================================
        left_scroll = QScrollArea()
        self.export_left_panel = left_scroll
        left_scroll.setMinimumWidth(260)
        left_scroll.setWidgetResizable(True)
        left = QWidget()
        left_scroll.setWidget(left)
        ll = QVBoxLayout(left)
        ll.setSpacing(8)

        export_box = QGroupBox("Cài Đặt Xuất")
        eg = QGridLayout(export_box)

        self.resolution = QComboBox()
        self.resolution.addItems([
            "720x1280 (HD - Nhanh)",
            "1080x1920 (Full HD)",
            "1080x1920 (Full HD 60FPS)",
            "1440x2560 (2K)",
            "2160x3840 (4K)",
            "1080x1440 (3:4)",
            "1920x1080 (YouTube)",
            "Original",
        ])
        self.codec = QComboBox()
        self.codec.addItems(["Auto", "H.264", "H.265", "AV1"])
        self.encoder = QComboBox()
        self.encoder.addItems(["Auto (GPU)", "GPU", "CPU"])

        eg.addWidget(QLabel("Khung hình"), 0, 0)
        eg.addWidget(self.resolution, 0, 1)
        eg.addWidget(QLabel("Codec"), 1, 0)
        eg.addWidget(self.codec, 1, 1)
        eg.addWidget(QLabel("Encode"), 2, 0)
        eg.addWidget(self.encoder, 2, 1)

        self.wheel_input_lock = QCheckBox("🔒 Khóa lăn thông số")
        self.wheel_input_lock.setChecked(True)
        self.wheel_input_lock.setToolTip(
            "Bật: cuộn trang không bao giờ làm thay đổi số/combobox. "
            "Tắt: phải click vào đúng ô rồi mới lăn được; rời chuột khỏi ô sẽ khóa lại."
        )
        self.wheel_input_lock.toggled.connect(self.set_wheel_input_lock)
        eg.addWidget(self.wheel_input_lock, 3, 0, 1, 2)

        wheel_hint = QLabel(
            "Mặc định khóa. Khi mở khóa, vẫn phải click đúng ô trước khi dùng con lăn."
        )
        wheel_hint.setObjectName("hint")
        wheel_hint.setWordWrap(True)
        eg.addWidget(wheel_hint, 4, 0, 1, 2)
        ll.addWidget(export_box)

        privacy = QGroupBox("Bảo vệ quyền riêng tư & Tối ưu file")
        pg = QVBoxLayout(privacy)
        self.strip_metadata = QCheckBox("Tối ưu metadata + xóa thông tin riêng tư trong file")
        self.strip_metadata.setChecked(True)
        pg.addWidget(self.strip_metadata)
        note = QLabel("• Giữ chất lượng hình ảnh, tối ưu MP4 và loại metadata không cần thiết.")
        note.setObjectName("hint")
        note.setWordWrap(True)
        pg.addWidget(note)
        ll.addWidget(privacy)

        # BLUR ZONES
        blur = QGroupBox("Blur zones")
        bg = QGridLayout(blur)
        self.blur_enabled = QCheckBox("Bật")
        self.blur_style = QComboBox()
        self.blur_style.addItems(["Đen mờ", "Trong mờ"])
        self.blur_opacity = QSpinBox()
        self.blur_opacity.setRange(1, 100)
        self.blur_opacity.setValue(20)
        self.blur_opacity.setSuffix(" %")

        self.auto_cover_source_sub = QCheckBox("Tự động che phụ đề gốc có sẵn trên video")
        self.auto_cover_source_sub.toggled.connect(self.on_auto_sub_toggle)
        self.auto_sub_detect_btn = QPushButton("Dò vùng sub tự động")
        self.auto_sub_detect_btn.clicked.connect(self.detect_source_subtitle_zone)
        self.auto_sub_status = QLabel("Auto Sub: chưa dò")
        self.auto_sub_status.setObjectName("hint")

        self.blur_zone_list = QListWidget()
        self.blur_zone_list.setMaximumHeight(78)
        self.blur_zone_list.currentRowChanged.connect(self.load_selected_blur_params)

        self.blur_params_toggle = QPushButton("▸ Thông số vùng")
        self.blur_params_toggle.setCheckable(True)
        self.blur_params_toggle.toggled.connect(self.toggle_blur_params)

        self.blur_params_panel = QWidget()
        bpf = QGridLayout(self.blur_params_panel)
        bpf.setContentsMargins(0, 4, 0, 0)

        self.blur_x_param = QDoubleSpinBox()
        self.blur_y_param = QDoubleSpinBox()
        self.blur_w_param = QDoubleSpinBox()
        self.blur_h_param = QDoubleSpinBox()
        for spin in [self.blur_x_param, self.blur_y_param, self.blur_w_param, self.blur_h_param]:
            spin.setRange(0, 100)
            spin.setDecimals(1)
            spin.setSingleStep(0.5)
            spin.setSuffix(" %")
            spin.valueChanged.connect(self.blur_params_changed)

        bpf.addWidget(QLabel("X"), 0, 0); bpf.addWidget(self.blur_x_param, 0, 1)
        bpf.addWidget(QLabel("Y"), 0, 2); bpf.addWidget(self.blur_y_param, 0, 3)
        bpf.addWidget(QLabel("W"), 1, 0); bpf.addWidget(self.blur_w_param, 1, 1)
        bpf.addWidget(QLabel("H"), 1, 2); bpf.addWidget(self.blur_h_param, 1, 3)
        mouse_hint = QLabel("Kéo vùng trực tiếp trên Preview; kéo ô vuông góc phải để resize.")
        mouse_hint.setObjectName("hint")
        mouse_hint.setWordWrap(True)
        bpf.addWidget(mouse_hint, 2, 0, 1, 4)
        self.blur_params_panel.setVisible(False)

        add_zone = QPushButton("+ Vùng thủ công")
        add_zone.setObjectName("greenSmall")
        add_zone.setMaximumWidth(120)
        add_zone.clicked.connect(lambda _checked=False: self.add_blur_zone())

        edit_zone = QPushButton("Sửa")
        edit_zone.setMaximumWidth(48)
        edit_zone.clicked.connect(self.edit_blur_zone)

        remove_zone = QPushButton("−")
        remove_zone.setObjectName("dangerSmall")
        remove_zone.setMaximumWidth(34)
        remove_zone.clicked.connect(self.remove_blur_zone)

        bg.addWidget(self.blur_enabled, 0, 0)
        bg.addWidget(self.blur_style, 0, 1)
        bg.addWidget(QLabel("Độ đậm"), 1, 0)
        bg.addWidget(self.blur_opacity, 1, 1)
        bg.addWidget(self.auto_cover_source_sub, 2, 0, 1, 2)
        auto_row = QHBoxLayout()
        auto_row.addWidget(self.auto_sub_detect_btn)
        auto_row.addWidget(self.auto_sub_status, 1)
        bg.addLayout(auto_row, 3, 0, 1, 2)
        bg.addWidget(self.blur_zone_list, 4, 0, 1, 2)
        bg.addWidget(self.blur_params_toggle, 5, 0, 1, 2)
        bg.addWidget(self.blur_params_panel, 6, 0, 1, 2)
        zr = QHBoxLayout()
        zr.addWidget(add_zone); zr.addWidget(edit_zone); zr.addWidget(remove_zone)
        zr.addStretch(1)
        bg.addLayout(zr, 7, 0, 1, 2)
        ll.addWidget(blur)

        # SPEED + LOGO
        advanced = QGroupBox("Tùy chỉnh")
        ag = QGridLayout(advanced)

        self.speed_enabled = QCheckBox("Tốc độ phát")
        self.play_speed = QDoubleSpinBox()
        self.play_speed.setRange(0.25, 4.0)
        self.play_speed.setValue(1.0)
        self.play_speed.setSingleStep(0.05)
        self.play_speed.setSuffix("x")

        self.logo_enabled = QCheckBox("Logo / Watermark")
        self.logo_path = QLineEdit()
        self.logo_path.setReadOnly(True)
        choose_logo = QPushButton("Chọn ảnh")
        choose_logo.clicked.connect(self.choose_logo)

        self.logo_pos = QComboBox()
        self.logo_pos.addItems(["Top-right", "Top-left", "Bottom-right", "Bottom-left", "Custom"])
        self.logo_scale = QSpinBox()
        self.logo_scale.setRange(3, 50)
        self.logo_scale.setValue(12)
        self.logo_scale.setSuffix(" %")
        self.logo_opacity = QSpinBox()
        self.logo_opacity.setRange(1, 100)
        self.logo_opacity.setValue(100)
        self.logo_opacity.setSuffix(" %")
        self.logo_remove_bg = QCheckBox("Xóa nền trắng logo")
        self.logo_x = QDoubleSpinBox(); self.logo_x.setRange(1,99); self.logo_x.setValue(88); self.logo_x.setSuffix(" %")
        self.logo_y = QDoubleSpinBox(); self.logo_y.setRange(1,99); self.logo_y.setValue(10); self.logo_y.setSuffix(" %")
        self.logo_params_toggle = QPushButton("▸ Thông số Logo")
        self.logo_params_toggle.setCheckable(True)
        self.logo_params_toggle.toggled.connect(self.toggle_logo_params)
        self.logo_params_panel = QWidget()
        lpg = QGridLayout(self.logo_params_panel); lpg.setContentsMargins(0,2,0,0)
        lpg.addWidget(QLabel("X"),0,0); lpg.addWidget(self.logo_x,0,1)
        lpg.addWidget(QLabel("Y"),0,2); lpg.addWidget(self.logo_y,0,3)
        lpg.addWidget(QLabel("Kích thước"),1,0); lpg.addWidget(self.logo_scale,1,1)
        lpg.addWidget(QLabel("Độ trong"),1,2); lpg.addWidget(self.logo_opacity,1,3)
        lh=QLabel("Kéo Logo trực tiếp trên Preview; kéo ô vuông góc phải để đổi kích thước."); lh.setObjectName("hint"); lh.setWordWrap(True); lpg.addWidget(lh,2,0,1,4)
        self.logo_params_panel.setVisible(False)

        ag.addWidget(self.speed_enabled, 0, 0)
        ag.addWidget(self.play_speed, 0, 1)
        ag.addWidget(self.logo_enabled, 1, 0, 1, 2)
        ag.addWidget(self.logo_path, 2, 0)
        ag.addWidget(choose_logo, 2, 1)
        ag.addWidget(QLabel("Preset vị trí"), 3, 0)
        ag.addWidget(self.logo_pos, 3, 1)
        ag.addWidget(self.logo_remove_bg, 4, 0, 1, 2)
        ag.addWidget(self.logo_params_toggle, 5, 0, 1, 2)
        ag.addWidget(self.logo_params_panel, 6, 0, 1, 2)
        ll.addWidget(advanced)

        # "CÀI ĐẶT NÂNG CAO" chỉ còn NỀN 2 BÊN + CHỮ PHỦ.
        extra = QGroupBox("Cài Đặt Nâng Cao")
        xg = QVBoxLayout(extra)

        side = QGroupBox("Nền 2 bên")
        sg = QGridLayout(side)
        self.side_bg_enabled = QCheckBox("Bật")
        self.side_bg_type = QComboBox()
        self.side_bg_type.addItems(["Mờ video", "Đen"])
        sg.addWidget(self.side_bg_enabled, 0, 0)
        sg.addWidget(QLabel("Kiểu"), 1, 0)
        sg.addWidget(self.side_bg_type, 1, 1)
        xg.addWidget(side)

        overlay = QGroupBox("Chữ phủ")
        og = QGridLayout(overlay)
        self.overlay_enabled = QCheckBox("Bật")
        self.overlay_text = QLineEdit()
        self.overlay_text.setPlaceholderText("Nội dung chữ phủ...")
        self.overlay_font = QFontComboBox()
        self.overlay_size = QSpinBox()
        self.overlay_size.setRange(12, 120)
        self.overlay_size.setValue(34)
        self.overlay_color = QLineEdit("#FFFFFF")
        pick_overlay_color = QPushButton("Màu")
        pick_overlay_color.clicked.connect(lambda: self.pick_color(self.overlay_color))
        self.overlay_pos = QComboBox()
        self.overlay_pos.addItems(["Top-left", "Top-right", "Bottom-left", "Bottom-right", "Custom"])
        self.overlay_x = QDoubleSpinBox(); self.overlay_x.setRange(2,98); self.overlay_x.setValue(12); self.overlay_x.setSuffix(" %")
        self.overlay_y = QDoubleSpinBox(); self.overlay_y.setRange(2,98); self.overlay_y.setValue(8); self.overlay_y.setSuffix(" %")
        self.overlay_params_toggle = QPushButton("▸ Thông số Chữ phủ")
        self.overlay_params_toggle.setCheckable(True)
        self.overlay_params_toggle.toggled.connect(self.toggle_overlay_params)
        self.overlay_params_panel = QWidget()
        opg=QGridLayout(self.overlay_params_panel); opg.setContentsMargins(0,2,0,0)
        opg.addWidget(QLabel("X"),0,0); opg.addWidget(self.overlay_x,0,1)
        opg.addWidget(QLabel("Y"),0,2); opg.addWidget(self.overlay_y,0,3)
        oh=QLabel("Kéo chữ phủ trực tiếp trên Preview; kéo ô vuông góc phải để đổi cỡ."); oh.setObjectName("hint"); oh.setWordWrap(True); opg.addWidget(oh,1,0,1,4)
        self.overlay_params_panel.setVisible(False)

        og.addWidget(self.overlay_enabled, 0, 0)
        og.addWidget(self.overlay_text, 1, 0, 1, 2)
        og.addWidget(QLabel("Font"), 2, 0); og.addWidget(self.overlay_font, 2, 1)
        og.addWidget(QLabel("Cỡ"), 3, 0); og.addWidget(self.overlay_size, 3, 1)
        og.addWidget(self.overlay_color, 4, 0); og.addWidget(pick_overlay_color, 4, 1)
        og.addWidget(QLabel("Preset vị trí"), 5, 0); og.addWidget(self.overlay_pos, 5, 1)
        og.addWidget(self.overlay_params_toggle, 6, 0, 1, 2)
        og.addWidget(self.overlay_params_panel, 7, 0, 1, 2)
        xg.addWidget(overlay)

        ll.addWidget(extra)
        ll.addStretch(1)

        # ==============================================================
        # CENTER: PREVIEW
        # ==============================================================
        center = QWidget()
        self.legacy_preview_panel = center
        cl = QVBoxLayout(center)
        cl.setContentsMargins(3, 3, 3, 3)

        phead = QHBoxLayout()
        self.left_panel_btn = QPushButton("☰ Cài đặt")
        self.left_panel_btn.setCheckable(True)
        self.left_panel_btn.setChecked(True)
        self.left_panel_btn.setMaximumWidth(84)
        self.left_panel_btn.toggled.connect(
            lambda checked: self.toggle_export_side_panel("left", checked)
        )
        self.right_panel_btn = QPushButton("Lồng tiếng ☰")
        self.right_panel_btn.setCheckable(True)
        self.right_panel_btn.setChecked(True)
        self.right_panel_btn.setMaximumWidth(96)
        self.right_panel_btn.toggled.connect(
            lambda checked: self.toggle_export_side_panel("right", checked)
        )
        phead.addWidget(self.left_panel_btn)
        phead.addWidget(QLabel("Preview"))
        phead.addWidget(QLabel("Canvas"))
        self.preview_ratio_combo = QComboBox()
        self.preview_ratio_combo.addItems(["Original", "16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "2:1", "5:4", "4:5"])
        self.preview_ratio_combo.currentTextChanged.connect(self.set_project_aspect_ratio)
        phead.addWidget(self.preview_ratio_combo)

        phead.addSpacing(10)
        zoom_out = QPushButton("−")
        zoom_out.setMaximumWidth(34)
        zoom_out.setToolTip("Zoom Out Preview")
        zoom_out.clicked.connect(lambda: self.change_preview_zoom(-10))
        self.preview_zoom_label = QLabel("100%")
        self.preview_zoom_label.setMinimumWidth(46)
        self.preview_zoom_label.setAlignment(Qt.AlignCenter)
        zoom_in = QPushButton("+")
        zoom_in.setMaximumWidth(34)
        zoom_in.setToolTip("Zoom In Preview")
        zoom_in.clicked.connect(lambda: self.change_preview_zoom(10))
        zoom_fit = QPushButton("Fit")
        zoom_fit.setMaximumWidth(46)
        zoom_fit.setToolTip(
            "Fit Preview về 100%. Khi zoom > 100%, giữ chuột giữa để pan."
        )
        zoom_fit.clicked.connect(self.reset_preview_zoom)
        phead.addWidget(zoom_out)
        phead.addWidget(self.preview_zoom_label)
        phead.addWidget(zoom_in)
        phead.addWidget(zoom_fit)
        self.preview_zoom_combo = QComboBox()
        self.preview_zoom_combo.addItems(["Fit", "Fill", "50%", "75%", "100%", "125%", "150%", "200%", "300%"])
        self.preview_zoom_combo.setCurrentText("100%")
        self.preview_zoom_combo.currentTextChanged.connect(self._preview_zoom_mode_changed)
        phead.addWidget(self.preview_zoom_combo)

        phead.addStretch(1)
        phead.addWidget(self.right_panel_btn)
        self.preview_state = QLabel("Stopped")
        self.preview_state.setObjectName("warnText")
        phead.addWidget(self.preview_state)
        cl.addLayout(phead)

        self.preview_frame = QFrame()
        self.preview_frame.setObjectName("previewFrame")
        preview_layout = QVBoxLayout(self.preview_frame)
        preview_layout.setContentsMargins(0, 0, 0, 0)

        # One surface contains BOTH decoded video and editor effects.
        self.live_overlay = InteractivePreviewOverlay()
        self.live_overlay.blurZoneChanged.connect(self.on_live_blur_zone_changed)
        self.live_overlay.subtitleGeometryChanged.connect(self.on_live_sub_geometry_changed)
        self.live_overlay.logoGeometryChanged.connect(self.on_live_logo_geometry_changed)
        self.live_overlay.overlayTextGeometryChanged.connect(self.on_live_text_geometry_changed)
        self.live_overlay.editorLayerGeometryChanged.connect(
            self.on_live_editor_layer_geometry_changed
        )
        self.live_overlay.interactionFinished.connect(self.on_live_overlay_interaction_finished)
        self.live_overlay.selectionChanged.connect(self.on_live_overlay_selection_changed)
        self.video_sink.videoFrameChanged.connect(self.live_overlay.set_video_frame)

        preview_layout.addWidget(self.live_overlay)
        cl.addWidget(self.preview_frame, 1)

        timeline = QHBoxLayout()
        self.preview_current = QLabel("00:00")
        self.timeline_slider = QSlider(Qt.Horizontal)
        self.timeline_slider.setRange(0, 0)
        self.timeline_slider.sliderMoved.connect(self.seek_preview)
        self.preview_total = QLabel("00:00")
        timeline.addWidget(self.preview_current)
        timeline.addWidget(self.timeline_slider, 1)
        timeline.addWidget(self.preview_total)
        cl.addLayout(timeline)

        playrow = QHBoxLayout()
        self.editor_toggle_btn = QPushButton("✂ Video Editor")
        self.editor_toggle_btn.setCheckable(True)
        self.editor_toggle_btn.toggled.connect(self.toggle_basic_editor)

        self.hide_sub_btn = QPushButton("Hide Sub")
        self.hide_sub_btn.clicked.connect(self.toggle_preview_sub)
        self.preview_play_button = QPushButton("▶ Play")
        self.preview_play_button.setObjectName("success")
        self.preview_play_button.clicked.connect(self.toggle_play)
        start_button = QPushButton("|◀")
        start_button.setToolTip("Go to start")
        start_button.clicked.connect(lambda: self.editor_seek_global(0.0) if self.editor_timeline_active() else self.player.setPosition(0))
        end_button = QPushButton("▶|")
        end_button.setToolTip("Go to end")
        end_button.clicked.connect(lambda: self.editor_seek_global(self.editor_master_total()) if self.editor_timeline_active() else self.player.setPosition(self.player.duration()))
        self.update_preview_btn = QPushButton("↻ Render cache ngầm")
        self.update_preview_btn.setObjectName("cyan")
        self.update_preview_btn.clicked.connect(self.preview_button_action)

        live_btn = QPushButton("⚡ Live Preview")
        live_btn.clicked.connect(self.return_to_live_source)

        playrow.addStretch(1)
        playrow.addWidget(start_button)
        playrow.addWidget(self.editor_toggle_btn)
        playrow.addWidget(self.hide_sub_btn)
        playrow.addWidget(self.preview_play_button)
        playrow.addWidget(end_button)
        playrow.addWidget(self.update_preview_btn)
        playrow.addWidget(live_btn)
        playrow.addStretch(1)
        cl.addLayout(playrow)

        # Preview / final mix audio controls like reference.
        audio_strip = QFrame()
        audio_strip.setObjectName("audioStrip")
        ar = QHBoxLayout(audio_strip)
        ar.setContentsMargins(8, 5, 8, 5)

        self.mute_music = QCheckBox("Tắt nhạc nền")
        self.mute_music.toggled.connect(self.update_audio_control_labels)
        self.mute_original_voice = QCheckBox("Tắt giọng gốc")
        self.mute_original_voice.toggled.connect(self.update_audio_control_labels)

        ar.addWidget(self.mute_music)
        ar.addWidget(self.mute_original_voice)

        self.source_volume = QSlider(Qt.Horizontal)
        self.source_volume.setRange(0, 100); self.source_volume.setValue(30)
        self.source_volume.setMaximumWidth(110)
        self.source_volume.valueChanged.connect(self.preview_source_volume_changed)
        self.source_volume_label = QLabel("Âm gốc: 30%")

        self.narration_volume = QSlider(Qt.Horizontal)
        self.narration_volume.setRange(0, 150); self.narration_volume.setValue(100)
        self.narration_volume.setMaximumWidth(110)
        self.narration_volume_label = QLabel("Giọng đọc: 100%")
        self.narration_volume.valueChanged.connect(self.update_audio_control_labels)

        self.music_volume = QSlider(Qt.Horizontal)
        self.music_volume.setRange(0, 100); self.music_volume.setValue(5)
        self.music_volume.setMaximumWidth(110)
        self.music_volume_label = QLabel("Nhạc nền: 5%")
        self.music_volume.valueChanged.connect(self.update_audio_control_labels)

        ar.addWidget(self.source_volume_label); ar.addWidget(self.source_volume)
        ar.addWidget(self.narration_volume_label); ar.addWidget(self.narration_volume)
        ar.addWidget(self.music_volume_label); ar.addWidget(self.music_volume)
        cl.addWidget(audio_strip)

        # ==============================================================
        # RIGHT: VOICE FIRST -> SUB/DỊCH SECOND
        # ==============================================================
        right_scroll = QScrollArea()
        self.export_right_panel = right_scroll
        right_scroll.setMinimumWidth(280)
        right_scroll.setWidgetResizable(True)
        right = QWidget()
        right_scroll.setWidget(right)
        rl = QVBoxLayout(right)
        rl.setSpacing(8)

        # Voice first.
        voice_box = QGroupBox("🔑 Lồng Tiếng (TTS)")
        vg = QGridLayout(voice_box)

        self.script_ready_label = QLabel("Kịch bản AI: chưa có")
        self.script_ready_label.setObjectName("readyText")
        self.tts_engine = QComboBox()
        self.tts_engine.addItems([
            "Piper Offline (Free)",
            "Gemini TTS",
            "Edge TTS",
            "Windows SAPI",
        ])

        self.tts_auto_fallback = QCheckBox("Gemini lỗi → tự chuyển Edge TTS")
        self.tts_auto_fallback.setChecked(True)
        self.tts_auto_fallback.setToolTip(
            "Nếu Gemini TTS trả 429/quota/rate-limit, app tự chuyển sang "
            "Edge TTS cho đoạn lỗi và các đoạn còn lại."
        )

        self.tts_fallback_voice = QComboBox()
        self.tts_fallback_voice.setEditable(True)
        self.tts_fallback_voice.addItems([
            "en-US-JennyNeural",
            "en-US-GuyNeural",
            "en-US-AriaNeural",
            "en-US-DavisNeural",
        ])

        self.tts_voice = QComboBox()
        self.tts_voice.setEditable(True)

        self.tts_voice_manager = QPushButton("Chọn giọng...")
        self.tts_voice_manager.clicked.connect(
            self.open_tts_voice_manager
        )

        self.piper_download_voice = QPushButton("⬇ Tải voice")
        self.piper_download_voice.clicked.connect(
            self.download_current_piper_voice
        )

        self.piper_try_voice = QPushButton("▶ Thử")
        self.piper_try_voice.clicked.connect(
            lambda: self.preview_piper_voice(
                self.tts_voice.currentText().strip()
            )
        )

        self.piper_status = QLabel("")
        self.piper_status.setObjectName("hint")

        self.tts_engine.currentTextChanged.connect(
            self.on_tts_engine_changed
        )
        self.tts_voice.currentTextChanged.connect(
            lambda _text: self.refresh_piper_status()
        )
        self.tts_speed = QDoubleSpinBox()
        self.tts_speed.setRange(0.5, 2.0)
        self.tts_speed.setValue(1.0)
        self.tts_speed.setSingleStep(0.05)
        self.tts_speed.setSuffix("x")
        self.tts_sync_label = QLabel("100% — theo voice thật")
        self.tts_sync_label.setObjectName("readyText")

        self.voice_file = QLineEdit()
        self.voice_file.setReadOnly(True)
        choose_voice = QPushButton("📁")
        choose_voice.clicked.connect(self.choose_voice_file)

        self.music_file = QLineEdit()
        self.music_file.setReadOnly(True)
        choose_music = QPushButton("📁")
        choose_music.clicked.connect(self.choose_music_file)

        self.voice_status = QLabel("Sẵn sàng.")
        create_voice = QPushButton("Tạo Giọng Đọc")
        create_voice.setObjectName("cyan")
        create_voice.clicked.connect(self.export_generate_voice)
        stop_voice = QPushButton("Dừng")
        stop_voice.setObjectName("danger")
        stop_voice.clicked.connect(self.stop_current)
        separate_voice = QPushButton("Tách giọng gốc")
        separate_voice.clicked.connect(self.separate_original_vocals)

        vg.addWidget(self.script_ready_label, 0, 0, 1, 4)
        vg.addWidget(QLabel("Engine"), 1, 0)
        vg.addWidget(self.tts_engine, 1, 1, 1, 3)

        vg.addWidget(QLabel("Giọng"), 2, 0)
        vg.addWidget(self.tts_voice, 2, 1, 1, 2)
        vg.addWidget(self.tts_voice_manager, 2, 3)

        piper_actions = QHBoxLayout()
        piper_actions.addWidget(self.piper_download_voice)
        piper_actions.addWidget(self.piper_try_voice)
        piper_actions.addWidget(self.piper_status, 1)
        vg.addLayout(piper_actions, 3, 0, 1, 4)

        vg.addWidget(QLabel("Tốc"), 4, 0)
        vg.addWidget(self.tts_speed, 4, 1)
        vg.addWidget(QLabel("Khớp TTS"), 4, 2)
        vg.addWidget(self.tts_sync_label, 4, 3)

        vg.addWidget(self.tts_auto_fallback, 5, 0, 1, 2)
        vg.addWidget(QLabel("Edge fallback"), 5, 2)
        vg.addWidget(self.tts_fallback_voice, 5, 3)

        tts_route_note = QLabel(
            "Piper = offline/free sau khi tải model. "
            "Gemini giữ Puck/Kore; Edge/SAPI vẫn dùng riêng."
        )
        tts_route_note.setObjectName("hint")
        tts_route_note.setWordWrap(True)
        vg.addWidget(tts_route_note, 6, 0, 1, 4)

        vg.addWidget(QLabel("File giọng"), 7, 0)
        vg.addWidget(self.voice_file, 7, 1, 1, 2)
        vg.addWidget(choose_voice, 7, 3)

        vg.addWidget(QLabel("Nhạc nền"), 8, 0)
        vg.addWidget(self.music_file, 8, 1, 1, 2)
        vg.addWidget(choose_music, 8, 3)

        br = QHBoxLayout()
        br.addWidget(create_voice, 1)
        br.addWidget(stop_voice)
        br.addWidget(separate_voice)
        vg.addLayout(br, 9, 0, 1, 4)
        vg.addWidget(self.voice_status, 10, 0, 1, 4)

        QTimer.singleShot(0, self.on_tts_engine_changed)
        rl.addWidget(voice_box)

        # Subtitle + translation second.
        sub_box = QGroupBox("Setting Sub & Dịch")
        sg = QVBoxLayout(sub_box)

        self.sub_enabled = QCheckBox("Bật phụ đề")
        self.sub_enabled.setChecked(False)
        self.sub_enabled.toggled.connect(self.update_subtitle_preview_style)
        sg.addWidget(self.sub_enabled)

        translate = QGroupBox("Dịch thuật")
        tg = QGridLayout(translate)
        self.translate_engine = QComboBox()
        self.translate_engine.addItems(["AI Provider (Settings)"])
        self.translate_target = QComboBox()
        self.translate_target.addItems(["English US", "Tiếng Việt", "中文"])
        self.translate_style = QComboBox()
        self.translate_style.addItems([
            "Tự nhiên - video US",
            "Ngắn gọn - subtitle",
            "Giữ thuật ngữ kỹ thuật",
            "Sát nghĩa",
        ])
        b_translate = QPushButton("Dịch Sub")
        b_translate.setObjectName("purple")
        b_translate.clicked.connect(self.translate_current_srt)

        tg.addWidget(self.translate_engine, 0, 0, 1, 2)
        tg.addWidget(QLabel("Dịch:"), 0, 2)
        tg.addWidget(self.translate_target, 0, 3)
        tg.addWidget(QLabel("Phong cách"), 1, 0)
        tg.addWidget(self.translate_style, 1, 1, 1, 2)
        tg.addWidget(b_translate, 1, 3)
        sg.addWidget(translate)

        style = QGroupBox("Kiểu phụ đề")
        st = QGridLayout(style)
        self.sub_preset = QComboBox()
        self.sub_preset.addItems(subtitle_engine.list_presets())
        self.sub_preset.currentTextChanged.connect(self.apply_named_subtitle_preset)
        b_presets = QPushButton("Chọn mẫu")
        b_presets.clicked.connect(self.open_subtitle_preset_dialog)

        self.sub_font = QFontComboBox()
        self.sub_size = QSpinBox(); self.sub_size.setRange(12, 120); self.sub_size.setValue(48)
        self.sub_color = QLineEdit("#FFFFFF")
        b_sub_color = QPushButton("Màu")
        b_sub_color.clicked.connect(lambda: self.pick_color(self.sub_color))
        self.sub_outline = QDoubleSpinBox(); self.sub_outline.setRange(0, 10); self.sub_outline.setValue(3.0)
        self.sub_outline.setSingleStep(0.5)
        self.sub_outline_color = QLineEdit("#000000")
        b_outline_color = QPushButton("Viền")
        b_outline_color.clicked.connect(lambda: self.pick_color(self.sub_outline_color))
        self.sub_bold = QCheckBox("Đậm"); self.sub_bold.setChecked(True)
        self.sub_italic = QCheckBox("Nghiêng")
        self.sub_background_box = QCheckBox("Nền sub")
        self.sub_bg_color = QLineEdit("#000000")
        self.sub_bg_opacity = QSpinBox(); self.sub_bg_opacity.setRange(0,100); self.sub_bg_opacity.setValue(65)
        self.sub_bg_opacity.setSuffix(" %")
        self.sub_shadow = QDoubleSpinBox(); self.sub_shadow.setRange(0,10); self.sub_shadow.setValue(1.0)
        self.sub_x = QSpinBox(); self.sub_x.setRange(5,95); self.sub_x.setValue(50); self.sub_x.setSuffix(" %")
        self.sub_y = QSpinBox(); self.sub_y.setRange(5,95); self.sub_y.setValue(86); self.sub_y.setSuffix(" %")
        self.sub_width = QSpinBox(); self.sub_width.setRange(20,96); self.sub_width.setValue(80); self.sub_width.setSuffix(" %")
        self.sub_max_chars = QSpinBox(); self.sub_max_chars.setRange(10,80); self.sub_max_chars.setValue(30)
        self.sub_single_line = QCheckBox("1 dòng tự động")
        self.sub_single_line.setChecked(True)
        self.sub_min_font = QSpinBox(); self.sub_min_font.setRange(12,60); self.sub_min_font.setValue(24)
        self.sub_min_font.setVisible(False)
        self.sub_auto_layout = QCheckBox("Căn giữa + bám Auto Blur")
        self.sub_auto_layout.setChecked(True)
        self.sub_inner_margin = QSpinBox()
        self.sub_inner_margin.setRange(0, 15)
        self.sub_inner_margin.setValue(5)
        self.sub_inner_margin.setSuffix(" %")
        self.sub_uppercase = QCheckBox("VIẾT HOA")

        self.sub_animation = QComboBox()
        self.sub_animation.addItems([
            "Không",
            "Pop",
            "Bounce",
            "Slide Up",
            "Fade",
            "Karaoke",
            "Typewriter",
            "Word Pop Sync",
        ])
        self.sub_anim_duration = QSpinBox()
        self.sub_anim_duration.setRange(60, 1200)
        self.sub_anim_duration.setValue(220)
        self.sub_anim_duration.setSuffix(" ms")
        self.sub_anim_strength = QSpinBox()
        self.sub_anim_strength.setRange(10, 200)
        self.sub_anim_strength.setValue(100)
        self.sub_anim_strength.setSuffix(" %")
        self.sub_karaoke_color = QLineEdit("#FFE600")

        self.sub_hide_on_voice_pause = QCheckBox("Ẩn sub khi giọng nghỉ")
        self.sub_hide_on_voice_pause.setChecked(True)
        self.sub_pause_gap_ms = QSpinBox()
        self.sub_pause_gap_ms.setRange(120, 1200)
        self.sub_pause_gap_ms.setValue(220)
        self.sub_pause_gap_ms.setSuffix(" ms")

        self.sub_word_pop_scale = QSpinBox()
        self.sub_word_pop_scale.setRange(101, 125)
        self.sub_word_pop_scale.setValue(108)
        self.sub_word_pop_scale.setSuffix(" %")

        self.sub_word_pop_ms = QSpinBox()
        self.sub_word_pop_ms.setRange(60, 260)
        self.sub_word_pop_ms.setValue(110)
        self.sub_word_pop_ms.setSuffix(" ms")

        b_karaoke_color = QPushButton("Màu karaoke")
        b_karaoke_color.clicked.connect(
            lambda: self.pick_color(self.sub_karaoke_color)
        )

        st.addWidget(QLabel("Mẫu"), 0, 0); st.addWidget(self.sub_preset, 0, 1, 1, 2); st.addWidget(b_presets, 0, 3)
        st.addWidget(QLabel("Font"), 1, 0); st.addWidget(self.sub_font, 1, 1, 1, 3)
        st.addWidget(QLabel("Cỡ"), 2, 0); st.addWidget(self.sub_size, 2, 1)
        st.addWidget(self.sub_color, 2, 2); st.addWidget(b_sub_color, 2, 3)
        st.addWidget(QLabel("Viền"), 3, 0); st.addWidget(self.sub_outline, 3, 1)
        st.addWidget(self.sub_outline_color, 3, 2); st.addWidget(b_outline_color, 3, 3)
        st.addWidget(self.sub_bold, 4, 0); st.addWidget(self.sub_italic, 4, 1)
        st.addWidget(self.sub_background_box, 4, 2); st.addWidget(self.sub_uppercase, 4, 3)
        st.addWidget(QLabel("Nền mờ"), 5, 0); st.addWidget(self.sub_bg_opacity, 5, 1)
        st.addWidget(QLabel("Shadow"), 5, 2); st.addWidget(self.sub_shadow, 5, 3)
        st.addWidget(QLabel("X"), 6, 0); st.addWidget(self.sub_x, 6, 1)
        st.addWidget(QLabel("Y"), 6, 2); st.addWidget(self.sub_y, 6, 3)
        st.addWidget(QLabel("Độ rộng"), 7, 0); st.addWidget(self.sub_width, 7, 1)
        st.addWidget(QLabel("Ký tự tối đa"), 7, 2); st.addWidget(self.sub_max_chars, 7, 3)
        st.addWidget(self.sub_single_line, 8, 0, 1, 2)
        st.addWidget(self.sub_auto_layout, 8, 2, 1, 2)
        st.addWidget(QLabel("Lề trong"), 9, 0); st.addWidget(self.sub_inner_margin, 9, 1)
        wheel_note = QLabel("🖱 Scroll chỉ đổi số sau khi click vào đúng ô.")
        wheel_note.setObjectName("hint")
        st.addWidget(wheel_note, 9, 2, 1, 2)

        st.addWidget(QLabel("Hiệu ứng"), 10, 0)
        st.addWidget(self.sub_animation, 10, 1)
        st.addWidget(QLabel("Thời gian"), 10, 2)
        st.addWidget(self.sub_anim_duration, 10, 3)

        st.addWidget(QLabel("Cường độ"), 11, 0)
        st.addWidget(self.sub_anim_strength, 11, 1)
        st.addWidget(self.sub_karaoke_color, 11, 2)
        st.addWidget(b_karaoke_color, 11, 3)

        st.addWidget(self.sub_hide_on_voice_pause, 12, 0, 1, 2)
        st.addWidget(QLabel("Khoảng nghỉ ≥"), 12, 2)
        st.addWidget(self.sub_pause_gap_ms, 12, 3)

        st.addWidget(QLabel("Word Pop"), 13, 0)
        st.addWidget(self.sub_word_pop_scale, 13, 1)
        st.addWidget(QLabel("Pop mượt"), 13, 2)
        st.addWidget(self.sub_word_pop_ms, 13, 3)

        word_pop_hint = QLabel(
            "Word Pop Sync: voice đọc đến từ nào thì chỉ từ đó hiện ra; "
            "mỗi từ pop nhẹ rồi chuyển sang từ kế tiếp."
        )
        word_pop_hint.setObjectName("hint")
        word_pop_hint.setWordWrap(True)
        st.addWidget(word_pop_hint, 14, 0, 1, 4)

        self.sub_params_toggle = QPushButton("▸ Thông số phụ đề")
        self.sub_params_toggle.setCheckable(True)
        self.sub_params_toggle.toggled.connect(self.toggle_sub_params)

        style_layout_parent = QWidget()
        style_parent_layout = QVBoxLayout(style_layout_parent)
        style_parent_layout.setContentsMargins(0,0,0,0)
        style_parent_layout.addWidget(self.sub_params_toggle)
        style_parent_layout.addWidget(style)
        style.setVisible(False)
        self.sub_style_details = style

        sub_mouse_hint = QLabel(
            "Sub dùng 1 cỡ chữ cố định. Câu dài tự tách thành nhiều cue 1 dòng. "
            "Kéo Sub thủ công sẽ tự tắt chế độ bám Auto Blur."
        )
        sub_mouse_hint.setObjectName("hint")
        sub_mouse_hint.setWordWrap(True)
        style_parent_layout.addWidget(sub_mouse_hint)

        sg.addWidget(style_layout_parent)

        for widget in [
            self.sub_font, self.sub_size, self.sub_color, self.sub_outline,
            self.sub_outline_color, self.sub_bold, self.sub_italic,
            self.sub_background_box, self.sub_bg_opacity, self.sub_shadow,
            self.sub_x, self.sub_y, self.sub_width, self.sub_max_chars,
            self.sub_single_line, self.sub_auto_layout, self.sub_inner_margin,
            self.sub_uppercase, self.sub_animation, self.sub_anim_duration,
            self.sub_anim_strength, self.sub_karaoke_color,
            self.sub_hide_on_voice_pause, self.sub_pause_gap_ms,
            self.sub_word_pop_scale, self.sub_word_pop_ms,
        ]:
            signal = getattr(widget, "valueChanged", None) or getattr(widget, "toggled", None) or getattr(widget, "textChanged", None) or getattr(widget, "currentFontChanged", None)
            if signal:
                signal.connect(self.update_subtitle_preview_style)

        self.sub_animation.currentTextChanged.connect(
            self.update_subtitle_preview_style
        )
        self.sub_animation.currentTextChanged.connect(
            self.schedule_autosave
        )
        self.sub_animation.currentTextChanged.connect(
            self.regenerate_subtitle_for_animation_mode
        )
        self.sub_hide_on_voice_pause.toggled.connect(
            self.schedule_autosave
        )
        self.sub_pause_gap_ms.valueChanged.connect(
            self.schedule_autosave
        )
        self.sub_word_pop_scale.valueChanged.connect(
            self.schedule_autosave
        )
        self.sub_word_pop_ms.valueChanged.connect(
            self.schedule_autosave
        )

        sub_buttons = QHBoxLayout()
        b_get_sub = QPushButton("LẤY SUB KHỚP GIỌNG")
        b_get_sub.setObjectName("success")
        b_get_sub.clicked.connect(self.get_sub_from_ai)
        b_choose_srt = QPushButton("Chọn SRT")
        b_choose_srt.clicked.connect(self.choose_sub)
        b_save_sub = QPushButton("Lưu")
        b_save_sub.clicked.connect(self.save_sub_editor)
        sub_buttons.addWidget(b_get_sub, 1)
        sub_buttons.addWidget(b_save_sub)
        sub_buttons.addWidget(b_choose_srt)
        sg.addLayout(sub_buttons)

        editrow = QHBoxLayout()
        self.clean_sub = QCheckBox("Lọc rác")
        clean_btn = QPushButton("Lọc")
        clean_btn.clicked.connect(self.clean_subtitle_text)
        self.sub_find = QLineEdit(); self.sub_find.setPlaceholderText("Tìm")
        self.sub_replace = QLineEdit(); self.sub_replace.setPlaceholderText("Thay")
        replace_btn = QPushButton("Thay tất cả")
        replace_btn.clicked.connect(self.subtitle_find_replace)
        editrow.addWidget(self.clean_sub); editrow.addWidget(clean_btn)
        editrow.addWidget(self.sub_find); editrow.addWidget(self.sub_replace)
        editrow.addWidget(replace_btn)
        sg.addLayout(editrow)

        self.sub_path = QLineEdit()
        self.sub_path.setReadOnly(True)
        sg.addWidget(self.sub_path)

        self.sub_editor = QPlainTextEdit()
        self.sub_editor.setPlaceholderText("Subtitle sẽ xuất hiện ở đây...")
        self.sub_editor.setMinimumHeight(170)
        self.sub_editor.textChanged.connect(self.preview_cues_from_editor)
        sg.addWidget(self.sub_editor, 1)

        rl.addWidget(sub_box)

        capcut = QGroupBox("CapCut Bridge")
        cg = QVBoxLayout(capcut)
        cap_note = QLabel("Xuất package MP4 + subtitle + narration + nhạc để import vào CapCut.")
        cap_note.setWordWrap(True)
        cap_export = QPushButton("Xuất package")
        cap_export.clicked.connect(self.capcut_package)
        cap_open = QPushButton("Mở CapCut")
        cap_open.clicked.connect(self.open_capcut)
        cg.addWidget(cap_note)
        cg.addWidget(cap_export)
        cg.addWidget(cap_open)
        rl.addWidget(capcut)
        rl.addStretch(1)

        body.addWidget(left_scroll)
        body.addWidget(center)
        body.addWidget(right_scroll)
        body.setSizes([355, 880, 470])
        body.setStretchFactor(0, 1)
        body.setStretchFactor(1, 3)
        body.setStretchFactor(2, 1)

        # Collapsible CapCut-like basic timeline editor lives in the same
        # vertical splitter so both regions can be resized with the mouse.
        self._build_basic_editor_panel(self.export_vertical_splitter)
        self.export_vertical_splitter.setStretchFactor(0, 4)
        self.export_vertical_splitter.setStretchFactor(1, 2)
        self.export_vertical_splitter.setSizes([760, 300])

        # Persist UI split sizes with the project without forcing a layout.
        body.splitterMoved.connect(lambda *_: self.schedule_autosave())
        self.export_vertical_splitter.splitterMoved.connect(
            lambda *_: self.schedule_autosave()
        )

        self.apply_subtitle_style(subtitle_engine.clone_preset("Documentary Clean"))
        self.sub_auto_layout.toggled.connect(
            lambda checked: self.sync_sub_layout_to_auto_blur(update_cues=checked)
        )
        self.sub_inner_margin.valueChanged.connect(
            lambda _=None: self.sync_sub_layout_to_auto_blur(update_cues=True)
        )
        self._wire_processed_preview_updates()

    def _wire_processed_preview_updates(self):
        # LIVE object changes: no media reload, immediate Qt overlay update.
        live_pairs = [
            (self.resolution, "currentTextChanged"),
            (self.blur_enabled, "toggled"),
            (self.blur_style, "currentTextChanged"),
            (self.blur_opacity, "valueChanged"),
            (self.sub_enabled, "toggled"),
            (self.sub_preset, "currentTextChanged"),
            (self.sub_size, "valueChanged"),
            (self.sub_x, "valueChanged"),
            (self.sub_y, "valueChanged"),
            (self.sub_width, "valueChanged"),
            (self.sub_animation, "currentTextChanged"),
            (self.sub_anim_duration, "valueChanged"),
            (self.sub_anim_strength, "valueChanged"),
            (self.logo_enabled, "toggled"),
            (self.logo_x, "valueChanged"),
            (self.logo_y, "valueChanged"),
            (self.logo_scale, "valueChanged"),
            (self.logo_opacity, "valueChanged"),
            (self.overlay_enabled, "toggled"),
            (self.overlay_text, "textChanged"),
            (self.overlay_x, "valueChanged"),
            (self.overlay_y, "valueChanged"),
            (self.overlay_size, "valueChanged"),
        ]
        for widget, signal_name in live_pairs:
            signal = getattr(widget, signal_name, None)
            if signal:
                signal.connect(self.update_live_overlay_state)

        self.logo_pos.currentTextChanged.connect(self.apply_logo_position_preset)
        self.overlay_pos.currentTextChanged.connect(self.apply_overlay_position_preset)

        # Audio is mixed live by dedicated QMediaPlayers.
        self.mute_music.toggled.connect(self.refresh_live_audio_sources)
        self.mute_original_voice.toggled.connect(self.refresh_live_audio_sources)
        self.source_volume.sliderReleased.connect(self.update_live_audio_mix)
        self.narration_volume.sliderReleased.connect(self.update_live_audio_mix)
        self.music_volume.sliderReleased.connect(self.update_live_audio_mix)

        # Background cache is debounced and never swaps current media automatically.
        cache_pairs = [
            (self.resolution, "currentTextChanged"),
            (self.blur_enabled, "toggled"),
            (self.blur_style, "currentTextChanged"),
            (self.blur_opacity, "valueChanged"),
            (self.sub_enabled, "toggled"),
            (self.sub_preset, "currentTextChanged"),
            (self.sub_size, "valueChanged"),
            (self.sub_x, "valueChanged"),
            (self.sub_y, "valueChanged"),
            (self.sub_width, "valueChanged"),
            (self.sub_animation, "currentTextChanged"),
            (self.sub_anim_duration, "valueChanged"),
            (self.sub_anim_strength, "valueChanged"),
            (self.speed_enabled, "toggled"),
            (self.play_speed, "valueChanged"),
            (self.logo_enabled, "toggled"),
            (self.logo_x, "valueChanged"),
            (self.logo_y, "valueChanged"),
            (self.logo_scale, "valueChanged"),
            (self.logo_opacity, "valueChanged"),
            (self.logo_remove_bg, "toggled"),
            (self.side_bg_enabled, "toggled"),
            (self.side_bg_type, "currentTextChanged"),
            (self.overlay_enabled, "toggled"),
            (self.overlay_text, "textChanged"),
            (self.overlay_x, "valueChanged"),
            (self.overlay_y, "valueChanged"),
            (self.overlay_size, "valueChanged"),
        ]
        for widget, signal_name in cache_pairs:
            signal = getattr(widget, signal_name, None)
            if signal:
                signal.connect(self.schedule_processed_preview)



    # ==================================================================
    # BASIC VIDEO EDITOR — NON-DESTRUCTIVE TIMELINE
    # ==================================================================
    def _build_basic_editor_panel(self, parent_layout):
        self.editor_panel = QGroupBox("✂ Basic Video Editor")
        self.editor_panel.setMinimumHeight(125)
        layout = QVBoxLayout(self.editor_panel)
        layout.setSpacing(5)

        header = QHBoxLayout()
        self.editor_use_timeline = QCheckBox("Dùng timeline khi Xuất Video")
        self.editor_use_timeline.setToolTip(
            "Bật: Xuất Video sẽ render các clip theo đúng thứ tự/trim trên timeline."
        )
        self.editor_use_timeline.toggled.connect(self.schedule_autosave)
        self.editor_use_timeline.toggled.connect(self.editor_timeline_mode_changed)

        add_file = QPushButton("+ Video")
        add_file.clicked.connect(self.editor_add_files)
        add_queue = QPushButton("+ Từ danh sách trên")
        add_queue.clicked.connect(self.editor_add_queue_selection)

        split = QPushButton("✂ Split")
        split.clicked.connect(self.editor_split_at_playhead)
        delete_clip = QPushButton("🗑 Xóa đoạn")
        delete_clip.setObjectName("dangerSmall")
        delete_clip.clicked.connect(self.editor_delete_selected_clip)

        move_left = QPushButton("←")
        move_left.setToolTip("Đưa clip sang trái")
        move_left.clicked.connect(lambda: self.editor_move_clip(-1))
        move_right = QPushButton("→")
        move_right.setToolTip("Đưa clip sang phải")
        move_right.clicked.connect(lambda: self.editor_move_clip(1))

        trim_in = QPushButton("Đặt IN")
        trim_in.setToolTip("Cắt bỏ phần trước vị trí Preview hiện tại")
        trim_in.clicked.connect(self.editor_set_in_at_playhead)
        trim_out = QPushButton("Đặt OUT")
        trim_out.setToolTip("Cắt bỏ phần sau vị trí Preview hiện tại")
        trim_out.clicked.connect(self.editor_set_out_at_playhead)

        preview_timeline = QPushButton("▶ Preview Timeline")
        preview_timeline.setObjectName("cyan")
        preview_timeline.clicked.connect(self.editor_render_preview)

        header.addWidget(self.editor_use_timeline)
        header.addWidget(add_file)
        header.addWidget(add_queue)
        header.addWidget(split)
        header.addWidget(delete_clip)
        header.addWidget(move_left)
        header.addWidget(move_right)
        header.addWidget(trim_in)
        header.addWidget(trim_out)
        header.addStretch(1)
        header.addWidget(preview_timeline)
        layout.addLayout(header)

        # Timeline + horizontal scrolling.
        timeline_row = QHBoxLayout()
        self.editor_timeline_scroll = QScrollArea()
        self.editor_timeline_scroll.setWidgetResizable(False)
        self.editor_timeline_scroll.setHorizontalScrollBarPolicy(
            Qt.ScrollBarAsNeeded
        )
        self.editor_timeline_scroll.setVerticalScrollBarPolicy(
            Qt.ScrollBarAlwaysOff
        )
        self.editor_timeline_scroll.setMinimumHeight(140)
        self.editor_timeline = BasicTimelineWidget()
        self.editor_timeline_scroll.setWidget(self.editor_timeline)

        self.editor_timeline.clipSelected.connect(
            self.editor_clip_selected
        )
        self.editor_timeline.clipTrimChanged.connect(
            self.editor_clip_trim_changed
        )
        self.editor_timeline.clipReordered.connect(
            self.editor_clip_reordered
        )
        self.editor_timeline.playheadChanged.connect(
            self.editor_global_playhead_changed
        )
        self.editor_timeline.itemSelected.connect(self._timeline_item_selected)
        self.editor_timeline.trackStateChanged.connect(self._timeline_track_state_changed)

        zoom_box = QVBoxLayout()
        zoom_box.addWidget(QLabel("Zoom"))
        self.editor_zoom = QSlider(Qt.Vertical)
        self.editor_zoom.setRange(8, 80)
        self.editor_zoom.setValue(24)
        self.editor_zoom.valueChanged.connect(
            self.editor_timeline.set_zoom
        )
        zoom_box.addWidget(self.editor_zoom, 1)

        timeline_row.addWidget(self.editor_timeline_scroll, 1)
        timeline_row.addLayout(zoom_box)
        layout.addLayout(timeline_row)

        # Selected clip numeric trim controls.
        clip_props = QFrame()
        clip_props.setObjectName("audioStrip")
        cp = QHBoxLayout(clip_props)
        cp.setContentsMargins(8, 4, 8, 4)

        self.editor_clip_name = QLabel("Chưa chọn clip")
        self.editor_clip_name.setMinimumWidth(170)
        self.editor_in = QDoubleSpinBox()
        self.editor_in.setRange(0, 86400)
        self.editor_in.setDecimals(3)
        self.editor_in.setSuffix(" s")
        self.editor_out = QDoubleSpinBox()
        self.editor_out.setRange(0, 86400)
        self.editor_out.setDecimals(3)
        self.editor_out.setSuffix(" s")
        self.editor_duration_label = QLabel("0.00 s")
        self.editor_total_label = QLabel("Timeline: 0.00 s")
        self.editor_playhead_label = QLabel("Playhead: 0.00 s")

        self.editor_in.valueChanged.connect(
            self.editor_clip_numeric_trim_changed
        )
        self.editor_out.valueChanged.connect(
            self.editor_clip_numeric_trim_changed
        )

        cp.addWidget(self.editor_clip_name, 1)
        cp.addWidget(QLabel("IN"))
        cp.addWidget(self.editor_in)
        cp.addWidget(QLabel("OUT"))
        cp.addWidget(self.editor_out)
        cp.addWidget(QLabel("Clip"))
        cp.addWidget(self.editor_duration_label)
        cp.addWidget(self.editor_playhead_label)
        cp.addWidget(self.editor_total_label)
        layout.addWidget(clip_props)

        # --------------------------------------------------------------
        # LAYERS — compact by default; properties expand only when needed.
        # --------------------------------------------------------------
        layers_box = QGroupBox("Layers trên Preview")
        lg = QVBoxLayout(layers_box)
        lg.setSpacing(4)

        self.editor_layer_list = QListWidget()
        self.editor_layer_list.setMaximumHeight(62)
        self.editor_layer_list.currentRowChanged.connect(
            self.editor_layer_selected
        )
        lg.addWidget(self.editor_layer_list)

        layer_buttons = QHBoxLayout()
        b_text = QPushButton("+ Text")
        b_text.clicked.connect(self.editor_add_text_layer)
        b_image = QPushButton("+ Ảnh")
        b_image.clicked.connect(self.editor_add_image_layer)
        b_blur = QPushButton("+ Blur")
        b_blur.clicked.connect(self.editor_add_blur_layer)
        b_sub = QPushButton("+ Sub")
        b_sub.clicked.connect(self.editor_enable_sub_layer)
        b_edit = QPushButton("Sửa")
        b_edit.clicked.connect(self.editor_edit_selected_layer)
        b_delete = QPushButton("Xóa")
        b_delete.setObjectName("dangerSmall")
        b_delete.clicked.connect(self.editor_delete_selected_layer)
        self.editor_layer_props_toggle = QPushButton("▸ Thuộc tính")
        self.editor_layer_props_toggle.setCheckable(True)
        self.editor_layer_props_toggle.toggled.connect(
            self.toggle_editor_layer_properties
        )

        for b in [
            b_text, b_image, b_blur, b_sub, b_edit, b_delete,
            self.editor_layer_props_toggle,
        ]:
            layer_buttons.addWidget(b)
        layer_buttons.addStretch(1)
        lg.addLayout(layer_buttons)

        self.editor_layer_props_panel = QFrame()
        self.editor_layer_props_panel.setObjectName("audioStrip")
        props = QGridLayout(self.editor_layer_props_panel)
        props.setContentsMargins(7, 5, 7, 5)
        props.setHorizontalSpacing(6)
        props.setVerticalSpacing(4)

        self.editor_layer_text = QLineEdit()
        self.editor_layer_text.setPlaceholderText(
            "Text hoặc đường dẫn ảnh"
        )
        self.editor_layer_start = QDoubleSpinBox()
        self.editor_layer_start.setRange(0, 86400)
        self.editor_layer_start.setDecimals(2)
        self.editor_layer_start.setSuffix(" s")
        self.editor_layer_end = QDoubleSpinBox()
        self.editor_layer_end.setRange(0, 86400)
        self.editor_layer_end.setDecimals(2)
        self.editor_layer_end.setSuffix(" s")
        self.editor_layer_x = QDoubleSpinBox()
        self.editor_layer_x.setRange(1, 99)
        self.editor_layer_x.setValue(50)
        self.editor_layer_x.setSuffix(" %")
        self.editor_layer_y = QDoubleSpinBox()
        self.editor_layer_y.setRange(1, 99)
        self.editor_layer_y.setValue(50)
        self.editor_layer_y.setSuffix(" %")
        self.editor_layer_size = QDoubleSpinBox()
        self.editor_layer_size.setRange(2, 220)
        self.editor_layer_size.setValue(52)
        self.editor_layer_opacity = QSpinBox()
        self.editor_layer_opacity.setRange(1, 100)
        self.editor_layer_opacity.setValue(100)
        self.editor_layer_opacity.setSuffix(" %")
        self.editor_layer_font = QFontComboBox()
        self.editor_layer_color = QLineEdit("#FFFFFF")
        self.editor_layer_color_btn = QPushButton("Màu")
        self.editor_layer_color_btn.clicked.connect(
            lambda: self.pick_color(self.editor_layer_color)
        )

        props.addWidget(QLabel("Nội dung"), 0, 0)
        props.addWidget(self.editor_layer_text, 0, 1, 1, 5)
        props.addWidget(QLabel("Start"), 1, 0)
        props.addWidget(self.editor_layer_start, 1, 1)
        props.addWidget(QLabel("End"), 1, 2)
        props.addWidget(self.editor_layer_end, 1, 3)
        props.addWidget(QLabel("Opacity"), 1, 4)
        props.addWidget(self.editor_layer_opacity, 1, 5)
        props.addWidget(QLabel("X"), 2, 0)
        props.addWidget(self.editor_layer_x, 2, 1)
        props.addWidget(QLabel("Y"), 2, 2)
        props.addWidget(self.editor_layer_y, 2, 3)
        props.addWidget(QLabel("Size"), 2, 4)
        props.addWidget(self.editor_layer_size, 2, 5)
        props.addWidget(QLabel("Font"), 3, 0)
        props.addWidget(self.editor_layer_font, 3, 1, 1, 3)
        props.addWidget(self.editor_layer_color, 3, 4)
        props.addWidget(self.editor_layer_color_btn, 3, 5)

        self.editor_layer_hint = QLabel(
            "Kéo layer trên Preview; kéo handle góc phải để resize. "
            "Start/End chỉ cần mở khi muốn layer xuất hiện theo thời gian."
        )
        self.editor_layer_hint.setObjectName("hint")
        self.editor_layer_hint.setWordWrap(True)
        props.addWidget(self.editor_layer_hint, 4, 0, 1, 6)

        for widget in [
            self.editor_layer_text,
            self.editor_layer_start,
            self.editor_layer_end,
            self.editor_layer_x,
            self.editor_layer_y,
            self.editor_layer_size,
            self.editor_layer_opacity,
            self.editor_layer_font,
            self.editor_layer_color,
        ]:
            signal = (
                getattr(widget, "textChanged", None)
                or getattr(widget, "valueChanged", None)
                or getattr(widget, "currentFontChanged", None)
            )
            if signal:
                signal.connect(self.editor_layer_params_changed)

        self.editor_layer_props_panel.setVisible(False)
        lg.addWidget(self.editor_layer_props_panel)
        layout.addWidget(layers_box)

        note = QLabel(
            "Workflow: Edit video → AI → Voice → Subtitle → Export  •  "
            "Trim/Split là non-destructive."
        )
        note.setObjectName("hint")
        note.setToolTip(
            "Kéo mép vàng để Trim; kéo clip để đổi thứ tự. "
            "Nên hoàn tất cắt/ghép trước khi tạo Voice/Sub để timeline luôn khớp."
        )
        layout.addWidget(note)

        self.editor_panel.setVisible(False)
        parent_layout.addWidget(self.editor_panel)

    def toggle_basic_editor(self, checked):
        checked = bool(checked)
        if hasattr(self, "export_vertical_splitter"):
            sizes = self.export_vertical_splitter.sizes()
            if not checked and len(sizes) >= 2 and sizes[1] > 20:
                self.editor_last_splitter_sizes = list(sizes)

        self.editor_panel.setVisible(checked)
        self.editor_toggle_btn.setText(
            "✂ Ẩn Editor" if checked else "✂ Video Editor"
        )

        if checked and not self.editor_clips:
            current = self.current_video()
            if current and Path(current).exists():
                self.editor_add_paths([current])

        # QSplitter recalculates geometry after the visibility change. This fixes
        # the old bug where hiding Editor left the Preview spilling below its area.
        if hasattr(self, "export_vertical_splitter"):
            if checked:
                restore = self.editor_last_splitter_sizes or [760, 300]
                QTimer.singleShot(0, lambda r=restore: self.export_vertical_splitter.setSizes(r))
            else:
                QTimer.singleShot(0, lambda: self.export_vertical_splitter.setSizes([1000, 0]))

        self.editor_refresh_all()
        QTimer.singleShot(0, self.export_tab.updateGeometry)

    def editor_timeline_mode_changed(self, checked):
        if bool(checked) and self.editor_clips:
            self.editor_update_master_timeline_ui()
        else:
            # Restore the real source media duration when leaving timeline mode.
            duration_ms = int(self.player.duration())
            self.timeline_slider.setRange(0, max(0, duration_ms))
            self.preview_total.setText(fmt_time(duration_ms / 1000.0))
            if not self.timeline_slider.isSliderDown():
                self.timeline_slider.setValue(int(self.player.position()))
            self.preview_current.setText(fmt_time(self.player.position() / 1000.0))
        self.update_live_overlay_state()

    def editor_add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Thêm video vào Timeline",
            "",
            "Video (*.mp4 *.mov *.mkv *.avi *.webm)",
        )
        if paths:
            self.editor_add_paths(paths)

    def editor_add_queue_selection(self):
        rows = sorted(
            {idx.row() for idx in self.queue_list.selectedIndexes()}
        )
        if rows:
            paths = [
                self.queue[i]
                for i in rows
                if 0 <= i < len(self.queue)
            ]
        else:
            current = self.current_video()
            paths = [current] if current else []
        if not paths:
            QMessageBox.information(
                self,
                "Video Editor",
                "Chưa chọn video ở danh sách phía trên.",
            )
            return
        self.editor_add_paths(paths)

    def editor_add_paths(self, paths):
        added = 0
        for path in paths:
            try:
                self.editor_clips.append(
                    editor_engine.make_clip(path)
                )
                added += 1
            except Exception as e:
                self.log_line(
                    f"[EDITOR ADD ERROR] {path}: {e}"
                )
        if added:
            self.editor_use_timeline.setChecked(True)
            self.editor_selected_clip = len(self.editor_clips) - 1
            self.editor_refresh_all()
            self.editor_clip_selected(self.editor_selected_clip)
            self.schedule_autosave()

    def editor_refresh_all(self):
        if not hasattr(self, "editor_timeline"):
            return
        self.editor_document.synchronize_legacy_items()
        self.editor_timeline.set_clips(self.editor_clips)
        self._synchronize_supplemental_timeline_items()
        self.editor_timeline.set_timeline_items(self.editor_document.timeline.items)
        self.editor_timeline.set_tracks(self.editor_document.timeline.tracks)
        self.editor_timeline.set_selected(self.editor_selected_clip)
        self.editor_total_label.setText(
            f"Timeline: {editor_engine.total_duration(self.editor_clips):.2f} s"
        )
        self.editor_refresh_layer_list()
        if self.editor_timeline_active():
            self.editor_update_master_timeline_ui()
        self.update_live_overlay_state()
        self._refresh_professional_panels()

    def _synchronize_supplemental_timeline_items(self):
        items = []
        if self.preview_cues:
            track = self.editor_document.timeline.track_for_kind(TimelineItemKind.SUBTITLE)
            group = self._current_subtitle_group_id()
            for index, cue in enumerate(self.preview_cues):
                start, end, text = cue[:3]
                items.append(TimelineItem(TimelineItemKind.SUBTITLE, track.id, float(start), float(end), id=f"{group}:{index}", group_id=group, metadata={"text": text, "font_size": self.sub_size.value()}))
        audio_path = self.narration_path or (self.voice_file.text().strip() if hasattr(self, "voice_file") else "")
        if audio_path:
            track = self.editor_document.timeline.track_for_kind(TimelineItemKind.AUDIO)
            duration = max(self.editor_document.timeline.duration, self.narration_player.duration() / 1000.0)
            items.append(TimelineItem(TimelineItemKind.AUDIO, track.id, 0.0, duration, id="ai-narration", source_ref=audio_path, metadata={"name": "AI Narration", "volume": self.narration_volume.value()}))
        effect_track = self.editor_document.timeline.track_for_kind(TimelineItemKind.BLUR)
        duration = max(0.1, editor_engine.total_duration(self.editor_clips) or self.player.duration() / 1000.0)
        for index, zone in enumerate(self.blur_zones()):
            items.append(TimelineItem(TimelineItemKind.BLUR, effect_track.id, float(zone.get("start", 0.0)), float(zone.get("end", duration)), id=f"blur:{index}", metadata=zone))
        self.editor_document.timeline.set_supplemental_items(items)

    def _timeline_track_state_changed(self, track_id, field, value):
        track = next((track for track in self.editor_document.timeline.tracks if track.id == track_id), None)
        if track is None: return
        for item in self.editor_document.timeline.items:
            if item.track_id != track_id: continue
            setattr(item, field, bool(value))
            if field == "locked": item.metadata["locked"] = bool(value)
            elif field == "visible": item.metadata["enabled"] = bool(value)
            elif field == "muted": item.metadata["muted"] = bool(value)
        self.update_live_overlay_state(); self.schedule_autosave()

    def _timeline_item_selected(self, kind, item_id, legacy_index):
        item = next((item for item in self.editor_document.timeline.items if item.id == item_id), None)
        if item is None: return
        group_id = item.group_id if kind == "subtitle" else ""
        self.editor_document.selection.select(kind, item_id, group_id)
        self.editor_timeline.set_selected_item(item_id)
        if kind in ("text", "image", "logo"):
            index = next((i for i, layer in enumerate(self.editor_layers) if layer.get("id") == item_id), -1)
            if index >= 0:
                self.editor_selected_layer = index; self.live_overlay.selected_type = "editor_layer"; self.live_overlay.selected_index = index; self.live_overlay.update()
        elif kind == "subtitle":
            self.live_overlay.selected_type = "sub"; self.live_overlay.update()
        self.context_inspector.load_properties(kind, item.metadata)

    def editor_clip_selected(self, index, seek=True):
        if not (0 <= index < len(self.editor_clips)):
            self.editor_selected_clip = -1
            self.editor_clip_name.setText("Chưa chọn clip")
            return

        self.editor_selected_clip = int(index)
        self.editor_timeline.set_selected(index)
        clip = self.editor_clips[index]
        self.editor_document.selection.select("video", str(clip.get("id", "")))
        if hasattr(self, "context_inspector"):
            self.context_inspector.load_properties("video", clip)

        self.editor_clip_name.setText(
            f"{index + 1}. {clip.get('name', Path(clip.get('path','')).name)}"
        )

        self.editor_in.blockSignals(True)
        self.editor_out.blockSignals(True)
        self.editor_in.setMaximum(
            max(0.1, float(clip.get("source_duration", clip.get("source_end", 0))) - 0.05)
        )
        self.editor_out.setMaximum(
            max(0.1, float(clip.get("source_duration", clip.get("source_end", 0))))
        )
        self.editor_in.setValue(
            float(clip.get("source_start", 0.0))
        )
        self.editor_out.setValue(
            float(clip.get("source_end", 0.0))
        )
        self.editor_in.blockSignals(False)
        self.editor_out.blockSignals(False)

        self.editor_duration_label.setText(
            f"{editor_engine.clip_duration(clip):.2f} s"
        )

        # Direct user selection opens the clip. Programmatic timeline seeking
        # can update the inspector without jumping back to the clip start.
        if seek:
            self.editor_seek_clip(
                index,
                float(clip.get("source_start", 0.0)),
                autoplay=False,
            )

    def editor_seek_clip(self, index, source_second, autoplay=False):
        if not (0 <= index < len(self.editor_clips)):
            return
        clip = self.editor_clips[index]
        path = str(clip.get("path", "") or "")
        if not path or not Path(path).exists():
            return

        self.editor_selected_clip = index
        self.editor_timeline.set_selected(index)
        self.preview_is_processed = False

        start = float(clip.get("source_start", 0.0))
        end = float(clip.get("source_end", start + 0.05))
        source_second = max(start, min(end, float(source_second)))
        target_ms = max(0, int(source_second * 1000))

        same_source = False
        try:
            same_source = (
                bool(self.preview_loaded_path)
                and Path(self.preview_loaded_path).resolve() == Path(path).resolve()
            )
        except Exception:
            same_source = False

        if same_source:
            self.player.setPosition(target_ms)
            if autoplay:
                self.player.play()
        else:
            # Restore the desired source position as soon as Qt reports LoadedMedia.
            self.preview_pending_position = target_ms
            self.load_preview_media(path, autoplay=autoplay)

        self.preview_state.setText("✂ Timeline Preview")

    def editor_clip_trim_changed(self, index, source_start, source_end):
        if not (0 <= index < len(self.editor_clips)):
            return
        old_clip = self.editor_clips[index]
        source_now = float(old_clip.get("source_start", 0.0))
        try:
            if (
                self.preview_loaded_path
                and Path(self.preview_loaded_path).resolve()
                == Path(old_clip.get("path", "")).resolve()
            ):
                source_now = self.player.position() / 1000.0
        except Exception:
            pass

        self.editor_clips[index] = editor_engine.trim_clip(
            old_clip, source_start, source_end
        )
        clip = self.editor_clips[index]
        source_now = max(
            float(clip.get("source_start", 0.0)),
            min(float(clip.get("source_end", 0.0)), source_now),
        )
        self.editor_selected_clip = index
        self.editor_refresh_all()
        self.editor_clip_selected(index, seek=False)
        self.editor_seek_clip(index, source_now, autoplay=False)
        self.schedule_autosave()

    def editor_clip_numeric_trim_changed(self, *args):
        index = self.editor_selected_clip
        if not (0 <= index < len(self.editor_clips)):
            return
        start = self.editor_in.value()
        end = self.editor_out.value()
        if end <= start + 0.049:
            return
        self.editor_clips[index] = editor_engine.trim_clip(
            self.editor_clips[index],
            start,
            end,
        )
        self.editor_timeline.set_clips(self.editor_clips)
        self.editor_duration_label.setText(
            f"{editor_engine.clip_duration(self.editor_clips[index]):.2f} s"
        )
        self.editor_total_label.setText(
            f"Timeline: {editor_engine.total_duration(self.editor_clips):.2f} s"
        )
        self.editor_update_master_timeline_ui()
        self.schedule_autosave()

    def editor_clip_reordered(self, source_index, target_index):
        new_index = editor_engine.reorder_clip(
            self.editor_clips,
            source_index,
            target_index,
        )
        self.editor_selected_clip = new_index
        self.editor_refresh_all()
        self.schedule_autosave()

    def editor_move_clip(self, delta):
        index = self.editor_selected_clip
        if not (0 <= index < len(self.editor_clips)):
            return
        target = max(
            0,
            min(len(self.editor_clips) - 1, index + int(delta)),
        )
        if target == index:
            return
        self.editor_clip_reordered(index, target)

    def editor_split_at_playhead(self):
        index = self.editor_selected_clip
        if not (0 <= index < len(self.editor_clips)):
            QMessageBox.information(
                self, "Split", "Chọn clip cần cắt."
            )
            return
        source_second = self.player.position() / 1000.0
        clip = self.editor_clips[index]
        if (
            self.preview_loaded_path
            and Path(self.preview_loaded_path).resolve()
            != Path(clip["path"]).resolve()
        ):
            source_second = (
                float(clip.get("source_start", 0.0))
                + editor_engine.clip_duration(clip) / 2.0
            )
        try:
            new_index = editor_engine.split_clip(
                self.editor_clips,
                index,
                source_second,
            )
            self.editor_selected_clip = new_index
            self.editor_refresh_all()
            self.editor_clip_selected(new_index)
            self.schedule_autosave()
        except Exception as e:
            QMessageBox.warning(self, "Split", str(e))

    def editor_delete_selected_clip(self):
        index = self.editor_selected_clip
        if not (0 <= index < len(self.editor_clips)):
            return
        self.editor_clips.pop(index)
        self.editor_selected_clip = min(
            index,
            len(self.editor_clips) - 1,
        )
        self.editor_refresh_all()
        if self.editor_selected_clip >= 0:
            self.editor_clip_selected(self.editor_selected_clip)
        self.schedule_autosave()

    def editor_set_in_at_playhead(self):
        i = self.editor_selected_clip
        if not (0 <= i < len(self.editor_clips)):
            return
        clip = self.editor_clips[i]
        pos = self.player.position() / 1000.0
        try:
            self.editor_clips[i] = editor_engine.trim_clip(
                clip,
                pos,
                float(clip.get("source_end", 0.0)),
            )
            self.editor_refresh_all()
            self.editor_clip_selected(i, seek=False)
            self.editor_seek_clip(
                i,
                float(self.editor_clips[i].get("source_start", 0.0)),
                autoplay=False,
            )
            self.schedule_autosave()
        except Exception as e:
            QMessageBox.warning(self, "Trim IN", str(e))

    def editor_set_out_at_playhead(self):
        i = self.editor_selected_clip
        if not (0 <= i < len(self.editor_clips)):
            return
        clip = self.editor_clips[i]
        pos = self.player.position() / 1000.0
        try:
            self.editor_clips[i] = editor_engine.trim_clip(
                clip,
                float(clip.get("source_start", 0.0)),
                pos,
            )
            self.editor_refresh_all()
            self.editor_clip_selected(i, seek=False)
            self.editor_seek_clip(
                i,
                min(
                    float(self.editor_clips[i].get("source_end", 0.0)) - 0.02,
                    max(
                        float(self.editor_clips[i].get("source_start", 0.0)),
                        pos,
                    ),
                ),
                autoplay=False,
            )
            self.schedule_autosave()
        except Exception as e:
            QMessageBox.warning(self, "Trim OUT", str(e))

    def editor_timeline_active(self):
        return bool(
            hasattr(self, "editor_use_timeline")
            and self.editor_use_timeline.isChecked()
            and self.editor_clips
        )

    def editor_flattened_preview_loaded(self):
        if not self.editor_preview_path or not self.preview_loaded_path:
            return False
        try:
            return (
                Path(self.editor_preview_path).resolve()
                == Path(self.preview_loaded_path).resolve()
            )
        except Exception:
            return False

    def editor_master_total(self):
        return self.editor_document.duration

    def editor_update_master_timeline_ui(self, global_second=None):
        if not self.editor_timeline_active():
            return
        total = max(0.0, self.editor_master_total())
        if global_second is None:
            global_second = self.editor_current_global_second()
        global_second = max(0.0, min(total, float(global_second or 0.0)))

        self.timeline_slider.setRange(0, int(round(total * 1000)))
        if not self.timeline_slider.isSliderDown():
            self.timeline_slider.setValue(int(round(global_second * 1000)))
        self.preview_current.setText(fmt_time(global_second))
        self.preview_total.setText(fmt_time(total))
        self.editor_timeline.set_playhead(global_second)
        self.editor_playhead_label.setText(
            f"Playhead: {global_second:.2f} s"
        )
        self.editor_total_label.setText(
            f"Timeline: {total:.2f} s"
        )

    def editor_current_global_second(self):
        if not self.editor_timeline_active():
            return self.player.position() / 1000.0
        if self.editor_flattened_preview_loaded():
            return max(0.0, self.player.position() / 1000.0)
        i = self.editor_selected_clip
        if not (0 <= i < len(self.editor_clips)):
            return 0.0
        clip = self.editor_clips[i]
        path = str(clip.get("path", "") or "")
        try:
            if (
                not self.preview_loaded_path
                or Path(self.preview_loaded_path).resolve() != Path(path).resolve()
            ):
                return editor_engine.timeline_ranges(self.editor_clips)[i][0]
        except Exception:
            return editor_engine.timeline_ranges(self.editor_clips)[i][0]
        return editor_engine.global_time_for_clip_source(
            self.editor_clips,
            i,
            self.player.position() / 1000.0,
        )

    def editor_seek_global(self, global_second, autoplay=None):
        if not self.editor_timeline_active():
            return
        if self.editor_sync_guard:
            return
        total = self.editor_master_total()
        global_second = max(0.0, min(total, float(global_second or 0.0)))

        if self.editor_flattened_preview_loaded():
            index, _source_second, _ = editor_engine.locate_time(
                self.editor_clips, global_second
            )
            if index >= 0:
                self.editor_selected_clip = index
                self.editor_clip_selected(index, seek=False)
            self.player.setPosition(int(global_second * 1000))
            self.editor_update_master_timeline_ui(global_second)
            return

        index, source_second, _ = editor_engine.locate_time(
            self.editor_clips, global_second
        )
        if index < 0:
            return
        if autoplay is None:
            autoplay = self.player.playbackState() == QMediaPlayer.PlayingState

        self.editor_sync_guard = True
        try:
            self.editor_selected_clip = index
            self.editor_clip_selected(index, seek=False)
            self.editor_update_master_timeline_ui(global_second)
            self.editor_seek_clip(index, source_second, autoplay=bool(autoplay))
        finally:
            self.editor_sync_guard = False

    def editor_global_playhead_changed(self, global_second):
        if not self.editor_timeline_active():
            return
        # Red editor playhead and blue Preview slider are the same global clock.
        self.editor_seek_global(
            global_second,
            autoplay=(self.player.playbackState() == QMediaPlayer.PlayingState),
        )

    def editor_sync_playhead_from_source(self, source_second):
        if not self.editor_timeline_active():
            return float(source_second or 0.0)

        # Flattened timeline preview is already on the global clock.
        if self.editor_flattened_preview_loaded():
            global_second = max(0.0, float(source_second or 0.0))
            self.editor_update_master_timeline_ui(global_second)
            return global_second

        i = self.editor_selected_clip
        if not (0 <= i < len(self.editor_clips)):
            return 0.0
        clip = self.editor_clips[i]
        path = str(clip.get("path", "") or "")
        if not self.preview_loaded_path or not path:
            return editor_engine.timeline_ranges(self.editor_clips)[i][0]
        try:
            if Path(self.preview_loaded_path).resolve() != Path(path).resolve():
                return editor_engine.timeline_ranges(self.editor_clips)[i][0]
        except Exception:
            return 0.0

        source_second = float(source_second or 0.0)
        start = float(clip.get("source_start", 0.0))
        end = float(clip.get("source_end", start + 0.05))
        source_second = max(start, min(end, source_second))

        global_second = editor_engine.global_time_for_clip_source(
            self.editor_clips, i, source_second
        )
        self.editor_update_master_timeline_ui(global_second)

        # When playback reaches trimmed OUT, continue with the next timeline clip.
        if (
            not self.editor_sync_guard
            and self.player.playbackState() == QMediaPlayer.PlayingState
            and source_second >= end - 0.035
        ):
            if i + 1 < len(self.editor_clips):
                next_global = editor_engine.timeline_ranges(self.editor_clips)[i + 1][0]
                QTimer.singleShot(0, lambda g=next_global: self.editor_seek_global(g, autoplay=True))
            else:
                self.player.pause()
                self.pause_live_audio_tracks()
                self.preview_state.setText("✂ Hết Timeline")

        return global_second

    def editor_render_preview(self):
        if not self.editor_clips:
            QMessageBox.information(
                self,
                "Preview Timeline",
                "Timeline chưa có video.",
            )
            return

        workspace = self.project_workspace_for(
            self.current_video()
            or self.editor_clips[0]["path"]
        )
        out = workspace / "editor_timeline_preview.mp4"

        def job(progress, log):
            return editor_engine.render_timeline(
                self.editor_clips,
                str(out),
                preview=True,
                log=log,
                process_holder=self.process_holder,
            )

        def done(path):
            current_global = self.editor_current_global_second()
            self.editor_preview_path = path
            self.preview_is_processed = False
            self.preview_pending_position = int(current_global * 1000)
            self.load_preview_media(path, autoplay=False)
            self.editor_update_master_timeline_ui(current_global)
            self.preview_state.setText("✓ Timeline Preview")
            self.status("Timeline Preview đã sẵn sàng.")

        self.run_worker(
            "Đang render Timeline Preview...",
            job,
            done,
        )

    # ------------------------------------------------------------------
    # EDITOR LAYERS
    # ------------------------------------------------------------------
    def editor_current_time(self):
        if (
            hasattr(self, "editor_use_timeline")
            and self.editor_use_timeline.isChecked()
            and self.editor_clips
            and 0 <= self.editor_selected_clip < len(self.editor_clips)
        ):
            clip = self.editor_clips[self.editor_selected_clip]
            path = str(clip.get("path", "") or "")
            if self.preview_loaded_path and path:
                try:
                    if Path(self.preview_loaded_path).resolve() == Path(path).resolve():
                        return editor_engine.global_time_for_clip_source(
                            self.editor_clips,
                            self.editor_selected_clip,
                            self.player.position() / 1000.0,
                        )
                except Exception:
                    pass
        return self.player.position() / 1000.0

    def editor_refresh_layer_list(self):
        if not hasattr(self, "editor_layer_list"):
            return
        selected_meta = None
        item = self.editor_layer_list.currentItem()
        if item:
            selected_meta = item.data(Qt.UserRole)

        self.editor_layer_list.blockSignals(True)
        self.editor_layer_list.clear()

        for i, layer in enumerate(self.editor_layers):
            kind = "Text" if layer.get("type") == "text" else "Ảnh"
            title = (
                str(layer.get("text", "") or "")[:35]
                if layer.get("type") == "text"
                else Path(str(layer.get("path", "") or "")).name
            )
            item = QListWidgetItem(
                f"{'✓' if layer.get('enabled', True) else '○'} "
                f"{kind} {i + 1}: {title}"
            )
            item.setData(
                Qt.UserRole,
                {"kind": "extra", "index": i},
            )
            self.editor_layer_list.addItem(item)

        if self.sub_enabled.isChecked():
            item = QListWidgetItem("✓ Subtitle")
            item.setData(Qt.UserRole, {"kind": "subtitle"})
            self.editor_layer_list.addItem(item)

        if self.logo_enabled.isChecked():
            item = QListWidgetItem(
                "✓ Logo: " + Path(self.logo_path.text().strip()).name
            )
            item.setData(Qt.UserRole, {"kind": "legacy_logo"})
            self.editor_layer_list.addItem(item)

        if self.overlay_enabled.isChecked():
            item = QListWidgetItem(
                "✓ Chữ phủ: " + self.overlay_text.text()[:35]
            )
            item.setData(Qt.UserRole, {"kind": "legacy_text"})
            self.editor_layer_list.addItem(item)

        for i, _zone in enumerate(self.blur_zones()):
            item = QListWidgetItem(f"✓ Blur zone {i + 1}")
            item.setData(
                Qt.UserRole,
                {"kind": "blur", "index": i},
            )
            self.editor_layer_list.addItem(item)

        self.editor_layer_list.blockSignals(False)

        # Restore selection if possible.
        if selected_meta:
            for row in range(self.editor_layer_list.count()):
                meta = self.editor_layer_list.item(row).data(Qt.UserRole)
                if meta == selected_meta:
                    self.editor_layer_list.setCurrentRow(row)
                    break
        self.editor_document.synchronize_legacy_items()
        self._refresh_professional_panels()

    def toggle_editor_layer_properties(self, checked):
        checked = bool(checked)
        self.editor_layer_props_panel.setVisible(checked)
        self.editor_layer_props_toggle.setText(
            "▾ Thuộc tính" if checked else "▸ Thuộc tính"
        )
        self.schedule_autosave()

    def editor_add_text_layer(self):
        text, ok = QInputDialog.getText(
            self,
            "Thêm Text",
            "Nội dung:",
            text="Text mới",
        )
        if not ok or not text.strip():
            return
        layer = editor_engine.make_text_layer(
            text.strip(),
            max(
                0.1,
                editor_engine.total_duration(self.editor_clips)
                or (self.player.duration() / 1000.0),
            ),
        )
        self.editor_layers.append(layer)
        self.editor_selected_layer = len(self.editor_layers) - 1
        self.editor_refresh_layer_list()
        self.editor_select_extra_layer_in_list(
            self.editor_selected_layer
        )
        self.update_live_overlay_state()
        self.schedule_autosave()

    def editor_add_image_layer(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Thêm ảnh / sticker / logo",
            "",
            "Image (*.png *.jpg *.jpeg *.webp *.bmp)",
        )
        if not path:
            return
        layer = editor_engine.make_image_layer(
            path,
            max(
                0.1,
                editor_engine.total_duration(self.editor_clips)
                or (self.player.duration() / 1000.0),
            ),
        )
        self.editor_layers.append(layer)
        self.editor_selected_layer = len(self.editor_layers) - 1
        self.editor_refresh_layer_list()
        self.editor_select_extra_layer_in_list(
            self.editor_selected_layer
        )
        self.update_live_overlay_state()
        self.schedule_autosave()

    def editor_add_blur_layer(self):
        self.blur_enabled.setChecked(True)
        self.add_blur_zone()
        self.editor_refresh_layer_list()
        self.update_live_overlay_state()

    def editor_enable_sub_layer(self):
        if not self.sub_path.text().strip():
            QMessageBox.information(
                self,
                "Subtitle",
                "Chưa có subtitle. Hãy LẤY SUB KHỚP GIỌNG hoặc Chọn SRT trước.",
            )
            return
        self.sub_enabled.setChecked(True)
        self.editor_refresh_layer_list()
        self.update_live_overlay_state()

    def editor_select_extra_layer_in_list(self, index):
        for row in range(self.editor_layer_list.count()):
            meta = self.editor_layer_list.item(row).data(Qt.UserRole)
            if (
                isinstance(meta, dict)
                and meta.get("kind") == "extra"
                and int(meta.get("index", -1)) == int(index)
            ):
                self.editor_layer_list.setCurrentRow(row)
                return

    def editor_layer_selected(self, row):
        item = self.editor_layer_list.item(row)
        if not item:
            self.editor_selected_layer = -1
            return
        meta = item.data(Qt.UserRole) or {}
        kind = meta.get("kind")

        if kind == "extra":
            index = int(meta.get("index", -1))
            if not (0 <= index < len(self.editor_layers)):
                return
            self.editor_selected_layer = index
            layer = self.editor_layers[index]

            widgets = [
                self.editor_layer_text,
                self.editor_layer_start,
                self.editor_layer_end,
                self.editor_layer_x,
                self.editor_layer_y,
                self.editor_layer_size,
                self.editor_layer_opacity,
                self.editor_layer_font,
                self.editor_layer_color,
            ]
            for w in widgets:
                w.blockSignals(True)

            if layer.get("type") == "text":
                self.editor_layer_text.setText(
                    str(layer.get("text", "") or "")
                )
                self.editor_layer_size.setValue(
                    float(layer.get("font_size", 52))
                )
                self.editor_layer_font.setCurrentFont(
                    QFont(str(layer.get("font_name", "Arial") or "Arial"))
                )
                self.editor_layer_color.setText(
                    str(layer.get("color", "#FFFFFF") or "#FFFFFF")
                )
                self.editor_layer_font.setEnabled(True)
                self.editor_layer_color.setEnabled(True)
                self.editor_layer_color_btn.setEnabled(True)
                self.editor_layer_hint.setText(
                    "Text: kéo để di chuyển; kéo góc phải để đổi cỡ chữ."
                )
            else:
                self.editor_layer_text.setText(
                    str(layer.get("path", "") or "")
                )
                self.editor_layer_size.setValue(
                    float(layer.get("scale", 20.0))
                )
                self.editor_layer_font.setEnabled(False)
                self.editor_layer_color.setEnabled(False)
                self.editor_layer_color_btn.setEnabled(False)
                self.editor_layer_hint.setText(
                    "Ảnh: kéo để di chuyển; kéo góc phải để resize."
                )

            self.editor_layer_start.setValue(
                float(layer.get("start", 0.0))
            )
            self.editor_layer_end.setValue(
                float(layer.get("end", 0.1))
            )
            self.editor_layer_x.setValue(
                float(layer.get("x", 50.0))
            )
            self.editor_layer_y.setValue(
                float(layer.get("y", 50.0))
            )
            self.editor_layer_opacity.setValue(
                int(layer.get("opacity", 100))
            )

            for w in widgets:
                w.blockSignals(False)

            self.live_overlay.selected_type = "editor_layer"
            self.live_overlay.selected_index = index
            self.live_overlay.update()

        elif kind == "blur":
            index = int(meta.get("index", -1))
            self.blur_zone_list.setCurrentRow(index)
            self.blur_params_toggle.setChecked(True)
        elif kind == "subtitle":
            self.sub_params_toggle.setChecked(True)
            self.live_overlay.selected_type = "sub"
            self.live_overlay.update()
        elif kind == "legacy_logo":
            self.logo_params_toggle.setChecked(True)
            self.live_overlay.selected_type = "logo"
            self.live_overlay.update()
        elif kind == "legacy_text":
            self.overlay_params_toggle.setChecked(True)
            self.live_overlay.selected_type = "text"
            self.live_overlay.update()

    def editor_layer_params_changed(self, *args):
        index = self.editor_selected_layer
        if not (0 <= index < len(self.editor_layers)):
            return
        layer = dict(self.editor_layers[index])

        layer["start"] = max(
            0.0,
            self.editor_layer_start.value(),
        )
        layer["end"] = max(
            layer["start"] + 0.05,
            self.editor_layer_end.value(),
        )
        layer["x"] = self.editor_layer_x.value()
        layer["y"] = self.editor_layer_y.value()
        layer["opacity"] = self.editor_layer_opacity.value()

        if layer.get("type") == "text":
            layer["text"] = self.editor_layer_text.text()
            layer["font_size"] = int(
                round(self.editor_layer_size.value())
            )
            layer["font_name"] = self.editor_layer_font.currentFont().family()
            layer["color"] = (
                self.editor_layer_color.text().strip()
                or "#FFFFFF"
            )
        else:
            layer["scale"] = self.editor_layer_size.value()

        self.editor_layers[index] = layer
        self.update_live_overlay_state()
        self.editor_refresh_layer_list()
        self.schedule_autosave()

    def editor_edit_selected_layer(self):
        item = self.editor_layer_list.currentItem()
        if not item:
            return
        meta = item.data(Qt.UserRole) or {}
        kind = meta.get("kind")

        if kind == "extra":
            index = int(meta.get("index", -1))
            if not (0 <= index < len(self.editor_layers)):
                return
            layer = self.editor_layers[index]
            if layer.get("type") == "text":
                text, ok = QInputDialog.getText(
                    self,
                    "Sửa Text",
                    "Nội dung:",
                    text=str(layer.get("text", "") or ""),
                )
                if ok:
                    layer["text"] = text
            else:
                path, _ = QFileDialog.getOpenFileName(
                    self,
                    "Thay ảnh",
                    "",
                    "Image (*.png *.jpg *.jpeg *.webp *.bmp)",
                )
                if path:
                    layer["path"] = str(Path(path).resolve())
            self.editor_layers[index] = layer
            self.editor_layer_selected(
                self.editor_layer_list.currentRow()
            )
            self.update_live_overlay_state()
            self.editor_refresh_layer_list()
            self.schedule_autosave()

        elif kind == "blur":
            self.blur_params_toggle.setChecked(True)
        elif kind == "subtitle":
            self.sub_params_toggle.setChecked(True)
        elif kind == "legacy_logo":
            self.choose_logo()
        elif kind == "legacy_text":
            text, ok = QInputDialog.getText(
                self,
                "Sửa Chữ phủ",
                "Nội dung:",
                text=self.overlay_text.text(),
            )
            if ok:
                self.overlay_text.setText(text)

    def editor_delete_selected_layer(self):
        item = self.editor_layer_list.currentItem()
        if not item:
            return
        meta = item.data(Qt.UserRole) or {}
        kind = meta.get("kind")

        if kind == "extra":
            index = int(meta.get("index", -1))
            if 0 <= index < len(self.editor_layers):
                self.editor_layers.pop(index)
                self.editor_selected_layer = -1
        elif kind == "blur":
            index = int(meta.get("index", -1))
            self.blur_zone_list.setCurrentRow(index)
            self.remove_blur_zone()
        elif kind == "subtitle":
            self.sub_enabled.setChecked(False)
        elif kind == "legacy_logo":
            self.logo_enabled.setChecked(False)
        elif kind == "legacy_text":
            self.overlay_enabled.setChecked(False)

        self.live_overlay.selected_type = ""
        self.live_overlay.selected_index = -1
        self.editor_refresh_layer_list()
        self.update_live_overlay_state()
        self.schedule_autosave()

    def on_live_editor_layer_geometry_changed(self, index, layer):
        if not (0 <= index < len(self.editor_layers)):
            return
        self.editor_layers[index] = dict(layer)
        self.editor_selected_layer = index
        self.editor_select_extra_layer_in_list(index)
        self.editor_layer_selected(
            self.editor_layer_list.currentRow()
        )
        self.schedule_autosave()



    # ------------------------------------------------------------------
    # AI STUDIO — controls LEFT, timeline RIGHT, NO TTS.
    # ------------------------------------------------------------------
    def _build_ai_tab(self):
        root = QVBoxLayout(self.ai_tab)

        splitter = QSplitter(Qt.Horizontal)
        root.addWidget(splitter, 1)

        left = QWidget()
        ll = QVBoxLayout(left)

        project_box = QGroupBox("Project")
        pg = QGridLayout(project_box)
        self.ai_video_path = QLineEdit()
        self.ai_video_path.setPlaceholderText("Chọn video cần AI viết kịch bản...")
        choose = QPushButton("📁 Chọn Video")
        choose.clicked.connect(self.choose_ai_video)
        from_exporter = QPushButton("← Video từ Exporter")
        from_exporter.clicked.connect(self.use_export_selection_for_ai)
        open_p = QPushButton("Mở Project")
        open_p.clicked.connect(self.open_ai_project)
        save_p = QPushButton("Lưu Project")
        save_p.clicked.connect(self.save_ai_project)
        self.autosave_label = QLabel("● Auto-save: BẬT")
        self.autosave_label.setObjectName("readyText")

        pg.addWidget(self.ai_video_path, 0, 0, 1, 3)
        pg.addWidget(choose, 1, 0)
        pg.addWidget(from_exporter, 1, 1)
        pg.addWidget(open_p, 2, 0)
        pg.addWidget(save_p, 2, 1)
        pg.addWidget(self.autosave_label, 3, 0, 1, 3)
        ll.addWidget(project_box)

        ai_box = QGroupBox("AI hiểu video + viết kịch bản")
        ag = QFormLayout(ai_box)
        self.market = QComboBox()
        self.market.addItems(["US", "Vietnam", "Global English"])
        self.script_style = QComboBox()
        self.script_style.addItems(list(AI_STYLE_LIBRARY.keys()))
        self.script_style.setMaxVisibleItems(18)
        self.script_style_vi = QLabel()
        self.script_style_vi.setObjectName("hint")
        self.script_style_vi.setWordWrap(True)
        self.script_style.currentTextChanged.connect(
            self.update_script_style_translation
        )
        self.ai_speed_mode = QComboBox()
        self.ai_speed_mode.addItems([
            "Nhanh — ít frame",
            "Chất lượng — Model Settings",
        ])
        self.ai_include_audio = QCheckBox("Nghe lời nói nguồn (chậm hơn)")
        self.ai_include_audio.setChecked(False)

        self.auto_ai_button = QPushButton("⚡ AI HIỂU VIDEO + VIẾT KỊCH BẢN")
        self.auto_ai_button.setObjectName("hero")
        self.auto_ai_button.setMinimumHeight(58)
        self.auto_ai_button.clicked.connect(self.ai_fast_pipeline)

        ag.addRow("Thị trường", self.market)
        ag.addRow("Phong cách", self.script_style)
        ag.addRow("🇻🇳 Nghĩa", self.script_style_vi)
        ag.addRow("Tốc độ AI", self.ai_speed_mode)
        ag.addRow("", self.ai_include_audio)
        ag.addRow("", self.auto_ai_button)
        ll.addWidget(ai_box)
        self.update_script_style_translation(
            self.script_style.currentText()
        )

        summary_box = QGroupBox("AI Understanding")
        sl = QVBoxLayout(summary_box)
        self.ai_summary = QPlainTextEdit()
        self.ai_summary.setPlaceholderText("Tóm tắt video sẽ hiện ở đây...")
        self.ai_summary.textChanged.connect(self.schedule_autosave)
        sl.addWidget(self.ai_summary)
        ll.addWidget(summary_box, 1)

        hint = QLabel(
            "Sau khi AI viết xong, project tự lưu và kịch bản tự chuyển sang "
            "Video Exporter → Lồng Tiếng (TTS)."
        )
        hint.setWordWrap(True)
        hint.setObjectName("hint")
        ll.addWidget(hint)

        # Hidden context retained for project compatibility.
        self.transcript = QPlainTextEdit()
        self.transcript.setVisible(False)

        right = QWidget()
        rl = QVBoxLayout(right)
        head = QHBoxLayout()
        head.addWidget(QLabel("Timeline / Kịch bản"))
        head.addStretch(1)
        self.ai_sync_status = QLabel("Chưa đồng bộ")
        self.ai_sync_status.setObjectName("warnText")
        head.addWidget(self.ai_sync_status)
        rl.addLayout(head)

        self.scene_table = QTableWidget(0, 4)
        self.scene_table.setHorizontalHeaderLabels([
            "Time", "Nội dung cảnh", "US Voice", "Vietnamese"
        ])
        self.scene_table.verticalHeader().setVisible(False)
        h = self.scene_table.horizontalHeader()
        h.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        h.setSectionResizeMode(1, QHeaderView.Stretch)
        h.setSectionResizeMode(2, QHeaderView.Stretch)
        h.setSectionResizeMode(3, QHeaderView.Stretch)
        self.scene_table.setWordWrap(True)
        self.scene_table.itemChanged.connect(self.schedule_autosave)
        rl.addWidget(self.scene_table, 1)

        splitter.addWidget(left)
        splitter.addWidget(right)
        splitter.setSizes([430, 1250])

    # ------------------------------------------------------------------
    # DOWNLOADER
    # ------------------------------------------------------------------
    def _build_download_tab(self):
        root = QVBoxLayout(self.download_tab)

        box = QGroupBox(
            "Universal Video Downloader — Douyin / Bilibili / Youku / "
            "Xiaohongshu / TikTok / YouTube / Facebook / ..."
        )
        g = QGridLayout(box)

        self.url = QLineEdit()
        self.url.setPlaceholderText(
            "Dán URL HOẶC nguyên đoạn text chia sẻ. "
            "App tự bóc link https://... bên trong."
        )

        self.dl_detected = QLabel("Chưa nhận diện link")
        self.dl_detected.setObjectName("hint")
        self.dl_detected.setWordWrap(True)

        self.dl_dir = QLineEdit()

        self.dl_quality = QComboBox()
        self.dl_quality.addItems(["Best MP4", "1080p", "720p"])

        self.cookies_browser = QComboBox()
        self.cookies_browser.setEditable(True)
        self.cookies_browser.addItems([
            "Auto (khuyến nghị)",
            "Không dùng cookies",
            "cookies.txt",
            "edge",
            "chrome",
            "firefox",
            "brave",
        ])

        self.cookies_file = QLineEdit()
        self.cookies_file.setPlaceholderText(
            "Tùy chọn: cookies.txt (Netscape) — ổn định hơn Chrome DPAPI trên Windows"
        )

        choose_cookie = QPushButton("Chọn cookies.txt")
        choose_cookie.clicked.connect(self.choose_downloader_cookie_file)

        choose = QPushButton("Thư mục")
        choose.clicked.connect(self.choose_download_dir)

        clean_btn = QPushButton("Nhận diện link")
        clean_btn.clicked.connect(self.preview_download_url)

        self.dl_update_btn = QPushButton("Cập nhật yt-dlp")
        self.dl_update_btn.clicked.connect(self.update_downloader_engine)

        start = QPushButton("Tải video")
        start.setObjectName("success")
        start.clicked.connect(self.start_download)

        g.addWidget(QLabel("URL / Share text"), 0, 0)
        g.addWidget(self.url, 0, 1, 1, 4)

        g.addWidget(QLabel("Nhận diện"), 1, 0)
        g.addWidget(self.dl_detected, 1, 1, 1, 3)
        g.addWidget(clean_btn, 1, 4)

        g.addWidget(QLabel("Lưu tại"), 2, 0)
        g.addWidget(self.dl_dir, 2, 1, 1, 3)
        g.addWidget(choose, 2, 4)

        g.addWidget(QLabel("Quality"), 3, 0)
        g.addWidget(self.dl_quality, 3, 1)

        g.addWidget(QLabel("Cookies"), 3, 2)
        g.addWidget(self.cookies_browser, 3, 3)

        g.addWidget(start, 3, 4)

        g.addWidget(QLabel("Cookie file"), 4, 0)
        g.addWidget(self.cookies_file, 4, 1, 1, 3)
        g.addWidget(choose_cookie, 4, 4)

        engine_row = QWidget()
        er = QHBoxLayout(engine_row)
        er.setContentsMargins(0, 0, 0, 0)
        self.dl_engine_version = QLabel(
            "yt-dlp: " + downloader.yt_dlp_version()
        )
        self.dl_engine_version.setObjectName("hint")
        er.addWidget(self.dl_engine_version)
        er.addStretch(1)
        er.addWidget(self.dl_update_btn)
        g.addWidget(engine_row, 5, 0, 1, 5)

        note = QLabel(
            "Windows: Auto KHÔNG tự đọc Chrome/Edge/Firefox để tránh DPAPI/DB lock. "
            "App thử public + impersonation trước; nếu site cần cookie, chọn cookies.txt. "
            "Browser mode vẫn giữ để bạn chọn thủ công."
        )
        note.setObjectName("hint")
        note.setWordWrap(True)
        g.addWidget(note, 6, 0, 1, 5)

        root.addWidget(box)

        self.dl_log = QPlainTextEdit()
        self.dl_log.setReadOnly(True)
        root.addWidget(self.dl_log, 1)

    # ------------------------------------------------------------------
    # SETTINGS
    # ------------------------------------------------------------------
    def _build_settings_tab(self):
        root = QVBoxLayout(self.settings_tab)

        provider_box = QGroupBox("AI Provider")
        form = QFormLayout(provider_box)

        provider_row = QWidget()
        row = QHBoxLayout(provider_row)
        row.setContentsMargins(0, 0, 0, 0)

        self.ai_provider_group = QButtonGroup(self)
        self.ai_provider_radios = {}
        for i, name in enumerate(
            ["Google Gemini", "CKEY", "OpenAI", "DeepSeek"]
        ):
            radio = QRadioButton(name)
            self.ai_provider_group.addButton(radio, i)
            self.ai_provider_radios[name] = radio
            row.addWidget(radio)
        row.addStretch(1)

        self.ai_provider_key_label = QLabel("CKEY API Key")
        self.ai_provider_key = QLineEdit()
        self.ai_provider_key.setEchoMode(QLineEdit.Password)
        self.ai_provider_key.setPlaceholderText("sk-xxxxxxxx")

        self.ai_base_url = QLineEdit()
        self.ai_base_url.setText("https://api.xah.io/v1")

        self.model = QComboBox()
        self.model.setEditable(True)
        self.model.addItems([
            "levuphong2909/gemini-3.7-flash-high",
            "gemini-3.7-flash",
            "gpt-4.1-mini",
            "deepseek-chat",
        ])

        self.ai_endpoint_preview = QLabel("")
        self.ai_endpoint_preview.setObjectName("hint")
        self.ai_endpoint_preview.setWordWrap(True)

        test = QPushButton("Test AI Provider")
        test.clicked.connect(self.test_ai_provider)

        form.addRow("AI Provider", provider_row)
        form.addRow(self.ai_provider_key_label, self.ai_provider_key)
        form.addRow("Base URL", self.ai_base_url)
        form.addRow("Model", self.model)
        form.addRow("Endpoint", self.ai_endpoint_preview)
        form.addRow("", test)

        note = QLabel(
            "CKEY: AI Studio + Dịch Sub dùng OpenAI-compatible "
            "POST Base URL + /chat/completions. "
            "Không gọi Google GenAI khi Provider = CKEY. "
            "Log hiển thị HTTP status, Request ID, token usage và raw error."
        )
        note.setObjectName("hint")
        note.setWordWrap(True)
        form.addRow("", note)

        root.addWidget(provider_box)

        self._provider_key_cache = {}
        self._provider_model_cache = {}
        self._provider_base_cache = {}
        self._active_ai_provider = None

        self.ai_provider_group.buttonClicked.connect(
            lambda _button: self.on_ai_provider_changed()
        )
        self.ai_base_url.textChanged.connect(self.update_ai_endpoint_preview)
        self.model.currentTextChanged.connect(self.update_ai_endpoint_preview)

        tts_box = QGroupBox("Gemini TTS — cấu hình riêng")
        tf = QFormLayout(tts_box)

        self.tts_api_key = QLineEdit()
        self.tts_api_key.setEchoMode(QLineEdit.Password)
        self.tts_api_key.setPlaceholderText(
            "Google Gemini API key chỉ dùng khi Engine = Gemini TTS"
        )
        # Compatibility with existing TTS code.
        self.api_key = self.tts_api_key

        self.tts_model = QComboBox()
        self.tts_model.setEditable(True)
        self.tts_model.addItems([
            "gemini-3.1-flash-tts-preview",
            "gemini-2.5-flash-preview-tts",
        ])

        self.voice = QComboBox()
        self.voice.setEditable(True)
        self.voice.addItems(["Kore", "Puck", "Charon", "Fenrir", "Aoede"])

        self.voice_style = QPlainTextEdit()
        self.voice_style.setMaximumHeight(90)

        tf.addRow("Google TTS API Key", self.tts_api_key)
        tf.addRow("Gemini TTS Model", self.tts_model)
        tf.addRow("Gemini Voice", self.voice)
        tf.addRow("Voice direction", self.voice_style)

        tts_note = QLabel(
            "Nếu dùng Edge TTS / Windows SAPI thì không cần Google TTS key."
        )
        tts_note.setObjectName("hint")
        tts_note.setWordWrap(True)
        tf.addRow("", tts_note)

        root.addWidget(tts_box)

        path_box = QGroupBox("Ứng dụng ngoài")
        pf = QFormLayout(path_box)
        self.capcut_path = QLineEdit()
        choose_capcut = QPushButton("Chọn CapCut.exe")
        choose_capcut.clicked.connect(self.choose_capcut_path)

        caprow = QWidget()
        caprl = QHBoxLayout(caprow)
        caprl.setContentsMargins(0, 0, 0, 0)
        caprl.addWidget(self.capcut_path, 1)
        caprl.addWidget(choose_capcut)
        pf.addRow("CapCut", caprow)
        root.addWidget(path_box)

        save = QPushButton("Lưu Settings")
        save.clicked.connect(self.save_settings)
        root.addWidget(save)
        root.addStretch(1)

    def current_ai_provider(self):
        for name, radio in self.ai_provider_radios.items():
            if radio.isChecked():
                return name
        return "CKEY"

    def _stash_provider_fields(self):
        provider = self._active_ai_provider
        if not provider:
            return
        self._provider_key_cache[provider] = (
            self.ai_provider_key.text().strip()
        )
        self._provider_model_cache[provider] = (
            self.model.currentText().strip()
        )
        self._provider_base_cache[provider] = (
            self.ai_base_url.text().strip()
        )

    def on_ai_provider_changed(self, initial=False):
        provider = self.current_ai_provider()

        if not initial:
            self._stash_provider_fields()

        defaults = ai.provider_defaults(provider)

        key = self._provider_key_cache.get(provider)
        if key is None:
            key = self.settings.get_provider_api_key(provider)
            self._provider_key_cache[provider] = key

        if provider not in self._provider_model_cache:
            saved = self.settings.data.get("provider_models", {}) or {}
            self._provider_model_cache[provider] = saved.get(
                provider,
                defaults["model"],
            )

        if provider not in self._provider_base_cache:
            saved = self.settings.data.get("provider_base_urls", {}) or {}
            self._provider_base_cache[provider] = saved.get(
                provider,
                defaults["base_url"],
            )

        self.ai_provider_key.blockSignals(True)
        self.ai_base_url.blockSignals(True)
        self.model.blockSignals(True)

        self.ai_provider_key.setText(
            self._provider_key_cache.get(provider, "")
        )
        self.ai_base_url.setText(
            self._provider_base_cache.get(provider, "")
        )
        self.model.setCurrentText(
            self._provider_model_cache.get(provider, "")
        )

        self.ai_provider_key.blockSignals(False)
        self.ai_base_url.blockSignals(False)
        self.model.blockSignals(False)

        labels = {
            "Google Gemini": "Google Gemini API Key",
            "CKEY": "CKEY API Key",
            "OpenAI": "OpenAI API Key",
            "DeepSeek": "DeepSeek API Key",
        }
        placeholders = {
            "Google Gemini": "AIza...",
            "CKEY": "sk-xxxxxxxx",
            "OpenAI": "sk-...",
            "DeepSeek": "sk-...",
        }

        self.ai_provider_key_label.setText(
            labels.get(provider, "API Key")
        )
        self.ai_provider_key.setPlaceholderText(
            placeholders.get(provider, "")
        )
        self.ai_base_url.setEnabled(provider != "Google Gemini")

        self._active_ai_provider = provider
        self.update_ai_endpoint_preview()

    def update_ai_endpoint_preview(self, *args):
        provider = self.current_ai_provider()

        if provider == "Google Gemini":
            self.ai_endpoint_preview.setText(
                "Google GenAI SDK"
            )
            return

        base = self.ai_base_url.text().strip().rstrip("/")
        endpoint = (
            base
            if base.endswith("/chat/completions")
            else base + "/chat/completions"
        ) if base else "(chưa có Base URL)"

        self.ai_endpoint_preview.setText(
            f"POST {endpoint}"
        )

    def current_ai_config(self):
        return ai.AIConfig(
            provider=self.current_ai_provider(),
            api_key=self.ai_provider_key.text().strip(),
            base_url=self.ai_base_url.text().strip(),
            model=self.model.currentText().strip(),
            timeout_seconds=150,
        )


    # ==================================================================
    # STYLE
    # ==================================================================
    def _style(self):
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background:#0d1727; color:#eef4ff; font-size:12px;
            }
            QTabWidget::pane { border:1px solid #33445e; }
            QTabBar::tab {
                background:#142137; padding:10px 18px; border:1px solid #33445e;
            }
            QTabBar::tab:selected { background:#169fe2; color:white; }
            QGroupBox {
                border:1px solid #40516c; border-radius:5px;
                margin-top:10px; padding-top:12px; font-weight:650;
            }
            QLineEdit, QPlainTextEdit, QComboBox, QSpinBox, QDoubleSpinBox,
            QListWidget, QTableWidget, QFontComboBox {
                background:#121f32; color:#f4f7fb;
                border:1px solid #465773; border-radius:3px; padding:5px;
            }
            QPushButton {
                background:#168fce; color:white; border:0;
                border-radius:6px; padding:8px 12px; font-weight:650;
            }
            QPushButton:hover { background:#22a7ea; }
            QPushButton#success { background:#18c567; }
            QPushButton#danger { background:#f0444a; }
            QPushButton#dangerSmall { background:#ee4a4f; padding:6px; }
            QPushButton#greenSmall { background:#20c86d; padding:6px; }
            QPushButton#yellow { background:#e9b600; color:#152033; }
            QPushButton#cyan { background:#0aaee9; }
            QPushButton#purple { background:#7548ed; }
            QPushButton#ratio { background:#31425f; padding:5px 9px; }
            QPushButton#hero {
                background:#237bdf; color:white; font-size:14px;
                border-radius:7px; padding:13px;
            }
            QCheckBox::indicator {
                width:32px; height:17px; border-radius:8px;
                background:#657080;
            }
            QCheckBox::indicator:checked { background:#1ed178; }
            QHeaderView::section {
                background:#17263b; color:#eef4ff; padding:7px;
                border:0; border-right:1px solid #3b4c66;
            }
            QProgressBar {
                background:#15243a; border:1px solid #40516c; text-align:center;
            }
            QProgressBar::chunk { background:#2b73ee; }
            QPlainTextEdit#blackLog { background:#03080d; color:#2df98d; }
            QFrame#previewFrame { background:#05080d; border:1px solid #3d4d66; }
            QFrame#audioStrip { background:#101b2d; border-top:1px solid #3b4d68; }
            QSplitter::handle { background:#23364f; }
            QSplitter::handle:hover { background:#169fe2; }
            QSplitter::handle:horizontal { width:7px; margin:0 1px; }
            QSplitter::handle:vertical { height:7px; margin:1px 0; }
            QScrollBar:vertical { background:#101b2d; width:11px; margin:0; }
            QScrollBar::handle:vertical { background:#405675; min-height:26px; border-radius:5px; }
            QScrollBar::handle:vertical:hover { background:#169fe2; }
            QScrollBar:horizontal { background:#101b2d; height:11px; margin:0; }
            QScrollBar::handle:horizontal { background:#405675; min-width:26px; border-radius:5px; }
            QScrollBar::handle:horizontal:hover { background:#169fe2; }
            QLabel#hint { color:#91a6c2; font-size:11px; }
            QLabel#readyText { color:#24e383; font-weight:700; }
            QLabel#warnText { color:#ffd000; font-weight:700; }
            QLabel#dialogTitle { font-size:18px;font-weight:700;color:#20b9ff;padding:8px; }
            QFrame#topBar {
                background:#111c2c; border:1px solid #2a3b52; border-radius:10px;
            }
            QLabel#brandLabel { color:#f4f8ff; font-size:14px; font-weight:800; padding:0 10px; }
            QLabel#projectStatus { color:#8ea3bd; padding:0 10px; }
            QPushButton#navButton {
                background:transparent; color:#9fb0c6; border-radius:7px; padding:9px 12px;
            }
            QPushButton#navButton:hover { background:#1c2b40; color:#ffffff; }
            QPushButton#navButton:checked { background:#243a57; color:#ffffff; }
            QPushButton#topExport { background:#2f7df4; padding:10px 22px; }
            QFrame#leftWorkspace, QFrame#inspectorPanel, QWidget#toolPage {
                background:#101a29; border:1px solid #26374d; border-radius:9px;
            }
            QFrame#toolNav { background:#0b1320; border-right:1px solid #26374d; }
            QPushButton#toolButton {
                background:transparent; color:#91a5bf; border-radius:8px;
                padding:4px; font-size:10px;
            }
            QPushButton#toolButton:hover { background:#1b2b41; color:white; }
            QPushButton#toolButton:checked { background:#245ea7; color:white; }
            QLabel#panelTitle { font-size:15px; font-weight:750; color:#f5f8fd; padding:4px; }
            QLabel#inspectorHeading { font-size:14px; font-weight:700; color:#7db7ff; padding:5px 0; }
            QLabel#emptyIcon { color:#527296; font-size:34px; }
            QLabel#emptyTitle { color:#dbe8f7; font-size:14px; font-weight:700; }
            QFrame#mediaDropArea { border:1px dashed #46617f; border-radius:9px; background:#0b1523; }
            QFrame#mediaCard { border:1px solid #2b3c52; border-radius:8px; background:#142236; }
            QFrame#mediaCard:hover { border-color:#3f8ce8; background:#182a42; }
            QLabel#mediaThumb { background:#080e17; border-radius:6px; color:#5d7999; font-size:20px; }
            QPushButton#cardAdd { background:#2878da; border-radius:14px; padding:0; font-size:18px; }
        """)

    # ==================================================================
    # SETTINGS / WORKER
    # ==================================================================
    def _load_settings_to_ui(self):
        d = self.settings.data

        provider = d.get("ai_provider", "CKEY")
        if provider not in self.ai_provider_radios:
            provider = "CKEY"

        self._provider_model_cache = dict(
            d.get("provider_models", {}) or {}
        )
        self._provider_base_cache = dict(
            d.get("provider_base_urls", {}) or {}
        )
        self._provider_key_cache = {
            name: self.settings.get_provider_api_key(name)
            for name in self.ai_provider_radios
        }

        self.ai_provider_radios[provider].setChecked(True)
        self._active_ai_provider = None
        self.on_ai_provider_changed(initial=True)

        self.tts_model.setCurrentText(
            d.get("tts_model", "gemini-3.1-flash-tts-preview")
        )
        self.voice.setCurrentText(d.get("voice", "Kore"))
        self.voice_style.setPlainText(
            d.get(
                "voice_style",
                "Natural American documentary narrator, confident, curious, medium pace.",
            )
        )
        self.tts_api_key.setText(self.settings.get_api_key())

        self.tts_engine.setCurrentText(
            d.get("tts_engine", "Piper Offline (Free)")
        )
        QTimer.singleShot(0, self.on_tts_engine_changed)
        saved_voice = d.get("tts_voice", "en_US-lessac-medium")
        QTimer.singleShot(
            0,
            lambda v=saved_voice: self.tts_voice.setCurrentText(v),
        )

        self.output_dir.setText(
            d.get("output_dir", str(ROOT / "exports"))
        )
        self.dl_dir.setText(
            d.get("download_dir", str(ROOT / "downloads"))
        )

        saved_cookie = d.get(
            "cookies_browser",
            "Auto (khuyến nghị)",
        )
        self.cookies_browser.setCurrentText(
            saved_cookie or "Auto (khuyến nghị)"
        )
        self.cookies_file.setText(d.get("cookies_file", ""))
        self.capcut_path.setText(d.get("capcut_path", ""))

        if hasattr(self, "market"):
            self.market.setCurrentText(
                d.get("ai_market", self.market.currentText())
            )
        if hasattr(self, "script_style"):
            saved_style = d.get("ai_script_style", "Factory documentary")
            if self.script_style.findText(saved_style) >= 0:
                self.script_style.setCurrentText(saved_style)
            self.update_script_style_translation(
                self.script_style.currentText()
            )


    def save_settings(self):
        self._stash_provider_fields()
        provider = self.current_ai_provider()

        self.settings.data.update({
            "ai_provider": provider,
            "model": self.model.currentText().strip(),
            "ai_base_url": self.ai_base_url.text().strip(),
            "provider_models": dict(self._provider_model_cache),
            "provider_base_urls": dict(self._provider_base_cache),
            "tts_model": self.tts_model.currentText().strip(),
            "voice": self.voice.currentText().strip(),
            "voice_style": self.voice_style.toPlainText().strip(),
            "tts_engine": self.tts_engine.currentText().strip(),
            "tts_voice": self.tts_voice.currentText().strip(),
            "output_dir": self.output_dir.text().strip(),
            "download_dir": self.dl_dir.text().strip(),
            "cookies_browser": self.cookies_browser.currentText().strip(),
            "cookies_file": self.cookies_file.text().strip(),
            "capcut_path": self.capcut_path.text().strip(),
            "ai_market": (
                self.market.currentText() if hasattr(self, "market") else "US"
            ),
            "ai_script_style": (
                self.script_style.currentText()
                if hasattr(self, "script_style")
                else "Factory documentary"
            ),
        })
        self.settings.save()

        for name, key in self._provider_key_cache.items():
            if (key or "").strip():
                self.settings.set_provider_api_key(name, key)

        if self.tts_api_key.text().strip():
            self.settings.set_api_key(
                self.tts_api_key.text().strip()
            )

        QMessageBox.information(
            self,
            "Settings",
            f"Đã lưu. AI Provider: {provider}",
        )


    def _retain_worker(self, worker: Worker):
        """Keep QThread alive until Qt emits finished.

        v0.8 could drop the last Python reference inside the custom `done` signal,
        while QThread.run() had not returned yet. On Windows/PySide this can abort
        the whole process with `QThread: Destroyed while thread is still running`.
        """
        if worker not in self._active_workers:
            self._active_workers.append(worker)

        def cleanup():
            try:
                if worker in self._active_workers:
                    self._active_workers.remove(worker)
                if self.worker is worker:
                    self.worker = None
                if self.preview_worker is worker:
                    self.preview_worker = None
                if self.auto_detect_worker is worker:
                    self.auto_detect_worker = None
                worker.deleteLater()
                if self.preview_dirty and not (self.worker and self.worker.isRunning()):
                    self.preview_render_timer.start()
            except Exception as e:
                self.log_line(f"[THREAD CLEANUP] {e}")

        worker.finished.connect(cleanup)

    def run_worker(self, title, fn, done):
        if self.worker and self.worker.isRunning():
            QMessageBox.information(self, "Đang chạy", "Hãy chờ tác vụ hiện tại hoàn tất.")
            return

        self.status(title)
        self.progress.setRange(0, 0)
        worker = Worker(fn)
        self.worker = worker
        self._retain_worker(worker)
        worker.progress.connect(self.worker_progress)
        worker.log.connect(self.route_log)
        worker.error.connect(self.worker_error)

        def result_ready(result):
            # Never destroy/clear the QThread here. This signal is emitted from
            # inside Worker.run(), before run() has fully returned.
            self.progress.setRange(0, 100)
            self.progress.setValue(100)
            try:
                done(result)
            except Exception:
                tb = traceback.format_exc()
                self.log_line("[RESULT HANDLER ERROR]\n" + tb)
                QMessageBox.critical(self, "Lỗi xử lý kết quả", tb[-3000:])

        worker.done.connect(result_ready)
        worker.start()

    def worker_progress(self, current, total):
        self.progress.setRange(0, max(1, total))
        self.progress.setValue(current)

    def worker_error(self, tb):
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.status("Error")

        markers = [
            "core.ai_provider.AIProviderError:",
            "AIProviderError:",
            "core.ffmpeg_engine.FFmpegError:",
            "core.gemini_engine.GeminiError:",
            "core.vocal_separator.VocalSeparationError:",
            "core.tts_engine.TTSError:",
            "FFmpegError:", "GeminiError:", "VocalSeparationError:", "TTSError:",
        ]
        message = ""
        for marker in markers:
            pos = tb.rfind(marker)
            if pos >= 0:
                message = tb[pos + len(marker):].strip()
                break
        if not message:
            lines = [x for x in tb.splitlines() if x.strip()]
            important = [
                x for x in lines
                if any(k in x.lower() for k in (
                    "error", "failed", "invalid", "permission denied",
                    "no such file", "cannot", "could not", "unknown encoder",
                ))
            ]
            selected = (important[-8:] + lines[-8:]) if important else lines[-16:]
            seen, compact = set(), []
            for line in selected:
                if line not in seen:
                    compact.append(line)
                    seen.add(line)
            message = "\n".join(compact[-16:])
        QMessageBox.critical(self, "Lỗi", message)

    def route_log(self, text):
        text = str(text)
        self.log_line(text)
        if text.startswith("[DOWNLOAD]"):
            self.dl_log.appendPlainText(text[len("[DOWNLOAD]"):].lstrip())

    def log_line(self, text):
        if hasattr(self, "log"):
            self.log.appendPlainText(str(text))

    def status(self, text):
        if hasattr(self, "status_label"):
            self.status_label.setText(str(text))
        self.statusBar().showMessage(str(text))

    # ==================================================================
    # PROJECT AUTOSAVE / RESTORE
    # ==================================================================
    def project_workspace_for(self, video_path: str) -> Path:
        p = Path(video_path).resolve()
        short = hashlib.sha1(str(p).encode("utf-8", errors="ignore")).hexdigest()[:8]
        folder = ROOT / "projects" / f"{p.stem[:60]}_{short}"
        folder.mkdir(parents=True, exist_ok=True)
        return folder

    def ai_workspace(self) -> Path:
        video = self.ai_video_path.text().strip() or self.project.video_path
        if not video or not Path(video).exists():
            raise RuntimeError("Chưa chọn video hợp lệ.")
        folder = self.project_workspace_for(video)
        self.project.video_path = str(Path(video))
        self.project.workspace = str(folder)
        return folder

    def project_autosave_path(self) -> Path | None:
        if not self.project.video_path:
            return None
        if self.project.workspace:
            folder = Path(self.project.workspace)
        else:
            folder = self.project_workspace_for(self.project.video_path)
            self.project.workspace = str(folder)
        folder.mkdir(parents=True, exist_ok=True)
        return folder / "project.json"

    def schedule_autosave(self, *args):
        if self._restoring_state:
            return
        if self.project.video_path:
            if hasattr(self, "top_bar"):
                self.top_bar.set_project_status("Saving…")
            self.autosave_timer.start()

    def capture_project_state(self):
        self.sync_scene_table()
        self.project.analysis_summary = self.ai_summary.toPlainText()
        self.project.transcript = self.transcript.toPlainText()
        self.project.narration_path = self.narration_path or self.voice_file.text().strip()
        self.project.subtitle_path = self.sub_path.text().strip()
        self.project.processed_preview_path = self.processed_preview_path
        self.project.export_state = self.export_state_dict()

    def autosave_project(self):
        path = self.project_autosave_path()
        if not path:
            return
        try:
            self.capture_project_state()
            self.project.save(path)
            self.settings.data["last_project"] = str(path)
            self.settings.save()
            self.autosave_label.setText(f"● Auto-save: {path.name}")
            if hasattr(self, "top_bar"):
                self.top_bar.set_project_status(f"Autosaved  •  {path.name}")
        except Exception as e:
            self.status(f"Auto-save lỗi: {e}")
            if hasattr(self, "top_bar"):
                self.top_bar.set_project_status("Autosave error")

    def save_ai_project(self):
        if not self.project.video_path:
            QMessageBox.warning(self, "Project", "Chưa có project.")
            return
        self.capture_project_state()
        default = str(self.project_autosave_path() or (ROOT / "project.json"))
        path, _ = QFileDialog.getSaveFileName(
            self, "Lưu Project", default, "Machine Studio Project (*.json)"
        )
        if not path:
            return
        if not path.lower().endswith(".json"):
            path += ".json"
        self.project.save(path)
        self.settings.data["last_project"] = path
        self.settings.save()
        self.status(f"Đã lưu project: {path}")

    def open_ai_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Mở Project", "", "Machine Studio Project (*.json)"
        )
        if path:
            self.load_project_file(path, show_message=True)

    def load_project_file(self, path: str, show_message=False):
        try:
            project = AIProject.load(path)
            self.project = project
            self.ai_video_path.setText(project.video_path)
            self.ai_summary.setPlainText(project.analysis_summary)
            self.transcript.setPlainText(project.transcript)
            self.narration_path = project.narration_path or ""
            self.processed_preview_path = project.processed_preview_path or ""
            self.voice_file.setText(self.narration_path)
            self.preview_is_processed = False
            self.sub_path.setText(project.subtitle_path or "")
            self.refresh_scene_table()
            self.apply_export_state(project.export_state or {})
            self.transfer_ai_to_exporter(switch_tab=False)
            if project.subtitle_path and Path(project.subtitle_path).exists():
                self.load_subtitle_file(project.subtitle_path)
            self.settings.data["last_project"] = path
            self.settings.save()
            if show_message:
                QMessageBox.information(self, "Project", "Đã khôi phục project.")
        except Exception as e:
            QMessageBox.critical(self, "Project", str(e))

    def restore_last_project(self):
        path = self.settings.data.get("last_project", "")
        if path and Path(path).exists():
            self.load_project_file(path, show_message=False)
            self.status("Đã tự khôi phục project gần nhất.")

    def closeEvent(self, event: QCloseEvent):
        running = [w for w in self._active_workers if w and w.isRunning()]
        if running:
            answer = QMessageBox.question(
                self, "Tác vụ đang chạy",
                "Ứng dụng vẫn đang xử lý nền/xuất video. Dừng tác vụ trước khi thoát để tránh hỏng file?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if answer == QMessageBox.No:
                event.ignore()
                return
            self.stop_current()
            # Background cache normally completes quickly; let QThread finish cleanly.
            for worker in list(running):
                try:
                    worker.requestInterruption()
                    worker.wait(1800)
                except Exception:
                    pass
            still = [w for w in self._active_workers if w and w.isRunning()]
            if still:
                self.status("Đang dừng tác vụ nền... hãy đóng lại sau vài giây.")
                event.ignore()
                return
        try:
            self.autosave_project()
        except Exception:
            pass
        event.accept()

    # ==================================================================
    # AI STUDIO
    # ==================================================================
    def choose_ai_video(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn video", "", "Video (*.mp4 *.mov *.mkv *.avi *.webm)"
        )
        if path:
            self.set_ai_video(path)

    def use_export_selection_for_ai(self):
        path = self.current_video()
        if not path:
            QMessageBox.warning(
                self, "AI Studio",
                "Chưa chọn video ở Video Exporter."
            )
            return
        self.set_ai_video(path)
        self.status("AI Studio đã nhận video đang chọn từ Exporter.")

    def set_ai_video(self, path: str):
        path = str(Path(path))
        existing = self.project_workspace_for(path) / "project.json"
        if existing.exists():
            self.load_project_file(str(existing), show_message=False)
            self.status("Đã tìm thấy project cũ và tự khôi phục.")
            return

        self.project = AIProject(video_path=path)
        self.project.workspace = str(self.project_workspace_for(path))
        self.ai_video_path.setText(path)
        self.ai_summary.clear()
        self.transcript.clear()
        self.narration_path = ""
        self.voice_file.clear()
        self.sub_path.clear()
        self.sub_editor.clear()
        self.refresh_scene_table()
        self.schedule_autosave()

    def _fast_model_id(self):
        return self.model.currentText().strip()

    def _adaptive_ai_sampling(self, duration: float):
        duration = max(1.0, float(duration or 0))
        if duration <= 30:
            target = 6
        elif duration <= 90:
            target = 8
        elif duration <= 240:
            target = 10
        else:
            target = 12
        return target, max(2.0, duration / target)

    def update_script_style_translation(self, style_name):
        if hasattr(self, "script_style_vi"):
            self.script_style_vi.setText(
                AI_STYLE_LIBRARY.get(
                    str(style_name),
                    "Phong cách tùy chỉnh — giữ tên tiếng Anh trong prompt.",
                )
            )

    def ai_fast_pipeline(self):
        video = self.ai_video_path.text().strip()
        if not video or not Path(video).exists():
            QMessageBox.warning(self, "AI", "Hãy chọn video trước.")
            return

        config = self.current_ai_config()
        if not config.api_key:
            QMessageBox.warning(
                self,
                "AI Provider",
                f"Vào Settings → nhập {config.provider} API Key → Test AI Provider.",
            )
            return

        try:
            workspace = self.ai_workspace()
        except Exception as e:
            QMessageBox.warning(self, "AI", str(e))
            return

        model = config.model
        market = self.market.currentText()
        style = self.script_style.currentText()
        include_audio = self.ai_include_audio.isChecked()
        frames_dir = workspace / "fast_frames"
        audio_path = workspace / "fast_source_audio.wav"

        def job(progress, log):
            info = ffm.probe(self.project.video_path)
            self.project.duration = info["duration"]
            _, interval = self._adaptive_ai_sampling(self.project.duration)
            self.project.interval = interval
            log(
                f"[AI FAST] duration={self.project.duration:.1f}s | "
                f"interval={interval:.1f}s | provider={config.provider} | model={model}"
            )
            if config.provider != "Google Gemini":
                try:
                    log(f"[AI FAST] endpoint={ai.chat_endpoint(config.base_url)}")
                except Exception:
                    pass

            self.project.scenes = ffm.extract_frames(
                self.project.video_path,
                str(frames_dir),
                interval,
                width=720,
            )
            progress(1, 3)

            self.project.source_audio = ""
            if include_audio and info.get("has_audio"):
                self.project.source_audio = ffm.extract_audio(
                    self.project.video_path, str(audio_path)
                )

            log(
                f"[AI FAST] frames={len(self.project.scenes)} | "
                f"source_audio={'YES' if include_audio else 'NO'}"
            )
            result = ai.fast_analyze_and_script(
                config=config,
                scenes=self.project.scenes,
                market=market,
                style=style,
                audio_path=self.project.source_audio if include_audio else "",
                log=log,
            )
            progress(2, 3)

            self.project.topic = result.get("topic", "")
            self.project.analysis_summary = result.get("summary", "")
            self.project.transcript = result.get("transcript", "")
            self.project.scenes = result.get("scenes", self.project.scenes)
            progress(3, 3)
            return result

        def done(_):
            self.ai_summary.setPlainText(self.project.analysis_summary)
            self.transcript.setPlainText(self.project.transcript)
            self.refresh_scene_table()

            # IMPORTANT workflow requested by user:
            # persist first, then transfer script to Exporter voice section.
            self.autosave_project()
            self.transfer_ai_to_exporter(switch_tab=False)

            self.ai_sync_status.setText("✓ Đã gửi sang Video Exporter")
            self.status("AI viết xong → project đã lưu → kịch bản đã chuyển sang Lồng Tiếng.")
            QMessageBox.information(
                self, "AI hoàn tất",
                "Kịch bản đã được tự lưu và đồng bộ sang Video Exporter → Lồng Tiếng (TTS).\n\n"
                "Bạn có thể sửa câu trong Timeline; mọi thay đổi tiếp tục được auto-save."
            )

        self.run_worker("AI đang hiểu video + viết kịch bản...", job, done)

    def refresh_scene_table(self):
        self.scene_table.blockSignals(True)
        self.scene_table.setRowCount(len(self.project.scenes))
        for row, scene in enumerate(self.project.scenes):
            meaning = scene.source_meaning or scene.visual
            if scene.chinese_text:
                meaning = (meaning + "\nCN: " + scene.chinese_text).strip()
            values = [
                f"{fmt_time(scene.start)}–{fmt_time(scene.end)}",
                meaning,
                scene.en_voice,
                scene.vi_voice,
            ]
            for col, value in enumerate(values):
                item = QTableWidgetItem(value)
                if col == 0:
                    item.setFlags(item.flags() & ~Qt.ItemIsEditable)
                self.scene_table.setItem(row, col, item)
            self.scene_table.setRowHeight(row, 86)
        self.scene_table.blockSignals(False)

    def sync_scene_table(self):
        if self.scene_table.rowCount() != len(self.project.scenes):
            return
        for row, scene in enumerate(self.project.scenes):
            meaning = self.scene_table.item(row, 1)
            en = self.scene_table.item(row, 2)
            vi = self.scene_table.item(row, 3)
            if meaning:
                scene.source_meaning = meaning.text()
            if en:
                scene.en_voice = en.text()
            if vi:
                scene.vi_voice = vi.text()

    def transfer_ai_to_exporter(self, switch_tab=False):
        if self.project.video_path:
            self.add_paths([self.project.video_path])
            try:
                idx = self.queue.index(self.project.video_path)
                self.queue_list.setCurrentRow(idx)
            except Exception:
                pass

        count = sum(1 for s in self.project.scenes if (s.en_voice or "").strip())
        self.script_ready_label.setText(
            f"Kịch bản AI: {count} đoạn — SẴN SÀNG TẠO GIỌNG"
            if count else "Kịch bản AI: chưa có"
        )
        self.voice_status.setText(
            "Đã nhận dữ liệu từ AI Studio. Bấm Tạo Giọng Đọc."
            if count else "Chưa có kịch bản."
        )
        if self.project.narration_path and Path(self.project.narration_path).exists():
            self.narration_path = self.project.narration_path
            self.voice_file.setText(self.narration_path)
            self.mute_original_voice.setChecked(True)
        if self.project.subtitle_path and Path(self.project.subtitle_path).exists():
            self.sub_path.setText(self.project.subtitle_path)
        if switch_tab:
            self.tabs.setCurrentWidget(self.export_tab)

    # ==================================================================
    # LIVE MULTI-TRACK AUDIO PREVIEW
    # ==================================================================
    def set_aux_media_if_needed(self, player, path):
        path = str(path or "").strip()
        current = player.source().toLocalFile() if player.source().isLocalFile() else ""
        if path and Path(path).exists():
            if not current or str(Path(current)) != str(Path(path)):
                player.setSource(QUrl.fromLocalFile(str(Path(path))))
        elif current:
            player.stop()
            player.setSource(QUrl())

    def refresh_live_audio_sources(self):
        if self.preview_is_processed:
            # Processed render already contains final mix.
            for out in [self.narration_output, self.music_output, self.accompaniment_output]:
                out.setVolume(0.0)
            return

        narration = self.voice_file.text().strip() or self.narration_path
        music = self.music_file.text().strip()
        accompaniment = self.accompaniment_path if self.mute_original_voice.isChecked() else ""

        self.set_aux_media_if_needed(self.narration_player, narration)
        self.set_aux_media_if_needed(self.music_player, music)
        self.set_aux_media_if_needed(self.accompaniment_player, accompaniment)
        self.update_live_audio_mix()

    def update_live_audio_mix(self, *args):
        if self.preview_is_processed:
            self.audio_output.setVolume(max(0.0, min(1.0, self.source_volume.value() / 100)))
            self.narration_output.setVolume(0.0)
            self.music_output.setVolume(0.0)
            self.accompaniment_output.setVolume(0.0)
            return

        # Source video contains original audio.
        if self.mute_original_voice.isChecked():
            self.audio_output.setVolume(0.0)
        else:
            self.audio_output.setVolume(max(0.0, min(1.0, self.source_volume.value() / 100)))

        self.narration_output.setVolume(
            max(0.0, min(1.0, self.narration_volume.value() / 100))
            if (self.voice_file.text().strip() or self.narration_path) else 0.0
        )
        self.music_output.setVolume(
            0.0 if self.mute_music.isChecked()
            else max(0.0, min(1.0, self.music_volume.value() / 100))
        )
        self.accompaniment_output.setVolume(
            max(0.0, min(1.0, self.source_volume.value() / 100))
            if self.mute_original_voice.isChecked() and self.accompaniment_path else 0.0
        )

    def play_live_audio_tracks(self):
        if self.preview_is_processed:
            return
        self.refresh_live_audio_sources()
        pos = self.player.position()
        for aux in [self.narration_player, self.music_player, self.accompaniment_player]:
            if aux.source().isValid():
                aux.setPosition(pos)
                aux.play()

    def pause_live_audio_tracks(self):
        for aux in [self.narration_player, self.music_player, self.accompaniment_player]:
            aux.pause()

    def seek_live_audio_tracks(self, position_ms):
        for aux in [self.narration_player, self.music_player, self.accompaniment_player]:
            if aux.source().isValid():
                aux.setPosition(int(position_ms))

    def on_live_music_status(self, status):
        if (
            status == QMediaPlayer.EndOfMedia
            and not self.mute_music.isChecked()
            and self.player.playbackState() == QMediaPlayer.PlayingState
        ):
            self.music_player.setPosition(0)
            self.music_player.play()

    def sync_live_audio_tracks(self):
        if self.preview_is_processed or self.player.playbackState() != QMediaPlayer.PlayingState:
            return
        main_pos = self.player.position()
        for aux in [self.narration_player, self.music_player, self.accompaniment_player]:
            if not aux.source().isValid():
                continue
            # Correct drift without constant seeking.
            if abs(aux.position() - main_pos) > 180:
                aux.setPosition(main_pos)
            if aux.playbackState() != QMediaPlayer.PlayingState:
                aux.play()

    def set_wheel_input_lock(self, checked):
        global WHEEL_INPUT_LOCKED
        WHEEL_INPUT_LOCKED = bool(checked)

        # Clear any old focused spin/combo so a previously clicked field
        # cannot keep receiving wheel input unexpectedly.
        if WHEEL_INPUT_LOCKED:
            widget = QApplication.focusWidget()
            if isinstance(widget, (_QSpinBox, _QDoubleSpinBox, _QComboBox)):
                try:
                    widget.clearFocus()
                    if hasattr(widget, "_wheel_armed"):
                        widget._wheel_armed = False
                except Exception:
                    pass

        self.status(
            "Đã khóa con lăn thông số."
            if WHEEL_INPUT_LOCKED
            else "Đã mở khóa con lăn: click đúng ô rồi mới lăn được."
        )

    # ==================================================================
    # EXPORTER / QUEUE / PREVIEW
    # ==================================================================
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        videos = []
        for url in event.mimeData().urls():
            path = url.toLocalFile()
            if Path(path).suffix.lower() in {".mp4", ".mov", ".mkv", ".avi", ".webm"}:
                videos.append(path)
        if videos:
            self.add_paths(videos)
            event.acceptProposedAction()

    def toggle_export_log(self, checked):
        checked = bool(checked)
        self.log.setVisible(checked)
        self.log_toggle_btn.setText("▾ Log" if checked else "▸ Log")
        self.schedule_autosave()

    def add_paths(self, paths):
        existing = set(self.queue)
        for path in paths:
            p = str(Path(path))
            if p not in existing:
                self.queue.append(p)
                self.queue_list.addItem(QListWidgetItem(Path(p).name))
                existing.add(p)
        if self.queue and self.queue_list.currentRow() < 0:
            self.queue_list.setCurrentRow(0)
        self._refresh_professional_panels()

    def add_files(self):
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Chọn video", "", "Video (*.mp4 *.mov *.mkv *.avi *.webm)"
        )
        if paths:
            self.add_paths(paths)

    def remove_selected_queue(self):
        rows = sorted({idx.row() for idx in self.queue_list.selectedIndexes()}, reverse=True)
        for row in rows:
            if 0 <= row < len(self.queue):
                self.queue.pop(row)
                self.queue_list.takeItem(row)
        self._refresh_professional_panels()

    def current_video(self):
        row = self.queue_list.currentRow()
        if 0 <= row < len(self.queue):
            return self.queue[row]
        return ""

    def queue_selection_changed(self, row):
        if not (0 <= row < len(self.queue)):
            return
        path = self.queue[row]

        # Once the Basic Editor timeline is active, the timeline is the source
        # of truth. Selecting the same media in the queue selects its timeline
        # clip instead of reopening the untrimmed 1:06 source video.
        if self.editor_timeline_active():
            try:
                wanted = Path(path).resolve()
                for i, clip in enumerate(self.editor_clips):
                    if Path(str(clip.get("path", ""))).resolve() == wanted:
                        self.editor_clip_selected(i)
                        self.editor_update_master_timeline_ui(
                            editor_engine.timeline_ranges(self.editor_clips)[i][0]
                        )
                        return
            except Exception:
                pass

        self.preview_is_processed = False
        self.load_preview_media(path, autoplay=False)
        self.preview_state.setText("⚡ Live Preview")
        self.refresh_live_audio_sources()
        self.update_live_overlay_state()

        # Auto-link existing project generated by AI Studio.
        project_path = self.project_workspace_for(path) / "project.json"
        if project_path.exists() and self.project.video_path != path:
            self.load_project_file(str(project_path), show_message=False)

    def toggle_export_side_panel(self, side, checked):
        checked = bool(checked)
        panel = (
            getattr(self, "export_left_panel", None)
            if side == "left"
            else getattr(self, "export_right_panel", None)
        )
        if panel is not None:
            panel.setVisible(checked)
        self.schedule_autosave()

    def set_preview_zoom_percent(self, percent):
        self.preview_zoom_percent = self.preview_service.set_zoom(percent)
        if hasattr(self, "preview_zoom_label"):
            self.preview_zoom_label.setText(
                f"{self.preview_zoom_percent}%"
            )
        if hasattr(self, "live_overlay"):
            self.live_overlay.set_preview_zoom(
                self.preview_zoom_percent / 100.0,
                reset_pan=(self.preview_zoom_percent <= 100),
            )
        self.schedule_autosave()

    def _preview_zoom_mode_changed(self, text):
        if text == "Fit":
            self.preview_service.state.fit_mode = "Fit"
            self.reset_preview_zoom()
        elif text == "Fill":
            self.preview_service.state.fit_mode = "Fill"
            self.set_preview_zoom_percent(125)
        elif text.endswith("%"):
            self.set_preview_zoom_percent(int(text[:-1]))

    def set_project_aspect_ratio(self, text):
        ratios = {"16:9": 16/9, "9:16": 9/16, "1:1": 1.0, "4:3": 4/3, "3:4": 3/4, "21:9": 21/9, "2:1": 2.0, "5:4": 5/4, "4:5": 4/5}
        self.editor_document.aspect_ratio = str(text)
        self.preview_service.state.aspect_ratio = str(text)
        aspect = self._source_aspect_cache.get(self.current_video(), 9/16) if text == "Original" else ratios.get(text, 9/16)
        self.live_overlay.set_output_aspect(aspect)
        self.schedule_autosave()

    def _preview_playback_state_changed(self, state):
        if hasattr(self, "preview_play_button"):
            self.preview_play_button.setText("❚❚ Pause" if state == QMediaPlayer.PlayingState else "▶ Play")

    def change_preview_zoom(self, delta):
        self.set_preview_zoom_percent(
            self.preview_zoom_percent + int(delta)
        )

    def reset_preview_zoom(self):
        self.preview_zoom_percent = 100
        if hasattr(self, "preview_zoom_label"):
            self.preview_zoom_label.setText("100%")
        if hasattr(self, "live_overlay"):
            self.live_overlay.reset_preview_view()
        self.schedule_autosave()

    def toggle_play(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
            self.pause_live_audio_tracks()
            self.preview_state.setText("Paused")
            return

        # Timeline mode uses one global clock even though Qt is decoding one
        # source clip at a time. Play therefore starts from the edited timeline.
        if self.editor_timeline_active():
            current_global = self.editor_current_global_second()
            total = self.editor_master_total()
            if current_global >= total - 0.03:
                current_global = 0.0

            if self.editor_flattened_preview_loaded():
                if self.player.mediaStatus() in (QMediaPlayer.NoMedia, QMediaPlayer.InvalidMedia):
                    self.editor_render_preview()
                    return
                self.player.setPosition(int(current_global * 1000))
                self.player.play()
            else:
                self.editor_seek_global(current_global, autoplay=True)
            self.play_live_audio_tracks()
            self.preview_state.setText("Playing Timeline")
            return

        status = self.player.mediaStatus()
        if status in (QMediaPlayer.NoMedia, QMediaPlayer.InvalidMedia):
            path = self.current_video() or self.project.video_path
            if not path or not Path(path).exists():
                self.preview_state.setText("Không có media")
                return
            self.preview_is_processed = False
            self.load_preview_media(path, autoplay=True)
            QTimer.singleShot(220, self.play_live_audio_tracks)
            return

        if status == QMediaPlayer.EndOfMedia:
            self.player.setPosition(0)
            self.seek_live_audio_tracks(0)

        self.player.play()
        self.play_live_audio_tracks()
        self.preview_state.setText("Playing")

    def on_preview_duration(self, duration_ms):
        if self.editor_timeline_active():
            self.editor_update_master_timeline_ui()
            return
        self.timeline_slider.setRange(0, max(0, int(duration_ms)))
        self.preview_total.setText(fmt_time(duration_ms / 1000))

    def on_preview_position(self, position_ms):
        source_sec = position_ms / 1000.0
        if self.editor_timeline_active():
            global_sec = self.editor_sync_playhead_from_source(source_sec)
            # Subtitle/layers are defined on the edited global timeline.
            self.update_preview_subtitle(global_sec)
        else:
            if not self.timeline_slider.isSliderDown():
                self.timeline_slider.setValue(int(position_ms))
            self.preview_current.setText(fmt_time(source_sec))
            self.update_preview_subtitle(source_sec)
        self.update_live_overlay_state()

    def seek_preview(self, value):
        if self.editor_timeline_active():
            self.editor_seek_global(
                float(value) / 1000.0,
                autoplay=(self.player.playbackState() == QMediaPlayer.PlayingState),
            )
            return
        self.player.setPosition(int(value))
        self.seek_live_audio_tracks(int(value))

    def return_to_live_source(self):
        if self.editor_timeline_active():
            global_sec = self.editor_current_global_second()
            was_playing = self.player.playbackState() == QMediaPlayer.PlayingState
            # Force return from flattened proxy to editable source clips while
            # preserving the exact global timeline position.
            index, source_second, _ = editor_engine.locate_time(
                self.editor_clips, global_sec
            )
            if index >= 0:
                self.preview_is_processed = False
                self.editor_selected_clip = index
                self.editor_clip_selected(index, seek=False)
                self.editor_update_master_timeline_ui(global_sec)
                self.editor_seek_clip(
                    index, source_second, autoplay=was_playing
                )
            self.refresh_live_audio_sources()
            self.preview_state.setText("⚡ Live Timeline")
            return

        source = self.current_video() or self.project.video_path
        if not source or not Path(source).exists():
            return
        pos = int(self.player.position())
        was_playing = self.player.playbackState() == QMediaPlayer.PlayingState
        self.preview_pending_position = pos
        self.preview_is_processed = False
        self.load_preview_media(source, autoplay=was_playing)
        self.refresh_live_audio_sources()
        self.update_live_overlay_state()
        self.preview_state.setText("⚡ Live Preview")


    def preview_button_action(self):
        """Background render never replaces the playing source automatically.

        Clicking only does one of two explicit actions:
        - if a cached final-look preview is ready: open it manually;
        - otherwise: request a background render.
        """
        if self.preview_pending_path and Path(self.preview_pending_path).exists():
            answer = QMessageBox.question(
                self,
                "Bản render",
                "Bản render thật đã sẵn sàng. Mở bản này để kiểm tra chính xác hiệu ứng?\n\n"
                "Live Preview hiện tại sẽ không tự đổi nếu bạn chọn No.",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer == QMessageBox.Yes:
                self.apply_pending_preview(autoplay=self.player.playbackState() == QMediaPlayer.PlayingState)
        else:
            self.refresh_processed_preview(background=True)


    def apply_pending_preview(self, autoplay=False):
        path = self.preview_pending_path
        if not path or not Path(path).exists():
            return

        old_position = int(self.player.position())
        was_playing = (
            self.player.playbackState() == QMediaPlayer.PlayingState
            or bool(autoplay)
        )

        self.processed_preview_path = path
        self.project.processed_preview_path = path
        self.preview_pending_path = ""
        self.preview_is_processed = True
        self.pause_live_audio_tracks()
        self.update_live_audio_mix()

        self.update_preview_btn.setText("↻ Render cache ngầm")
        self.preview_state.setText("Đang áp dụng Preview...")

        # Keep where the editor was looking instead of jumping to 00:00.
        self.preview_pending_position = old_position
        self.preview_should_autoplay = was_playing
        self.load_preview_media(path, autoplay=was_playing)

    def _after_media_loaded_restore_position(self):
        if self.preview_pending_position > 0:
            pos = self.preview_pending_position
            self.preview_pending_position = 0
            self.player.setPosition(pos)

    def show_preview_still_immediately(self, path: str):
        """Paint a real video frame before QMediaPlayer is asked to Play."""
        if not hasattr(self, "live_overlay"):
            return
        try:
            source = Path(path)
            key = hashlib.sha1(
                (str(source.resolve()) + f"|{source.stat().st_mtime_ns}").encode(
                    "utf-8",
                    errors="ignore",
                )
            ).hexdigest()[:20]
            still_dir = ROOT / "preview_cache" / "stills"
            still_path = still_dir / f"{key}.jpg"

            ffm.extract_preview_still(
                str(source),
                str(still_path),
                at_seconds=0.05,
                width=960,
            )
            image = QImage(str(still_path))
            if not image.isNull():
                self.live_overlay.set_video_image(image)
                self.preview_state.setText("Source Preview — Ready")
        except Exception:
            # Qt player may still supply a frame later; do not interrupt user.
            self.log_line(
                "[PREVIEW STILL ERROR]\n" + traceback.format_exc()
            )

    def load_preview_media(self, path: str, autoplay: bool = False):
        """Hard reload a local media file.

        Qt Multimedia on Windows may cache a file if the same URL is reused.
        We explicitly stop + clear the source before loading the new proxy.
        """
        if not path or not Path(path).exists():
            self.preview_state.setText("Preview file không tồn tại")
            return

        self.preview_loaded_path = str(Path(path).resolve())
        self.preview_should_autoplay = bool(autoplay)

        # Show a cached/extracted still immediately. This means selecting a
        # video is enough to see it; Play is only for motion/audio.
        self.show_preview_still_immediately(path)

        self.player.stop()
        self.player.setSource(QUrl())
        # Keep timeline UI at its current position while the new media loads.
        self.preview_state.setText("Đang nạp Preview...")

        # Give the backend one event-loop cycle after clearing the old file handle.
        QTimer.singleShot(
            80,
            lambda p=str(Path(path).resolve()): self.player.setSource(
                QUrl.fromLocalFile(p)
            )
        )

    def on_preview_media_status(self, status):
        if status == QMediaPlayer.LoadingMedia:
            self.preview_state.setText("Đang nạp...")
        elif status == QMediaPlayer.LoadedMedia:
            self.preview_state.setText(
                "✓ Processed Preview" if self.preview_is_processed else "Source Preview"
            )
            self._after_media_loaded_restore_position()
            if not self.preview_should_autoplay and self.player.position() <= 0:
                QTimer.singleShot(40, lambda: self.player.setPosition(1))
            if self.preview_should_autoplay:
                self.preview_should_autoplay = False
                QTimer.singleShot(60, self.player.play)
        elif status == QMediaPlayer.BufferedMedia:
            self._after_media_loaded_restore_position()
            if self.preview_should_autoplay:
                self.preview_should_autoplay = False
                QTimer.singleShot(30, self.player.play)
        elif status == QMediaPlayer.EndOfMedia:
            self.preview_state.setText("Stopped")
        elif status == QMediaPlayer.InvalidMedia:
            self.preview_should_autoplay = False
            self.preview_state.setText("Preview lỗi codec/media")

    def on_preview_player_error(self, error, error_string=""):
        if error == QMediaPlayer.NoError:
            return
        msg = error_string or self.player.errorString() or str(error)
        self.preview_state.setText("Preview Player Error")
        self.status(f"Qt Player không mở được preview: {msg}")
        # Do not show a modal every time an auto-preview happens.
        self.log_line(f"[PREVIEW PLAYER ERROR] {msg}")

    def toggle_preview_sub(self):
        self.preview_sub_hidden = not self.preview_sub_hidden
        self.hide_sub_btn.setText("Show Sub" if self.preview_sub_hidden else "Hide Sub")
        self.update_preview_subtitle(self.player.position() / 1000)
        self.update_live_overlay_state()

    def preview_source_volume_changed(self, value):
        self.update_live_audio_mix()
        self.update_audio_control_labels()
        self.update_live_overlay_state()
        self.refresh_live_audio_sources()

    def update_audio_control_labels(self, *args):
        self.source_volume_label.setText(f"Âm gốc: {self.source_volume.value()}%")
        self.narration_volume_label.setText(f"Giọng đọc: {self.narration_volume.value()}%")
        self.music_volume_label.setText(f"Nhạc nền: {self.music_volume.value()}%")
        self.update_live_audio_mix()

    def preview_source_volume_changed_no_recurse(self):
        self.update_live_audio_mix()


    def choose_output_dir(self):
        path = QFileDialog.getExistingDirectory(
            self, "Thư mục xuất", self.output_dir.text().strip() or str(ROOT / "exports")
        )
        if path:
            self.output_dir.setText(path)
            self.settings.data["output_dir"] = path
            self.settings.save()

    # ==================================================================
    # BLUR / LOGO / OVERLAY
    # ==================================================================
    def format_blur_zone(self, zone, number):
        prefix = "AUTO SUB" if zone.get("auto") else f"Vùng {number}"
        return (
            f"{prefix}: X{float(zone.get('x',0)):.1f}% Y{float(zone.get('y',0)):.1f}% "
            f"W{float(zone.get('w',100)):.1f}% H{float(zone.get('h',20)):.1f}%"
        )

    def _find_auto_blur_row(self):
        for row in range(self.blur_zone_list.count()):
            zone = dict(self.blur_zone_list.item(row).data(Qt.UserRole) or {})
            if zone.get("auto"):
                return row
        return -1

    def ensure_auto_sub_zone(self, zone=None, center=True):
        row = self._find_auto_blur_row()
        value = dict(zone or {"x": 8.0, "y": 71.0, "w": 84.0, "h": 11.0, "auto": True})
        value["auto"] = True

        w = max(30.0, min(94.0, float(value.get("w", 84.0))))
        h = max(5.0, min(20.0, float(value.get("h", 11.0))))
        y = max(42.0, min(96.0 - h, float(value.get("y", 71.0))))
        x = (100.0 - w) / 2.0 if center else max(
            0.0, min(100.0 - w, float(value.get("x", (100.0 - w) / 2.0)))
        )
        value.update({"x": x, "y": y, "w": w, "h": h})

        if row < 0:
            item = QListWidgetItem()
            item.setData(Qt.UserRole, value)
            self.blur_zone_list.insertItem(0, item)
            row = 0
        else:
            self.blur_zone_list.item(row).setData(Qt.UserRole, value)

        self.refresh_blur_zone_labels()
        return row

    def on_auto_sub_toggle(self, checked):
        try:
            if self._restoring_state:
                return
            if checked:
                self.blur_enabled.setChecked(True)
                row = self.ensure_auto_sub_zone(center=True)
                self.blur_zone_list.setCurrentRow(row)
                self.sync_sub_layout_to_auto_blur(update_cues=False)
                self.auto_sub_status.setText("Auto Sub: đang dò...")
                # Dò tự động nếu có video; kết quả vẫn có thể kéo sửa bằng chuột.
                QTimer.singleShot(80, self.detect_source_subtitle_zone)
            else:
                self.auto_sub_status.setText("Auto Sub: TẮT")
            self.update_live_overlay_state()
            self.schedule_processed_preview()
        except Exception:
            self.log_line("[AUTO SUB TOGGLE ERROR]\n" + traceback.format_exc())

    def detect_source_subtitle_zone(self):
        source = self.current_video() or self.project.video_path
        if not source or not Path(source).exists():
            self.auto_sub_status.setText("Auto Sub: chưa chọn video")
            return
        if self.auto_detect_worker and self.auto_detect_worker.isRunning():
            return

        self.auto_cover_source_sub.setChecked(True)
        self.blur_enabled.setChecked(True)
        self.auto_sub_status.setText("Auto Sub: đang phân tích local...")
        self.auto_sub_detect_btn.setEnabled(False)

        def job(progress, log):
            return subtitle_detector.detect_source_subtitle_zone(source, samples=7)

        worker = Worker(job)
        self.auto_detect_worker = worker
        self._retain_worker(worker)

        def done(zone):
            try:
                row = self.ensure_auto_sub_zone(zone, center=True)
                self.blur_zone_list.setCurrentRow(row)
                self.sync_sub_layout_to_auto_blur(update_cues=True)
                self.auto_sub_status.setText(
                    f"Auto Sub: {zone.get('w',0):.0f}% × {zone.get('h',0):.0f}% — kéo để chỉnh"
                )
                self.update_live_overlay_state()
                self.schedule_processed_preview()
                self.schedule_autosave()
            except Exception:
                self.log_line("[AUTO SUB RESULT ERROR]\n" + traceback.format_exc())

        def err(tb):
            self.log_line("[AUTO SUB DETECT ERROR]\n" + tb[-3500:])
            row = self.ensure_auto_sub_zone()
            self.blur_zone_list.setCurrentRow(row)
            self.auto_sub_status.setText("Auto Sub: dùng vùng mặc định — kéo để chỉnh")
            self.update_live_overlay_state()

        def enable_button():
            self.auto_sub_detect_btn.setEnabled(True)

        worker.done.connect(done)
        worker.error.connect(err)
        worker.finished.connect(enable_button)
        worker.start()

    def add_blur_zone(self, zone=None):
        """Add a MANUAL region.

        QPushButton.clicked emits a bool. Older builds accidentally consumed
        that bool as `zone`, causing: AttributeError: 'bool' object has no
        attribute 'get'. Accept/ignore it defensively here as well.
        """
        if isinstance(zone, bool):
            zone = None
        if zone is None:
            zone = {"x": 68.0, "y": 8.0, "w": 26.0, "h": 14.0, "auto": False}

        try:
            value = {
                "x": float(zone.get("x", 68.0)),
                "y": float(zone.get("y", 8.0)),
                "w": float(zone.get("w", 26.0)),
                "h": float(zone.get("h", 14.0)),
                "auto": bool(zone.get("auto", False)),
            }
            value["x"] = max(0.0, min(97.0, value["x"]))
            value["y"] = max(0.0, min(97.0, value["y"]))
            value["w"] = max(3.0, min(100.0 - value["x"], value["w"]))
            value["h"] = max(3.0, min(100.0 - value["y"], value["h"]))

            item = QListWidgetItem()
            item.setData(Qt.UserRole, value)
            self.blur_zone_list.addItem(item)

            self.blur_enabled.blockSignals(True)
            self.blur_enabled.setChecked(True)
            self.blur_enabled.blockSignals(False)

            self.refresh_blur_zone_labels()
            row = self.blur_zone_list.count() - 1
            self.blur_zone_list.blockSignals(True)
            self.blur_zone_list.setCurrentRow(row)
            self.blur_zone_list.blockSignals(False)
            self.load_selected_blur_params(row)

            QTimer.singleShot(0, self._after_manual_blur_added)

        except Exception:
            tb = traceback.format_exc()
            self.log_line("[ADD BLUR ERROR]\n" + tb)
            QMessageBox.critical(
                self,
                "Blur Zone",
                "Không thể thêm vùng che. Ứng dụng vẫn tiếp tục chạy.\n\n" + tb[-1200:],
            )

    def _after_manual_blur_added(self):
        for name, fn in (
            ("LIVE", self.update_live_overlay_state),
            ("CACHE", self.schedule_processed_preview),
            ("AUTOSAVE", self.schedule_autosave),
        ):
            try:
                fn()
            except Exception:
                self.log_line(f"[BLUR {name} ERROR]\n" + traceback.format_exc())
        self._refresh_professional_panels()


    def edit_blur_zone(self):
        item = self.blur_zone_list.currentItem()
        if not item:
            return
        current = dict(item.data(Qt.UserRole) or {})
        dlg = BlurZoneDialog(self, current)
        if dlg.exec() == QDialog.Accepted:
            updated = dlg.result_zone()
            updated["auto"] = bool(current.get("auto"))
            item.setData(Qt.UserRole, updated)
            self.blur_enabled.setChecked(True)
            self.refresh_blur_zone_labels()
            self.update_live_overlay_state()
            self.schedule_processed_preview()
            self.schedule_autosave()

    def remove_blur_zone(self):
        row = self.blur_zone_list.currentRow()
        if row < 0:
            return
        item = self.blur_zone_list.item(row)
        zone = dict(item.data(Qt.UserRole) or {})
        self.blur_zone_list.takeItem(row)
        if zone.get("auto"):
            self.auto_cover_source_sub.setChecked(False)
            self.auto_sub_status.setText("Auto Sub: TẮT")
        self.refresh_blur_zone_labels()
        self.update_live_overlay_state()
        self.schedule_processed_preview()
        self.schedule_autosave()

    def refresh_blur_zone_labels(self):
        manual_no = 0
        for i in range(self.blur_zone_list.count()):
            item = self.blur_zone_list.item(i)
            zone = dict(item.data(Qt.UserRole) or {})
            if not zone.get("auto"):
                manual_no += 1
                number = manual_no
            else:
                number = 0
            item.setText(self.format_blur_zone(zone, number))

    def blur_zones(self):
        """Manual regions only; auto subtitle mask has its own export field."""
        result = []
        for i in range(self.blur_zone_list.count()):
            zone = dict(self.blur_zone_list.item(i).data(Qt.UserRole) or {})
            if not zone.get("auto"):
                zone.pop("_list_row", None)
                result.append(zone)
        return result

    def auto_subtitle_zone(self):
        row = self._find_auto_blur_row()
        if row < 0:
            return {}
        zone = dict(self.blur_zone_list.item(row).data(Qt.UserRole) or {})
        zone.pop("_list_row", None)
        return zone

    def all_live_blur_zones(self):
        zones = []
        for row in range(self.blur_zone_list.count()):
            zone = dict(self.blur_zone_list.item(row).data(Qt.UserRole) or {})
            if zone.get("auto") and not self.auto_cover_source_sub.isChecked():
                continue
            zone["_list_row"] = row
            zones.append(zone)
        return zones

    def choose_logo(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn logo", "", "Image (*.png *.jpg *.jpeg *.webp)"
        )
        if path:
            self.logo_path.setText(path)
            self.logo_enabled.setChecked(True)
            self.logo_params_toggle.setChecked(True)
            self.update_live_overlay_state()
            self.schedule_processed_preview()
            self.schedule_autosave()

    def apply_logo_position_preset(self, name):
        presets = {
            "Top-right": (90, 10), "Top-left": (10, 10),
            "Bottom-right": (90, 90), "Bottom-left": (10, 90),
        }
        if name not in presets:
            return
        x, y = presets[name]
        self.logo_x.blockSignals(True); self.logo_y.blockSignals(True)
        self.logo_x.setValue(x); self.logo_y.setValue(y)
        self.logo_x.blockSignals(False); self.logo_y.blockSignals(False)
        self.update_live_overlay_state()
        self.schedule_processed_preview()

    def apply_overlay_position_preset(self, name):
        presets = {
            "Top-right": (88, 8), "Top-left": (12, 8),
            "Bottom-right": (88, 92), "Bottom-left": (12, 92),
        }
        if name not in presets:
            return
        x, y = presets[name]
        self.overlay_x.blockSignals(True); self.overlay_y.blockSignals(True)
        self.overlay_x.setValue(x); self.overlay_y.setValue(y)
        self.overlay_x.blockSignals(False); self.overlay_y.blockSignals(False)
        self.update_live_overlay_state()
        self.schedule_processed_preview()

    def pick_color(self, line_edit: QLineEdit):
        color = QColorDialog.getColor(
            QColor(line_edit.text().strip() or "#FFFFFF"), self, "Chọn màu"
        )
        if color.isValid():
            line_edit.setText(color.name().upper())
            self.update_live_overlay_state()
            self.update_subtitle_preview_style()

    # ==================================================================
    # LIVE EDITOR OVERLAY
    # ==================================================================
    def current_output_aspect(self):
        target = ffm.parse_resolution(self.resolution.currentText())
        if target:
            return target[0] / max(1, target[1])
        source = self.current_video() or self.project.video_path
        if source:
            key = str(source)
            if key in self._source_aspect_cache:
                return self._source_aspect_cache[key]
            try:
                info = ffm.probe(source)
                aspect = info["width"] / max(1, info["height"])
                self._source_aspect_cache[key] = aspect
                return aspect
            except Exception:
                pass
        return 9 / 16

    def update_live_overlay_state(self, *args):
        if not hasattr(self, "live_overlay"):
            return
        try:
            self.live_overlay.set_output_aspect(self.current_output_aspect())

            if self.preview_is_processed:
                self.live_overlay.set_blur_state(False, self.blur_style.currentText(), self.blur_opacity.value(), [])
                self.live_overlay.set_subtitle_state(False, "", self.current_subtitle_style())
                self.live_overlay.set_logo_state(False, "", 50, 50, 10, 100)
                self.live_overlay.set_overlay_text_state(False, "", 50, 50, "Arial", 30, "#FFFFFF")
                self.live_overlay.set_editor_layers([], 0.0)
                return

            self.live_overlay.set_blur_state(
                self.blur_enabled.isChecked(),
                self.blur_style.currentText(),
                self.blur_opacity.value(),
                self.all_live_blur_zones(),
            )

            text = ""
            second = (
                self.editor_current_time()
                if self.editor_timeline_active()
                else self.player.position() / 1000.0
            )
            cue_start = second
            cue_end = second
            if not self.preview_sub_hidden and self.sub_enabled.isChecked():
                text, cue_start, cue_end = self.preview_subtitle_state_at(second)

            self.live_overlay.set_subtitle_state(
                self.sub_enabled.isChecked() and not self.preview_sub_hidden,
                text,
                self.current_subtitle_style(),
                effect=self.sub_animation.currentText(),
                elapsed=max(0.0, second - cue_start),
                duration=max(0.01, cue_end - cue_start),
            )

            self.live_overlay.set_logo_state(
                self.logo_enabled.isChecked(), self.logo_path.text().strip(),
                self.logo_x.value(), self.logo_y.value(), self.logo_scale.value(),
                self.logo_opacity.value(),
            )
            self.live_overlay.set_overlay_text_state(
                self.overlay_enabled.isChecked(), self.overlay_text.text(),
                self.overlay_x.value(), self.overlay_y.value(),
                self.overlay_font.currentFont().family(), self.overlay_size.value(),
                self.overlay_color.text().strip() or "#FFFFFF",
            )
            self.live_overlay.set_editor_layers(
                self.editor_layers,
                self.editor_current_time()
                if hasattr(self, "editor_current_time")
                else second,
            )
        except Exception:
            self.log_line("[LIVE OVERLAY UPDATE ERROR]\n" + traceback.format_exc())

    def on_live_blur_zone_changed(self, index, zone):
        try:
            row = int(zone.get("_list_row", index))
            if not (0 <= row < self.blur_zone_list.count()):
                return
            clean = dict(zone)
            clean.pop("_list_row", None)
            # preserve auto/manual identity from UI item
            existing = dict(self.blur_zone_list.item(row).data(Qt.UserRole) or {})
            clean["auto"] = bool(existing.get("auto"))
            item = self.blur_zone_list.item(row)
            item.setData(Qt.UserRole, clean)
            self.refresh_blur_zone_labels()
            self.blur_zone_list.blockSignals(True)
            self.blur_zone_list.setCurrentRow(row)
            self.blur_zone_list.blockSignals(False)
            self.load_selected_blur_params(row)
            if clean.get("auto"):
                self.auto_sub_status.setText("Auto Sub: đã chỉnh bằng chuột")
                self.sync_sub_layout_to_auto_blur(update_cues=False)
        except Exception:
            self.log_line("[LIVE BLUR CHANGE ERROR]\n" + traceback.format_exc())

    def on_live_sub_geometry_changed(self, x, y, width, font_size):
        if hasattr(self, "sub_auto_layout") and self.sub_auto_layout.isChecked():
            self.sub_auto_layout.blockSignals(True)
            self.sub_auto_layout.setChecked(False)
            self.sub_auto_layout.blockSignals(False)
        widgets = [self.sub_x, self.sub_y, self.sub_width, self.sub_size]
        for w in widgets: w.blockSignals(True)
        self.sub_x.setValue(round(x)); self.sub_y.setValue(round(y))
        self.sub_width.setValue(round(width)); self.sub_size.setValue(round(font_size))
        for w in widgets: w.blockSignals(False)
        self.sub_max_chars.blockSignals(True)
        self.sub_max_chars.setValue(self._stable_sub_char_limit())
        self.sub_max_chars.blockSignals(False)
        self.update_live_overlay_state()

    def on_live_logo_geometry_changed(self, x, y, scale):
        for w in [self.logo_x, self.logo_y, self.logo_scale]: w.blockSignals(True)
        self.logo_x.setValue(x); self.logo_y.setValue(y); self.logo_scale.setValue(round(scale))
        for w in [self.logo_x, self.logo_y, self.logo_scale]: w.blockSignals(False)
        if self.logo_pos.findText("Custom") < 0: self.logo_pos.addItem("Custom")
        self.logo_pos.blockSignals(True); self.logo_pos.setCurrentText("Custom"); self.logo_pos.blockSignals(False)
        self.update_live_overlay_state()

    def on_live_text_geometry_changed(self, x, y, font_size):
        for w in [self.overlay_x, self.overlay_y, self.overlay_size]: w.blockSignals(True)
        self.overlay_x.setValue(x); self.overlay_y.setValue(y); self.overlay_size.setValue(round(font_size))
        for w in [self.overlay_x, self.overlay_y, self.overlay_size]: w.blockSignals(False)
        if self.overlay_pos.findText("Custom") < 0: self.overlay_pos.addItem("Custom")
        self.overlay_pos.blockSignals(True); self.overlay_pos.setCurrentText("Custom"); self.overlay_pos.blockSignals(False)
        self.update_live_overlay_state()

    def on_live_overlay_interaction_finished(self):
        if (
            hasattr(self, "live_overlay")
            and self.live_overlay.selected_type == "editor_layer"
        ):
            self.schedule_autosave()
            self.schedule_processed_preview()
            return

        if hasattr(self, "sub_auto_layout") and self.sub_auto_layout.isChecked():
            self.sync_sub_layout_to_auto_blur(update_cues=True)
        else:
            self.reflow_current_subtitle_for_layout()
        self.schedule_autosave()
        self.schedule_processed_preview()

    def on_live_overlay_selection_changed(self, kind, index):
        if kind == "blur" and index >= 0:
            self.editor_document.selection.select("blur", f"blur:{index}")
            self.editor_timeline.set_selected_item(f"blur:{index}")
            zones = self.all_live_blur_zones()
            if index < len(zones):
                row = int(zones[index].get("_list_row", index))
                self.blur_zone_list.setCurrentRow(row)
            self.blur_params_toggle.setChecked(True)
        elif kind == "sub":
            self.editor_document.selection.select("subtitle", "subtitle", self._current_subtitle_group_id())
            self.sub_params_toggle.setChecked(True)
        elif kind == "logo":
            self.editor_document.selection.select("logo", "primary-logo")
            self.context_inspector.load_properties("logo", {"x": self.logo_x.value(), "y": self.logo_y.value(), "scale": self.logo_scale.value(), "opacity": self.logo_opacity.value()})
            self.logo_params_toggle.setChecked(True)
        elif kind == "text":
            self.editor_document.selection.select("text", "primary-overlay-text")
            self.context_inspector.load_properties("text", {"text": self.overlay_text.text(), "font_name": self.overlay_font.currentFont().family(), "font_size": self.overlay_size.value(), "x": self.overlay_x.value(), "y": self.overlay_y.value(), "opacity": 100})
            self.overlay_params_toggle.setChecked(True)
        elif kind == "editor_layer" and 0 <= index < len(self.editor_layers):
            layer = self.editor_layers[index]
            selection_kind = "image" if layer.get("type") == "image" else "text"
            self.editor_document.selection.select(selection_kind, str(layer.get("id", "")), str(layer.get("group_id", "")))
            self.editor_timeline.set_selected_item(str(layer.get("id", "")))
            self.context_inspector.load_properties(selection_kind, layer)

    def toggle_blur_params(self, checked):
        self.blur_params_panel.setVisible(checked)
        self.blur_params_toggle.setText("▾ Ẩn thông số vùng" if checked else "▸ Thông số vùng")

    def toggle_sub_params(self, checked):
        self.sub_style_details.setVisible(checked)
        self.sub_params_toggle.setText("▾ Ẩn thông số phụ đề" if checked else "▸ Thông số phụ đề")

    def toggle_logo_params(self, checked):
        self.logo_params_panel.setVisible(checked)
        self.logo_params_toggle.setText("▾ Ẩn thông số Logo" if checked else "▸ Thông số Logo")

    def toggle_overlay_params(self, checked):
        self.overlay_params_panel.setVisible(checked)
        self.overlay_params_toggle.setText("▾ Ẩn thông số Chữ phủ" if checked else "▸ Thông số Chữ phủ")

    def load_selected_blur_params(self, row):
        if not (0 <= row < self.blur_zone_list.count()): return
        zone = dict(self.blur_zone_list.item(row).data(Qt.UserRole) or {})
        for widget in [self.blur_x_param, self.blur_y_param, self.blur_w_param, self.blur_h_param]: widget.blockSignals(True)
        self.blur_x_param.setValue(float(zone.get("x",0))); self.blur_y_param.setValue(float(zone.get("y",0)))
        self.blur_w_param.setValue(float(zone.get("w",100))); self.blur_h_param.setValue(float(zone.get("h",20)))
        for widget in [self.blur_x_param, self.blur_y_param, self.blur_w_param, self.blur_h_param]: widget.blockSignals(False)

    def blur_params_changed(self, *args):
        row = self.blur_zone_list.currentRow()
        if not (0 <= row < self.blur_zone_list.count()): return
        existing = dict(self.blur_zone_list.item(row).data(Qt.UserRole) or {})
        zone = {"x":self.blur_x_param.value(),"y":self.blur_y_param.value(),"w":self.blur_w_param.value(),"h":self.blur_h_param.value(),"auto":bool(existing.get("auto"))}
        zone["w"] = max(3,min(zone["w"],100-zone["x"])); zone["h"] = max(3,min(zone["h"],100-zone["y"]))
        self.blur_zone_list.item(row).setData(Qt.UserRole,zone)
        self.refresh_blur_zone_labels(); self.update_live_overlay_state(); self.schedule_processed_preview(); self.schedule_autosave()

    # ==================================================================
    # TTS ENGINE / PIPER VOICE MANAGER
    # ==================================================================
    def on_tts_engine_changed(self, *args):
        engine = self.tts_engine.currentText()
        previous = self.tts_voice.currentText().strip()

        if "Piper" in engine:
            voices = piper_engine.installed_voices(ROOT)
            # Keep a useful catalog starter even before online refresh.
            for voice in piper_engine.FEATURED_VOICES:
                if voice not in voices:
                    voices.append(voice)
            if previous and previous.startswith(("en_", "vi_", "zh_", "de_", "fr_", "es_", "pt_", "pl_", "ru_")):
                if previous not in voices:
                    voices.insert(0, previous)
            if not voices:
                voices = ["en_US-lessac-medium"]

            self._replace_tts_voice_items(
                voices,
                preferred=previous if previous in voices else "en_US-lessac-medium",
            )
            self.tts_voice_manager.setText("Voice Manager")
            self.tts_voice_manager.setEnabled(True)

        elif "Gemini" in engine:
            voices = ["Kore", "Puck", "Charon", "Fenrir", "Aoede"]
            self._replace_tts_voice_items(
                voices,
                preferred=previous if previous in voices else "Puck",
            )
            self.tts_voice_manager.setText("Gemini voices")
            self.tts_voice_manager.setEnabled(False)

        elif "Edge" in engine:
            voices = [
                "en-US-JennyNeural",
                "en-US-GuyNeural",
                "en-US-AriaNeural",
                "en-US-DavisNeural",
                "vi-VN-HoaiMyNeural",
                "vi-VN-NamMinhNeural",
            ]
            self._replace_tts_voice_items(
                voices,
                preferred=previous if previous in voices else "en-US-JennyNeural",
            )
            self.tts_voice_manager.setText("Edge voices")
            self.tts_voice_manager.setEnabled(False)

        else:
            # Windows SAPI: editable because installed voice names differ per PC.
            self._replace_tts_voice_items(
                [previous] if previous else [""],
                preferred=previous,
            )
            self.tts_voice_manager.setText("SAPI")
            self.tts_voice_manager.setEnabled(False)

        is_piper = "Piper" in engine
        self.piper_download_voice.setVisible(is_piper)
        self.piper_try_voice.setVisible(is_piper)
        self.piper_status.setVisible(is_piper)

        is_gemini = "Gemini" in engine
        self.tts_auto_fallback.setVisible(is_gemini)
        self.tts_fallback_voice.setVisible(is_gemini)

        self.refresh_piper_status()

    def _replace_tts_voice_items(self, items, preferred=""):
        self.tts_voice.blockSignals(True)
        self.tts_voice.clear()
        for item in items:
            if item and self.tts_voice.findText(item) < 0:
                self.tts_voice.addItem(item)
        if preferred:
            self.tts_voice.setCurrentText(preferred)
        elif self.tts_voice.count():
            self.tts_voice.setCurrentIndex(0)
        self.tts_voice.blockSignals(False)

    def refresh_piper_status(self):
        if "Piper" not in self.tts_engine.currentText():
            return
        voice_id = self.tts_voice.currentText().strip()
        if not voice_id:
            self.piper_status.setText("Chưa chọn voice")
            return

        if not piper_engine.piper_installed():
            self.piper_status.setText("⚠ Chưa cài piper-tts")
            self.piper_download_voice.setText("Cài Piper trước")
            self.piper_download_voice.setEnabled(False)
            self.piper_try_voice.setEnabled(False)
            return

        self.piper_download_voice.setEnabled(True)
        installed = piper_engine.is_voice_installed(
            ROOT,
            voice_id,
        )
        if installed:
            model, _ = piper_engine.voice_paths(ROOT, voice_id)
            self.piper_status.setText(
                "✓ Offline " + piper_engine.human_size(
                    model.stat().st_size
                )
            )
            self.piper_download_voice.setText("✓ Đã tải")
            self.piper_download_voice.setEnabled(False)
            self.piper_try_voice.setEnabled(True)
        else:
            self.piper_status.setText("Chưa tải — tải 1 lần rồi dùng offline")
            self.piper_download_voice.setText("⬇ Tải voice")
            self.piper_download_voice.setEnabled(True)
            self.piper_try_voice.setEnabled(False)

    def open_tts_voice_manager(self):
        if "Piper" not in self.tts_engine.currentText():
            return

        dialog = PiperVoiceDialog(
            self,
            current_voice=self.tts_voice.currentText().strip(),
        )
        if dialog.exec() == QDialog.Accepted:
            voice_id = dialog.selected_voice
            current_items = [
                self.tts_voice.itemText(i)
                for i in range(self.tts_voice.count())
            ]
            if voice_id not in current_items:
                self.tts_voice.addItem(voice_id)
            self.tts_voice.setCurrentText(voice_id)
            self.refresh_piper_status()

    def download_current_piper_voice(self):
        if "Piper" not in self.tts_engine.currentText():
            return
        voice_id = self.tts_voice.currentText().strip()
        if not voice_id:
            return

        def job(progress, log):
            return piper_engine.download_voice(
                ROOT,
                voice_id,
                log=log,
            )

        def done(_voice_id):
            self.refresh_piper_status()
            self.status(
                f"Piper voice đã sẵn sàng offline: {voice_id}"
            )

        self.run_worker(
            f"Đang tải Piper voice {voice_id}...",
            job,
            done,
        )

    def preview_piper_voice(self, voice_id, dialog_parent=None):
        voice_id = (voice_id or "").strip()
        if not voice_id:
            return
        if not piper_engine.is_voice_installed(ROOT, voice_id):
            QMessageBox.information(
                dialog_parent or self,
                "Piper",
                "Voice này chưa tải. Bấm Tải voice trước.",
            )
            return

        preview_dir = ROOT / "piper_voices" / "_preview"
        preview_dir.mkdir(parents=True, exist_ok=True)
        target = preview_dir / f"{voice_id}_preview.wav"
        sample = (
            "This incredible machine is changing the way heavy industry works."
        )

        def job(progress, log):
            return piper_engine.synthesize(
                ROOT,
                voice_id,
                sample,
                str(target),
                speed=self.tts_speed.value(),
                log=log,
            )

        def done(path):
            self.status(f"Piper preview: {voice_id}")
            try:
                if os.name == "nt":
                    os.startfile(path)
                else:
                    QDesktopServices.openUrl(
                        QUrl.fromLocalFile(path)
                    )
            except Exception:
                QDesktopServices.openUrl(
                    QUrl.fromLocalFile(path)
                )

        self.run_worker(
            f"Đang tạo preview Piper {voice_id}...",
            job,
            done,
        )

    # ==================================================================
    # TTS NOW LIVES IN VIDEO EXPORTER
    # ==================================================================
    def choose_voice_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn file giọng", "", "Audio (*.wav *.mp3 *.m4a *.aac *.flac *.ogg)"
        )
        if path:
            self.voice_file.setText(path)
            self.narration_path = path
            self.project.narration_path = path
            self.refresh_live_audio_sources()
            self.schedule_autosave()

    def choose_music_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn nhạc nền", "", "Audio (*.wav *.mp3 *.m4a *.aac *.flac *.ogg)"
        )
        if path:
            self.music_file.setText(path)
            self.refresh_live_audio_sources()
            self.schedule_processed_preview()

    def export_generate_voice(self):
        self.sync_scene_table()
        script_scenes = [
            s for s in self.project.scenes if (s.en_voice or "").strip()
        ]
        if not script_scenes:
            QMessageBox.warning(
                self,
                "Lồng Tiếng",
                "Chưa có kịch bản từ AI Studio.\nHãy chạy AI Studio trước.",
            )
            return

        try:
            workspace = self.ai_workspace()
        except Exception as e:
            QMessageBox.warning(self, "Lồng Tiếng", str(e))
            return

        selected_engine = self.tts_engine.currentText()
        selected_voice = self.tts_voice.currentText().strip()
        speed = self.tts_speed.value()
        google_tts_key = self.tts_api_key.text().strip()
        gemini_model = self.tts_model.currentText().strip()
        direction = self.voice_style.toPlainText().strip()

        if "Piper" in selected_engine:
            if not piper_engine.piper_installed():
                QMessageBox.warning(
                    self,
                    "Piper TTS",
                    "Chưa cài piper-tts. Hãy chạy install_piper.bat "
                    "hoặc chạy lại install.bat.",
                )
                return
            if not selected_voice:
                selected_voice = "en_US-lessac-medium"

        auto_fallback = self.tts_auto_fallback.isChecked()
        fallback_voice = (
            self.tts_fallback_voice.currentText().strip()
            or "en-US-JennyNeural"
        )

        voice_dir = workspace / "voice_scenes"
        voice_dir.mkdir(parents=True, exist_ok=True)

        if (
            "Gemini" in selected_engine
            and selected_voice
            not in {"Kore", "Puck", "Charon", "Fenrir", "Aoede"}
        ):
            selected_voice = self.voice.currentText().strip() or "Kore"

        if "Gemini" in selected_engine and not google_tts_key:
            if auto_fallback:
                self.voice_status.setText(
                    "Google TTS key trống → sẽ dùng Edge TTS fallback."
                )
            else:
                QMessageBox.warning(
                    self,
                    "Lồng Tiếng",
                    "Gemini TTS cần Google TTS API Key trong Settings.\n"
                    "Hoặc bật 'Gemini lỗi → tự chuyển Edge TTS'.",
                )
                return

        def job(progress, log):
            chunks = []
            total = len(script_scenes)

            active_engine = selected_engine
            active_voice = selected_voice
            fallback_used = False
            fallback_reason = ""

            # If Gemini selected but no key exists, start Edge immediately.
            if "Gemini" in active_engine and not google_tts_key and auto_fallback:
                active_engine = "Edge TTS"
                active_voice = fallback_voice
                fallback_used = True
                fallback_reason = "Google TTS API key trống"
                log(
                    "[TTS FALLBACK] Gemini TTS không có Google key "
                    f"→ Edge TTS ({active_voice})"
                )

            log(
                f"[TTS] Selected engine={selected_engine} | "
                f"voice={selected_voice} | scenes={total}"
            )
            log(
                f"[TTS] Auto fallback={'ON' if auto_fallback else 'OFF'} | "
                f"Edge voice={fallback_voice}"
            )

            if "Piper" in active_engine:
                if not piper_engine.is_voice_installed(
                    ROOT,
                    active_voice,
                ):
                    log(
                        f"[PIPER] Voice chưa có offline. "
                        f"Tự tải 1 lần: {active_voice}"
                    )
                    piper_engine.download_voice(
                        ROOT,
                        active_voice,
                        log=log,
                    )
                log(
                    f"[PIPER] Dùng model cache cho toàn bộ {total} scene: "
                    f"{active_voice}"
                )

            for i, scene in enumerate(script_scenes):
                text = scene.en_voice.strip()

                # Extension follows the ACTUAL engine for each scene.
                ext = ".mp3" if "Edge" in active_engine else ".wav"
                out = voice_dir / f"scene_{scene.index:03d}{ext}"

                try:
                    log(
                        f"[TTS] Scene {i + 1}/{total} | "
                        f"engine={active_engine} | voice={active_voice}"
                    )

                    tts_engine.generate_tts(
                        engine=active_engine,
                        text=text,
                        out_path=str(out),
                        speed=speed,
                        voice=active_voice,
                        api_key=google_tts_key,
                        gemini_model=gemini_model,
                        direction=direction,
                        piper_root=str(ROOT),
                        log=log,
                    )

                except Exception as exc:
                    # Only auto-fallback Gemini quota/rate failures.
                    if (
                        "Gemini" in active_engine
                        and auto_fallback
                        and tts_engine.is_gemini_quota_error(exc)
                    ):
                        fallback_used = True
                        fallback_reason = str(exc)

                        log(
                            "[TTS FALLBACK] Gemini TTS lỗi quota/rate-limit:"
                        )
                        log(f"[TTS FALLBACK] {exc}")
                        log(
                            f"[TTS FALLBACK] Chuyển scene hiện tại + phần còn lại "
                            f"sang Edge TTS ({fallback_voice})."
                        )

                        active_engine = "Edge TTS"
                        active_voice = fallback_voice

                        # Recreate current scene with correct extension.
                        out = voice_dir / f"scene_{scene.index:03d}.mp3"
                        try:
                            out.unlink(missing_ok=True)
                        except Exception:
                            pass

                        tts_engine.generate_tts(
                            engine=active_engine,
                            text=text,
                            out_path=str(out),
                            speed=speed,
                            voice=active_voice,
                            piper_root=str(ROOT),
                            log=log,
                        )
                    else:
                        raise

                chunks.append({
                    "scene_index": scene.index,
                    "start": scene.start,
                    "scene_end": scene.end,
                    "path": str(out),
                    "en_text": text,
                    "vi_text": scene.vi_voice.strip(),
                    "tts_engine": active_engine,
                    "tts_voice": active_voice,
                })
                progress(i + 1, total)

            timeline = workspace / "narration_synced.m4a"
            manifest = ffm.build_scene_timeline_audio(
                chunks,
                str(timeline),
                total_duration=(
                    self.project.duration
                    or ffm.probe(self.project.video_path)["duration"]
                ),
            )

            # Keep TTS engine metadata after timeline builder.
            chunk_by_index = {
                int(x["scene_index"]): x
                for x in chunks
            }
            for item in manifest:
                source = chunk_by_index.get(
                    int(item.get("scene_index", -1))
                )
                if source:
                    item["tts_engine"] = source.get("tts_engine", "")
                    item["tts_voice"] = source.get("tts_voice", "")

            manifest_path = workspace / "voice_manifest.json"
            manifest_path.write_text(
                json.dumps(
                    manifest,
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )

            return {
                "timeline": str(timeline),
                "manifest_path": str(manifest_path),
                "manifest": manifest,
                "fallback_used": fallback_used,
                "fallback_reason": fallback_reason,
                "final_engine": active_engine,
                "final_voice": active_voice,
            }

        def done(result):
            path = result["timeline"]
            manifest_path = result["manifest_path"]
            manifest = result["manifest"]

            self.narration_path = path
            self.voice_file.setText(path)
            self.project.narration_path = path
            self.project.voice_manifest_path = manifest_path

            by_index = {
                int(x.get("scene_index")): x
                for x in manifest
            }
            for scene in self.project.scenes:
                item = by_index.get(scene.index)
                if item:
                    scene.voice_start = float(
                        item.get("start", scene.start)
                    )
                    scene.voice_end = float(
                        item.get("end", scene.end)
                    )
                    scene.voice_file = str(
                        item.get("path", "")
                    )

            self.mute_original_voice.setChecked(True)
            self.narration_volume.setValue(100)

            synced_srt = workspace / "subtitle_synced_en.srt"
            ffm.write_srt_from_voice_manifest(
                manifest,
                str(synced_srt),
                "en",
                hide_on_voice_pause=self.sub_hide_on_voice_pause.isChecked(),
                pause_ms=self.sub_pause_gap_ms.value(),
                word_by_word=(
                    self.sub_animation.currentText() == "Word Pop Sync"
                ),
            )
            self.project.subtitle_path = str(synced_srt)

            if result["fallback_used"]:
                self.voice_status.setText(
                    "✓ Voice hoàn tất bằng Edge fallback — "
                    f"{result['final_voice']}"
                )
                self.status(
                    "Gemini TTS bị quota/rate-limit nên app đã tự chuyển "
                    "sang Edge TTS và vẫn hoàn tất voice + timeline + subtitle."
                )
            else:
                self.voice_status.setText(
                    f"✓ Voice đã ghép vào timeline: {Path(path).name}"
                )
                self.status(
                    "Đã tạo voice. Live Preview đã đồng bộ giọng đọc mà "
                    "không reload video; render cache đang chạy ngầm."
                )

            self.script_ready_label.setText(
                f"Voice: {len(manifest)} đoạn — SUB CÓ TIMELINE THẬT"
            )

            self.autosave_project()
            self.refresh_live_audio_sources()
            self.schedule_processed_preview()

        self.run_worker(
            f"{selected_engine} đang tạo voice theo từng timeline...",
            job,
            done,
        )


    def separate_original_vocals(self):
        src = self.current_video() or self.project.video_path
        if not src:
            QMessageBox.warning(self, "Tách giọng", "Chưa chọn video.")
            return

        out_dir = self.project_workspace_for(src) / "demucs"

        def job(progress, log):
            return vocal_separator.separate_vocals(
                src, str(out_dir), log=log, process_holder=self.process_holder
            )

        def done(result):
            self.accompaniment_path = result.get("accompaniment", "")
            self.vocals_path = result.get("vocals", "")
            self.voice_status.setText("✓ Đã tách giọng gốc; có thể bật 'Tắt giọng gốc'.")
            self.refresh_live_audio_sources()
            self.schedule_autosave()

        self.run_worker("Đang tách giọng gốc bằng Demucs...", job, done)

    # ==================================================================
    # SUBTITLE / TRANSLATION
    # ==================================================================
    def _output_dimensions_for_layout(self):
        target = ffm.parse_resolution(self.resolution.currentText())
        if target:
            return target
        source = self.current_video() or self.project.video_path
        if source:
            try:
                info = ffm.probe(source)
                return max(2, info.get("width") or 1080), max(2, info.get("height") or 1920)
            except Exception:
                pass
        return 1080, 1920

    def _subtitle_pixel_metrics(self):
        font = QFont(self.sub_font.currentFont().family())
        font.setPixelSize(max(12, int(self.sub_size.value())))
        font.setBold(self.sub_bold.isChecked())
        font.setItalic(self.sub_italic.isChecked())
        return QFontMetricsF(font)

    def _subtitle_available_pixel_width(self):
        out_w, _ = self._output_dimensions_for_layout()
        width_px = float(out_w) * max(0.20, min(0.96, self.sub_width.value() / 100.0))

        # Reserve room for outline/shadow and a small visual safety margin.
        outline_px = max(0.0, float(self.sub_outline.value()))
        safety = max(26.0, outline_px * 8.0 + width_px * 0.035)
        return max(90.0, width_px - safety)

    def _split_subtitle_text_pixel_safe(self, text: str):
        """Split a caption using actual Qt font pixel widths.

        Font size stays FIXED. If text is too wide, the sentence becomes more
        timed cues instead of shrinking/cropping the font.
        """
        clean = re.sub(r"<[^>]+>", "", str(text or ""))
        clean = " ".join(clean.replace("\\n", " ").replace(r"\\N", " ").split())
        if self.sub_uppercase.isChecked():
            clean = clean.upper()
        if not clean:
            return []

        metrics = self._subtitle_pixel_metrics()
        available = self._subtitle_available_pixel_width() * 0.94

        if metrics.horizontalAdvance(clean) <= available:
            return [clean]

        words = clean.split()
        chunks = []
        current = ""

        for word in words:
            candidate = word if not current else current + " " + word
            if metrics.horizontalAdvance(candidate) <= available:
                current = candidate
                continue

            if current:
                chunks.append(current)
                current = ""

            # A single token can itself be too wide: split by characters.
            if metrics.horizontalAdvance(word) > available:
                part = ""
                for ch in word:
                    cand = part + ch
                    if part and metrics.horizontalAdvance(cand) > available:
                        chunks.append(part)
                        part = ch
                    else:
                        part = cand
                current = part
            else:
                current = word

        if current:
            chunks.append(current)

        return [x.strip() for x in chunks if x.strip()]

    def _pixel_safe_timed_cues(self, cues):
        out = []
        for start, end, body in cues:
            start = float(start)
            end = float(end)
            if end <= start:
                continue

            chunks = self._split_subtitle_text_pixel_safe(body)
            if not chunks:
                continue
            if len(chunks) == 1:
                out.append((start, end, chunks[0]))
                continue

            duration = end - start
            weights = []
            for chunk in chunks:
                if " " in chunk:
                    weights.append(max(1.0, len(chunk.split()) + len(chunk) / 40.0))
                else:
                    weights.append(max(1.0, len(chunk)))
            total = sum(weights) or float(len(chunks))

            cursor = start
            for i, (chunk, weight) in enumerate(zip(chunks, weights)):
                cue_end = end if i == len(chunks) - 1 else cursor + duration * weight / total
                cue_end = min(end, max(cursor + 0.08, cue_end))
                out.append((cursor, cue_end, chunk))
                cursor = cue_end
        return out

    def _reflow_srt_pixel_safe(self, path: str):
        target = Path(path)
        if (
            not self.sub_single_line.isChecked()
            or not target.exists()
            or target.suffix.lower() != ".srt"
        ):
            return str(target)

        cues = subtitle_engine.parse_srt(
            target.read_text(encoding="utf-8-sig", errors="replace")
        )
        cues = self._pixel_safe_timed_cues(cues)
        subtitle_engine.write_srt_cues(cues, str(target))
        return str(target)

    def _display_subtitle_for_time(self, start, end, body, second):
        """Safety net for Live Preview.

        Even if an old/project SRT was not reflowed yet, never draw a clipped
        line: split it by exact pixel width and choose the correct phrase for
        the current timestamp.
        """
        chunks = self._split_subtitle_text_pixel_safe(body)
        if len(chunks) <= 1 or end <= start:
            return chunks[0] if chunks else ""

        duration = end - start
        weights = [
            max(1.0, len(c.split()) + len(c) / 40.0) if " " in c else max(1.0, len(c))
            for c in chunks
        ]
        total = sum(weights) or float(len(chunks))
        elapsed = max(0.0, min(duration, float(second) - float(start)))

        acc = 0.0
        for i, (chunk, weight) in enumerate(zip(chunks, weights)):
            acc += duration * weight / total
            if elapsed <= acc or i == len(chunks) - 1:
                return chunk
        return chunks[-1]

    def _stable_sub_char_limit(self):
        metrics = self._subtitle_pixel_metrics()
        avg = max(6.0, metrics.averageCharWidth())
        return max(8, min(60, int(self._subtitle_available_pixel_width() / avg)))


    def sync_sub_layout_to_auto_blur(self, update_cues=False):
        if not hasattr(self, "sub_auto_layout") or not self.sub_auto_layout.isChecked():
            return

        zone = self.auto_subtitle_zone()
        if zone:
            margin = max(0.0, min(15.0, float(self.sub_inner_margin.value())))
            x = float(zone.get("x", 8.0))
            y = float(zone.get("y", 71.0))
            w = float(zone.get("w", 84.0))
            h = float(zone.get("h", 11.0))

            center_x = x + w / 2.0
            center_y = y + h / 2.0
            inner_w = max(20.0, w - margin * 2.0)
            # Fixed size for the whole project, relative to the Auto Blur/video band.
            font_size = round(max(30.0, min(64.0, h * 1920.0 / 100.0 * 0.27)))

            widgets = [self.sub_x, self.sub_y, self.sub_width, self.sub_size]
            for widget in widgets:
                widget.blockSignals(True)
            self.sub_x.setValue(round(center_x))
            self.sub_y.setValue(round(center_y))
            self.sub_width.setValue(round(inner_w))
            self.sub_size.setValue(font_size)
            for widget in widgets:
                widget.blockSignals(False)
        else:
            widgets = [self.sub_x, self.sub_y, self.sub_width]
            for widget in widgets:
                widget.blockSignals(True)
            self.sub_x.setValue(50)
            self.sub_y.setValue(84)
            self.sub_width.setValue(86)
            for widget in widgets:
                widget.blockSignals(False)

        self.sub_max_chars.blockSignals(True)
        self.sub_max_chars.setValue(self._stable_sub_char_limit())
        self.sub_max_chars.blockSignals(False)
        self.update_live_overlay_state()

        if update_cues:
            self.reflow_current_subtitle_for_layout()

    def reflow_current_subtitle_for_layout(self):
        path = self.sub_path.text().strip()
        if (
            not self.sub_single_line.isChecked()
            or not path
            or Path(path).suffix.lower() != ".srt"
            or not Path(path).exists()
        ):
            return
        try:
            self._reflow_srt_pixel_safe(path)
            self.load_subtitle_file(path)
        except Exception:
            self.log_line("[SUB REFLOW ERROR]\n" + traceback.format_exc())

    def current_subtitle_style(self) -> SubtitleStyle:
        return SubtitleStyle(
            preset_name=self.sub_preset.currentText(),
            font_name=self.sub_font.currentFont().family(),
            font_size=self.sub_size.value(),
            primary_color=self.sub_color.text().strip() or "#FFFFFF",
            outline_color=self.sub_outline_color.text().strip() or "#000000",
            background_color=self.sub_bg_color.text().strip() or "#000000",
            bold=self.sub_bold.isChecked(),
            italic=self.sub_italic.isChecked(),
            outline=self.sub_outline.value(),
            shadow=self.sub_shadow.value(),
            background_box=self.sub_background_box.isChecked(),
            background_opacity=self.sub_bg_opacity.value(),
            x_percent=self.sub_x.value(),
            y_percent=self.sub_y.value(),
            width_percent=self.sub_width.value(),
            max_chars_per_line=self.sub_max_chars.value(),
            single_line_auto=self.sub_single_line.isChecked(),
            min_font_size=self.sub_size.value(),
            auto_layout=self.sub_auto_layout.isChecked(),
            inner_margin_percent=self.sub_inner_margin.value(),
            uppercase=self.sub_uppercase.isChecked(),
            animation=self.sub_animation.currentText(),
            animation_duration_ms=self.sub_anim_duration.value(),
            animation_strength=self.sub_anim_strength.value(),
            karaoke_color=self.sub_karaoke_color.text().strip() or "#FFE600",
            word_pop_scale=self.sub_word_pop_scale.value(),
            word_pop_ms=self.sub_word_pop_ms.value(),
        )

    def apply_subtitle_style(self, style: SubtitleStyle):
        self.sub_preset.blockSignals(True)
        self.sub_preset.setCurrentText(style.preset_name)
        self.sub_preset.blockSignals(False)
        _family_font = QFont(style.font_name)
        _family_font.setPointSize(10)
        self.sub_font.setCurrentFont(_family_font)
        self.sub_size.setValue(style.font_size)
        self.sub_color.setText(style.primary_color)
        self.sub_outline.setValue(style.outline)
        self.sub_outline_color.setText(style.outline_color)
        self.sub_bold.setChecked(style.bold)
        self.sub_italic.setChecked(style.italic)
        self.sub_background_box.setChecked(style.background_box)
        self.sub_bg_color.setText(style.background_color)
        self.sub_bg_opacity.setValue(style.background_opacity)
        self.sub_shadow.setValue(style.shadow)
        self.sub_x.setValue(getattr(style, "x_percent", 50))
        self.sub_y.setValue(style.y_percent)
        self.sub_width.setValue(getattr(style, "width_percent", 80))
        self.sub_max_chars.setValue(style.max_chars_per_line)
        self.sub_single_line.setChecked(getattr(style, "single_line_auto", True))
        self.sub_min_font.setValue(getattr(style, "font_size", 48))
        self.sub_auto_layout.setChecked(getattr(style, "auto_layout", True))
        self.sub_animation.setCurrentText(
            getattr(style, "animation", "Không")
        )
        self.sub_anim_duration.setValue(
            int(getattr(style, "animation_duration_ms", 220))
        )
        self.sub_anim_strength.setValue(
            int(getattr(style, "animation_strength", 100))
        )
        self.sub_karaoke_color.setText(
            getattr(style, "karaoke_color", "#FFE600")
        )
        self.sub_word_pop_scale.setValue(
            int(getattr(style, "word_pop_scale", 108))
        )
        self.sub_word_pop_ms.setValue(
            int(getattr(style, "word_pop_ms", 110))
        )
        self.sub_inner_margin.setValue(getattr(style, "inner_margin_percent", 5))
        self.sub_uppercase.setChecked(style.uppercase)
        self.update_subtitle_preview_style()

    def apply_named_subtitle_preset(self, name):
        if name in subtitle_engine.PRESETS:
            self.apply_subtitle_style(subtitle_engine.clone_preset(name))

    def open_subtitle_preset_dialog(self):
        dlg = SubtitlePresetDialog(self)
        if dlg.exec() == QDialog.Accepted and dlg.selected_name:
            self.apply_subtitle_style(subtitle_engine.clone_preset(dlg.selected_name))

    def update_subtitle_preview_style(self, *args):
        if not hasattr(self, "live_overlay"):
            return
        self.update_live_overlay_state()
        self.schedule_autosave()
        self.schedule_processed_preview()


    def subtitle_one_line_char_limit(self):
        return self._stable_sub_char_limit()


    def normalize_current_srt_to_one_line(self, path: str | None = None):
        if not self.sub_single_line.isChecked():
            return path or self.sub_path.text().strip()
        target = str(path or self.sub_path.text().strip())
        if not target or Path(target).suffix.lower() != ".srt" or not Path(target).exists():
            return target
        self._reflow_srt_pixel_safe(target)
        return target

    def get_sub_from_ai(self):
        self.sync_scene_table()
        manifest = []
        manifest_path = self.project.voice_manifest_path

        if manifest_path:
            manifest = ffm.load_voice_manifest(manifest_path)

        # Projects made before v0.7 may have scene voice timing but no manifest file.
        if not manifest:
            for scene in self.project.scenes:
                if scene.voice_end > scene.voice_start >= 0 and scene.en_voice.strip():
                    manifest.append({
                        "scene_index": scene.index,
                        "start": scene.voice_start,
                        "end": scene.voice_end,
                        "en_text": scene.en_voice,
                        "vi_text": scene.vi_voice,
                    })

        if not manifest:
            QMessageBox.warning(
                self, "Subtitle",
                "Hãy TẠO GIỌNG ĐỌC trước.\n\n"
                "v0.7 tạo subtitle từ thời lượng voice THẬT, không còn lấy "
                "timeline ước lượng ban đầu của AI."
            )
            return

        try:
            workspace = self.ai_workspace()
        except Exception as e:
            QMessageBox.warning(self, "Subtitle", str(e))
            return

        target = self.translate_target.currentText()
        if target == "Tiếng Việt":
            language = "vi"
            suffix = "vi"
        else:
            language = "en"
            suffix = "en"

        out = workspace / f"subtitle_voice_synced_{suffix}.srt"
        ffm.write_srt_from_voice_manifest(
            manifest,
            str(out),
            language,
            max_chars=self.subtitle_one_line_char_limit(),
            single_line=self.sub_single_line.isChecked(),
            hide_on_voice_pause=self.sub_hide_on_voice_pause.isChecked(),
            pause_ms=self.sub_pause_gap_ms.value(),
            word_by_word=(
                self.sub_animation.currentText() == "Word Pop Sync"
            ),
        )

        self._reflow_srt_pixel_safe(str(out))
        self.project.subtitle_path = str(out)
        self.sub_path.setText(str(out))
        self.sub_enabled.setChecked(True)
        self.load_subtitle_file(str(out))
        self.autosave_project()

        self.update_live_overlay_state()
        self.status(
            "Subtitle đã khớp voice và hiển thị trực tiếp trên Live Preview; "
            "render cache chạy ngầm."
        )
        self.schedule_processed_preview()

    def choose_sub(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn subtitle", "", "Subtitle (*.srt *.ass *.ssa)"
        )
        if path:
            # Keep imported ASS untouched; SRT can be normalized to one-line mode.
            if Path(path).suffix.lower() == ".srt":
                self.normalize_current_srt_to_one_line(path)
            self.sub_path.setText(path)
            self.project.subtitle_path = path
            self.sub_enabled.setChecked(True)
            self.load_subtitle_file(path)
            self.schedule_autosave()

    def load_subtitle_file(self, path):
        p = Path(path)
        if not p.exists():
            return
        self.subtitle_group_id = hashlib.sha1(str(p.resolve()).encode("utf-8", errors="ignore")).hexdigest()[:14]
        if p.suffix.lower() == ".srt":
            text = p.read_text(encoding="utf-8-sig", errors="replace")
            self.sub_editor.blockSignals(True)
            self.sub_editor.setPlainText(text)
            self.sub_editor.blockSignals(False)
            self.preview_cues = subtitle_engine.parse_srt(text)
        else:
            self.sub_editor.blockSignals(True)
            self.sub_editor.setPlainText(
                "ASS/SSA đã chọn. Preview text editor chỉ hiển thị SRT."
            )
            self.sub_editor.blockSignals(False)
            self.preview_cues = []
        self.update_preview_subtitle(self.player.position() / 1000)
        self.editor_refresh_all()

    def _current_subtitle_group_id(self):
        return getattr(self, "subtitle_group_id", "") or "subtitle-group"

    def preview_cues_from_editor(self):
        if Path(self.sub_path.text().strip()).suffix.lower() == ".srt":
            self.preview_cues = subtitle_engine.parse_srt(self.sub_editor.toPlainText())
            self.update_preview_subtitle(self.player.position() / 1000)

    def save_sub_editor(self):
        path = self.sub_path.text().strip()
        if not path:
            try:
                workspace = self.ai_workspace()
            except Exception as e:
                QMessageBox.warning(self, "Subtitle", str(e))
                return
            path = str(workspace / "subtitle_manual.srt")
            self.sub_path.setText(path)
        if Path(path).suffix.lower() != ".srt":
            QMessageBox.warning(self, "Subtitle", "Editor này lưu SRT.")
            return
        Path(path).write_text(self.sub_editor.toPlainText(), encoding="utf-8-sig")
        self.normalize_current_srt_to_one_line(path)
        self.project.subtitle_path = path
        self.load_subtitle_file(path)
        self.autosave_project()
        self.status("Đã lưu subtitle — chế độ 1 dòng đã được áp dụng.")

    def preview_subtitle_state_at(self, second):
        """Return (text, start, end).

        IMPORTANT: once a real SRT/voice timeline exists, never fall back to
        whole AI scene windows. That old fallback kept text visible while the
        narration was already silent.
        """
        second = float(second or 0.0)

        if self.preview_cues:
            for start, end, body in self.preview_cues:
                # End is exclusive so adjacent/gap boundaries never linger.
                if start <= second < end:
                    text = self._display_subtitle_for_time(
                        start,
                        end,
                        body,
                        second,
                    )
                    return text, float(start), float(end)
            return "", second, second

        # Before voice/sub generation there may be no SRT yet. Only then is
        # scene narration a useful editor fallback.
        for scene in self.project.scenes:
            if scene.start <= second < scene.end:
                text = self._display_subtitle_for_time(
                    scene.start,
                    scene.end,
                    scene.en_voice,
                    second,
                )
                return text, float(scene.start), float(scene.end)

        return "", second, second

    def regenerate_subtitle_for_animation_mode(self, *args):
        """Rebuild voice-derived SRT when switching into/out of Word Pop Sync."""
        if self._restoring_state:
            return

        manifest_path = str(
            getattr(self.project, "voice_manifest_path", "") or ""
        )
        if not manifest_path or not Path(manifest_path).exists():
            self.update_live_overlay_state()
            if self.sub_animation.currentText() == "Word Pop Sync":
                self.status(
                    "Word Pop Sync đã bật. Hãy tạo voice trước để có "
                    "timeline từng từ."
                )
            return

        try:
            manifest = ffm.load_voice_manifest(manifest_path)
            if not manifest:
                return

            effect = self.sub_animation.currentText()
            current_path = self.sub_path.text().strip()

            # Only auto-regenerate if entering Word Pop, or if leaving Word Pop
            # while currently displaying the generated word-pop subtitle file.
            entering_word_pop = effect == "Word Pop Sync"
            leaving_generated_word_pop = (
                not entering_word_pop
                and current_path
                and Path(current_path).name.startswith("subtitle_word_pop_")
            )
            if not entering_word_pop and not leaving_generated_word_pop:
                self.update_live_overlay_state()
                return

            workspace = self.ai_workspace()
            target = self.translate_target.currentText()
            language = "vi" if target == "Tiếng Việt" else "en"

            if entering_word_pop:
                out = workspace / f"subtitle_word_pop_{language}.srt"
            else:
                out = workspace / f"subtitle_voice_synced_{language}.srt"

            ffm.write_srt_from_voice_manifest(
                manifest,
                str(out),
                language,
                max_chars=self.subtitle_one_line_char_limit(),
                single_line=True if entering_word_pop else self.sub_single_line.isChecked(),
                hide_on_voice_pause=self.sub_hide_on_voice_pause.isChecked(),
                pause_ms=self.sub_pause_gap_ms.value(),
                word_by_word=entering_word_pop,
            )

            self.project.subtitle_path = str(out)
            self.sub_path.setText(str(out))
            self.sub_enabled.setChecked(True)
            self.load_subtitle_file(str(out))
            self.autosave_project()
            self.update_live_overlay_state()
            self.schedule_processed_preview()

            if entering_word_pop:
                self.status(
                    "Word Pop Sync: subtitle đã chuyển sang từng từ theo voice."
                )
            else:
                self.status(
                    "Đã trở lại subtitle theo câu/dòng."
                )
        except Exception:
            self.log_line(
                "[WORD POP SYNC ERROR]\n" + traceback.format_exc()
            )

    def update_preview_subtitle(self, second):
        if not hasattr(self, "live_overlay"):
            return

        text = ""
        cue_start = float(second or 0.0)
        cue_end = cue_start

        if not self.preview_sub_hidden and self.sub_enabled.isChecked():
            text, cue_start, cue_end = self.preview_subtitle_state_at(second)

        self.live_overlay.set_subtitle_state(
            self.sub_enabled.isChecked() and not self.preview_sub_hidden,
            text,
            self.current_subtitle_style(),
            effect=self.sub_animation.currentText(),
            elapsed=max(0.0, float(second) - cue_start),
            duration=max(0.01, cue_end - cue_start),
        )

    def clean_subtitle_text(self):
        text = self.sub_editor.toPlainText()
        if not text.strip():
            return
        # Conservative clean-up: remove common tags, repeated spaces and excessive blanks.
        text = re.sub(r"<[^>]+>", "", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        self.sub_editor.setPlainText(text.strip() + "\n")
        self.status("Đã lọc rác subtitle.")

    def subtitle_find_replace(self):
        find = self.sub_find.text()
        if not find:
            return
        text = self.sub_editor.toPlainText()
        count = text.count(find)
        self.sub_editor.setPlainText(text.replace(find, self.sub_replace.text()))
        self.status(f"Đã thay {count} vị trí.")

    def translate_current_srt(self):
        source = self.sub_path.text().strip()
        if not source or not Path(source).exists() or Path(source).suffix.lower() != ".srt":
            QMessageBox.warning(self, "Dịch Sub", "Hãy LẤY SUB TỪ AI hoặc chọn SRT trước.")
            return

        target_ui = self.translate_target.currentText()
        target = {
            "English US": "English (United States)",
            "Tiếng Việt": "Vietnamese",
            "中文": "Simplified Chinese",
        }.get(target_ui, target_ui)

        config = self.current_ai_config()
        if not config.api_key:
            QMessageBox.warning(
                self,
                "Dịch Sub",
                f"Chưa nhập API key cho {config.provider} trong Settings.",
            )
            return
        style_name = self.translate_style.currentText()
        style_prompts = {
            "Tự nhiên - video US":
                "Use natural, concise wording suitable for modern video subtitles.",
            "Ngắn gọn - subtitle":
                "Keep each translated cue very concise and easy to read quickly.",
            "Giữ thuật ngữ kỹ thuật":
                "Preserve machine, engineering, factory and technical terminology accurately.",
            "Sát nghĩa":
                "Translate faithfully and do not paraphrase unless necessary for grammar.",
        }
        prompt = style_prompts.get(style_name, "")
        out = str(Path(source).with_name(
            f"{Path(source).stem}_{target_ui.replace(' ','_')}.srt"
        ))

        def job(progress, log):
            return ai.translate_srt_file(
                config,
                source,
                out,
                target,
                prompt,
                log=log,
            )

        def done(path):
            self.normalize_current_srt_to_one_line(path)
            self.sub_path.setText(path)
            self.project.subtitle_path = path
            self.sub_enabled.setChecked(True)
            self.load_subtitle_file(path)
            self.autosave_project()
            self.update_live_overlay_state()
            self.status(
                "Đã dịch subtitle → tự chia thành các cue 1 dòng, vẫn nằm đúng trong timeline voice."
            )
            self.schedule_processed_preview()

        self.run_worker("AI đang dịch subtitle...", job, done)

    # ==================================================================
    # EXPORT STATE / RENDER
    # ==================================================================
    def export_state_dict(self):
        return {
            "resolution": self.resolution.currentText(),
            "codec": self.codec.currentText(),
            "encoder": self.encoder.currentText(),
            "wheel_input_lock": self.wheel_input_lock.isChecked(),
            "strip_metadata": self.strip_metadata.isChecked(),
            "blur_enabled": self.blur_enabled.isChecked(),
            "blur_style": self.blur_style.currentText(),
            "blur_opacity": self.blur_opacity.value(),
            "blur_zones": self.blur_zones(),
            "auto_cover_source_subtitle": self.auto_cover_source_sub.isChecked(),
            "auto_subtitle_zone": self.auto_subtitle_zone(),
            "speed_enabled": self.speed_enabled.isChecked(),
            "play_speed": self.play_speed.value(),
            "logo_enabled": self.logo_enabled.isChecked(),
            "logo_path": self.logo_path.text().strip(),
            "logo_position": self.logo_pos.currentText(),
            "logo_scale": self.logo_scale.value(),
            "logo_x": self.logo_x.value(),
            "logo_y": self.logo_y.value(),
            "logo_opacity": self.logo_opacity.value(),
            "logo_remove_bg": self.logo_remove_bg.isChecked(),
            "side_bg_enabled": self.side_bg_enabled.isChecked(),
            "side_bg_type": self.side_bg_type.currentText(),
            "overlay_enabled": self.overlay_enabled.isChecked(),
            "overlay_text": self.overlay_text.text(),
            "overlay_font": self.overlay_font.currentFont().family(),
            "overlay_size": self.overlay_size.value(),
            "overlay_x": self.overlay_x.value(),
            "overlay_y": self.overlay_y.value(),
            "overlay_color": self.overlay_color.text(),
            "overlay_position": self.overlay_pos.currentText(),
            "mute_music": self.mute_music.isChecked(),
            "mute_original_voice": self.mute_original_voice.isChecked(),
            "source_volume": self.source_volume.value(),
            "narration_volume": self.narration_volume.value(),
            "music_volume": self.music_volume.value(),
            "music_file": self.music_file.text().strip(),
            "accompaniment_path": self.accompaniment_path,
            "vocals_path": self.vocals_path,
            "subtitle_style": self.current_subtitle_style().__dict__,
            "sub_enabled": self.sub_enabled.isChecked(),
            "sub_hide_on_voice_pause": self.sub_hide_on_voice_pause.isChecked(),
            "sub_pause_gap_ms": self.sub_pause_gap_ms.value(),
            "editor_use_timeline": (
                self.editor_use_timeline.isChecked()
                if hasattr(self, "editor_use_timeline")
                else False
            ),
            "editor_clips": [
                dict(c) for c in getattr(self, "editor_clips", [])
            ],
            "editor_layers": [
                dict(layer) for layer in getattr(self, "editor_layers", [])
            ],
            "preview_zoom_percent": int(
                getattr(self, "preview_zoom_percent", 100)
            ),
            "project_aspect_ratio": self.editor_document.aspect_ratio,
            "subtitle_group_id": self._current_subtitle_group_id(),
            "workspace_splitter_sizes": (
                self.video_editor_tab.sizes()
                if hasattr(self, "video_editor_tab") else {}
            ),
            "editor_visible": bool(
                hasattr(self, "editor_panel")
                and self.editor_panel.isVisible()
            ),
            "editor_restore_sizes": list(
                getattr(self, "editor_last_splitter_sizes", [760, 300])
            ),
            "export_body_sizes": (
                self.export_body_splitter.sizes()
                if hasattr(self, "export_body_splitter")
                else [355, 880, 470]
            ),
            "export_vertical_sizes": (
                self.export_vertical_splitter.sizes()
                if hasattr(self, "export_vertical_splitter")
                else [760, 300]
            ),
            "export_log_visible": bool(
                hasattr(self, "log") and self.log.isVisible()
            ),
            "editor_layer_props_visible": bool(
                hasattr(self, "editor_layer_props_panel")
                and self.editor_layer_props_panel.isVisible()
            ),
            "left_panel_visible": bool(
                hasattr(self, "export_left_panel")
                and self.export_left_panel.isVisible()
            ),
            "right_panel_visible": bool(
                hasattr(self, "export_right_panel")
                and self.export_right_panel.isVisible()
            ),
        }

    def apply_export_state(self, data):
        if not data:
            return
        self._restoring_state = True
        for key, widget in {
            "resolution": self.resolution,
            "codec": self.codec,
            "encoder": self.encoder,
            "blur_style": self.blur_style,
            "logo_position": self.logo_pos,
            "side_bg_type": self.side_bg_type,
            "overlay_position": self.overlay_pos,
        }.items():
            if key in data:
                widget.setCurrentText(str(data[key]))

        for key, widget in {
            "blur_opacity": self.blur_opacity,
            "play_speed": self.play_speed,
            "logo_scale": self.logo_scale,
            "logo_x": self.logo_x,
            "logo_y": self.logo_y,
            "logo_opacity": self.logo_opacity,
            "overlay_size": self.overlay_size,
            "overlay_x": self.overlay_x,
            "overlay_y": self.overlay_y,
        }.items():
            if key in data:
                try:
                    widget.setValue(data[key])
                except Exception:
                    pass

        for key, widget in {
            "strip_metadata": self.strip_metadata,
            "wheel_input_lock": self.wheel_input_lock,
            "blur_enabled": self.blur_enabled,
            "auto_cover_source_subtitle": self.auto_cover_source_sub,
            "speed_enabled": self.speed_enabled,
            "logo_enabled": self.logo_enabled,
            "logo_remove_bg": self.logo_remove_bg,
            "side_bg_enabled": self.side_bg_enabled,
            "overlay_enabled": self.overlay_enabled,
            "mute_music": self.mute_music,
            "mute_original_voice": self.mute_original_voice,
            "sub_enabled": self.sub_enabled,
        }.items():
            if key in data:
                widget.setChecked(bool(data[key]))

        if "logo_path" in data:
            self.logo_path.setText(str(data["logo_path"] or ""))
        if "overlay_text" in data:
            self.overlay_text.setText(str(data["overlay_text"] or ""))
        if "overlay_font" in data:
            self.overlay_font.setCurrentFont(QFont(str(data["overlay_font"] or "Arial")))
        if "overlay_color" in data:
            self.overlay_color.setText(str(data["overlay_color"] or "#FFFFFF"))
        if "music_file" in data:
            self.music_file.setText(str(data["music_file"] or ""))

        for key, widget in {
            "source_volume": self.source_volume,
            "narration_volume": self.narration_volume,
            "music_volume": self.music_volume,
        }.items():
            if key in data:
                widget.setValue(int(data[key]))

        self.accompaniment_path = str(data.get("accompaniment_path", "") or "")
        self.vocals_path = str(data.get("vocals_path", "") or "")

        if isinstance(data.get("subtitle_style"), dict):
            try:
                self.apply_subtitle_style(SubtitleStyle(**data["subtitle_style"]))
            except Exception:
                pass

        if "sub_hide_on_voice_pause" in data:
            self.sub_hide_on_voice_pause.setChecked(
                bool(data["sub_hide_on_voice_pause"])
            )
        if "sub_pause_gap_ms" in data:
            try:
                self.sub_pause_gap_ms.setValue(
                    int(data["sub_pause_gap_ms"])
                )
            except Exception:
                pass

        # Restore non-destructive Basic Editor state.
        if isinstance(data.get("editor_clips"), list):
            self.editor_clips[:] = [
                editor_engine.normalize_clip(c)
                for c in data["editor_clips"]
                if isinstance(c, dict)
            ]
        if isinstance(data.get("editor_layers"), list):
            self.editor_layers[:] = [
                dict(layer)
                for layer in data["editor_layers"]
                if isinstance(layer, dict)
            ]
        self.editor_document.replace_legacy_state(
            self.editor_clips, self.editor_layers
        )
        if hasattr(self, "editor_use_timeline"):
            self.editor_use_timeline.setChecked(
                bool(data.get("editor_use_timeline", False))
            )
        self.editor_selected_clip = (
            0 if self.editor_clips else -1
        )
        self.editor_selected_layer = -1

        if isinstance(data.get("blur_zones"), list):
            self.blur_zone_list.clear()
            auto_zone = data.get("auto_subtitle_zone")
            if isinstance(auto_zone, dict) and auto_zone:
                self.ensure_auto_sub_zone(auto_zone)
            for zone in data["blur_zones"]:
                if isinstance(zone, dict):
                    self.add_blur_zone(zone)

        # Restore professional workspace layout without firing editing actions.
        self.preview_zoom_percent = max(
            50, min(300, int(data.get("preview_zoom_percent", 100)))
        )
        if hasattr(self, "preview_zoom_label"):
            self.preview_zoom_label.setText(
                f"{self.preview_zoom_percent}%"
            )
        if hasattr(self, "live_overlay"):
            self.live_overlay.set_preview_zoom(
                self.preview_zoom_percent / 100.0,
                reset_pan=True,
            )
        ratio = str(data.get("project_aspect_ratio", "Original"))
        self.subtitle_group_id = str(data.get("subtitle_group_id", "") or "")
        if hasattr(self, "preview_ratio_combo"):
            self.preview_ratio_combo.setCurrentText(ratio)
        if hasattr(self, "video_editor_tab") and isinstance(data.get("workspace_splitter_sizes"), dict):
            QTimer.singleShot(0, lambda sizes=data["workspace_splitter_sizes"]: self.video_editor_tab.restore_sizes(sizes))

        restore_sizes = data.get("editor_restore_sizes")
        if isinstance(restore_sizes, list) and len(restore_sizes) >= 2:
            self.editor_last_splitter_sizes = [
                max(0, int(x)) for x in restore_sizes[:2]
            ]

        if hasattr(self, "log_toggle_btn"):
            log_visible = bool(data.get("export_log_visible", False))
            self.log_toggle_btn.blockSignals(True)
            self.log_toggle_btn.setChecked(log_visible)
            self.log_toggle_btn.blockSignals(False)
            self.log.setVisible(log_visible)
            self.log_toggle_btn.setText(
                "▾ Log" if log_visible else "▸ Log"
            )

        if hasattr(self, "editor_layer_props_toggle"):
            props_visible = bool(
                data.get("editor_layer_props_visible", False)
            )
            self.editor_layer_props_toggle.blockSignals(True)
            self.editor_layer_props_toggle.setChecked(props_visible)
            self.editor_layer_props_toggle.blockSignals(False)
            self.editor_layer_props_panel.setVisible(props_visible)
            self.editor_layer_props_toggle.setText(
                "▾ Thuộc tính" if props_visible else "▸ Thuộc tính"
            )

        left_visible = bool(data.get("left_panel_visible", True))
        right_visible = bool(data.get("right_panel_visible", True))
        if hasattr(self, "left_panel_btn"):
            self.left_panel_btn.blockSignals(True)
            self.left_panel_btn.setChecked(left_visible)
            self.left_panel_btn.blockSignals(False)
            self.export_left_panel.setVisible(left_visible)
        if hasattr(self, "right_panel_btn"):
            self.right_panel_btn.blockSignals(True)
            self.right_panel_btn.setChecked(right_visible)
            self.right_panel_btn.blockSignals(False)
            self.export_right_panel.setVisible(right_visible)

        editor_visible = bool(data.get("editor_visible", False))
        if hasattr(self, "editor_toggle_btn"):
            self.editor_toggle_btn.blockSignals(True)
            self.editor_toggle_btn.setChecked(editor_visible)
            self.editor_toggle_btn.blockSignals(False)
            self.editor_toggle_btn.setText(
                "✂ Ẩn Editor" if editor_visible else "✂ Video Editor"
            )
            self.editor_panel.setVisible(editor_visible)

        body_sizes = data.get("export_body_sizes")
        vertical_sizes = data.get("export_vertical_sizes")
        if hasattr(self, "export_body_splitter") and isinstance(body_sizes, list):
            QTimer.singleShot(0, lambda v=[int(x) for x in body_sizes]: self.export_body_splitter.setSizes(v))
        if hasattr(self, "export_vertical_splitter"):
            if editor_visible and isinstance(vertical_sizes, list):
                QTimer.singleShot(0, lambda v=[int(x) for x in vertical_sizes]: self.export_vertical_splitter.setSizes(v))
            elif editor_visible:
                QTimer.singleShot(0, lambda: self.export_vertical_splitter.setSizes(self.editor_last_splitter_sizes))
            else:
                QTimer.singleShot(0, lambda: self.export_vertical_splitter.setSizes([1000, 0]))

        self._restoring_state = False
        self.update_audio_control_labels()
        if hasattr(self, "editor_timeline"):
            self.editor_refresh_all()
        self.update_live_overlay_state()

    def gather_export_options(self):
        fit_mode = "Crop"
        if self.side_bg_enabled.isChecked():
            fit_mode = "Blur background" if self.side_bg_type.currentText() == "Mờ video" else "Pad"

        source_audio_mode = "Giữ âm gốc"
        if self.mute_original_voice.isChecked():
            if self.accompaniment_path and Path(self.accompaniment_path).exists():
                source_audio_mode = "Chỉ nhạc nền đã tách"
            else:
                source_audio_mode = "Tắt toàn bộ âm gốc"

        narration = self.voice_file.text().strip()
        if not narration and self.narration_path:
            narration = self.narration_path

        music_volume = 0.0 if self.mute_music.isChecked() else self.music_volume.value() / 100.0

        return ExportOptions(
            resolution=self.resolution.currentText(),
            fit_mode=fit_mode,
            codec=self.codec.currentText(),
            encoder=self.encoder.currentText(),

            speed=self.play_speed.value() if self.speed_enabled.isChecked() else 1.0,
            zoom=1.0,
            auto_zoom=False,
            mirror=False,
            border=0,
            brightness=0.0,
            contrast=1.0,
            saturation=1.0,
            sharpen=0.0,
            vignette=False,
            strip_metadata=self.strip_metadata.isChecked(),

            burn_subtitle=self.sub_enabled.isChecked(),
            subtitle_path=self.sub_path.text().strip(),
            subtitle_style=self.current_subtitle_style(),

            logo_path=self.logo_path.text().strip() if self.logo_enabled.isChecked() else "",
            logo_position=self.logo_pos.currentText(),
            logo_scale=self.logo_scale.value() / 100.0,
            logo_x_percent=self.logo_x.value(),
            logo_y_percent=self.logo_y.value(),
            logo_opacity=self.logo_opacity.value(),
            logo_remove_white_bg=self.logo_remove_bg.isChecked(),

            overlay_text=self.overlay_text.text().strip() if self.overlay_enabled.isChecked() else "",
            overlay_position=self.overlay_pos.currentText(),
            overlay_font_name=self.overlay_font.currentFont().family(),
            overlay_font_size=self.overlay_size.value(),
            overlay_color=self.overlay_color.text().strip() or "#FFFFFF",
            overlay_x_percent=self.overlay_x.value(),
            overlay_y_percent=self.overlay_y.value(),

            editor_layers=[
                dict(layer) for layer in self.editor_layers
            ],

            blur_enabled=self.blur_enabled.isChecked(),
            blur_zones=self.blur_zones(),
            blur_style=self.blur_style.currentText(),
            blur_opacity=self.blur_opacity.value(),
            auto_cover_source_subtitle=self.auto_cover_source_sub.isChecked(),
            auto_subtitle_zone=self.auto_subtitle_zone(),

            source_audio_mode=source_audio_mode,
            source_volume=self.source_volume.value() / 100.0,
            accompaniment_path=self.accompaniment_path,
            narration_path=narration if narration and Path(narration).exists() else "",
            narration_volume=self.narration_volume.value() / 100.0,
            narration_speed=1.0,
            background_music_path=self.music_file.text().strip(),
            background_music_volume=music_volume,
            background_music_loop=True,
            duck_source_under_voice=True,
        )

    def export_batch(self):
        has_editor_timeline = (
            hasattr(self, "editor_use_timeline")
            and self.editor_use_timeline.isChecked()
            and bool(self.editor_clips)
        )
        if not self.queue and not has_editor_timeline:
            QMessageBox.warning(self, "Xuất Video", "Chưa có video.")
            return

        try:
            # Ensure current subtitle editor/project edits are persisted.
            if self.sub_path.text().strip() and Path(self.sub_path.text().strip()).suffix.lower() == ".srt":
                self.save_sub_editor()
            self.autosave_project()

            out_dir = Path(self.output_dir.text().strip() or ROOT / "exports")
            out_dir.mkdir(parents=True, exist_ok=True)

            if self.sub_enabled.isChecked():
                sub_file = self.sub_path.text().strip()
                if sub_file and Path(sub_file).suffix.lower() == ".srt":
                    try:
                        self._reflow_srt_pixel_safe(sub_file)
                        self.load_subtitle_file(sub_file)
                    except Exception:
                        self.log_line(
                            "[SUB PIXEL REFLOW BEFORE EXPORT ERROR]\n"
                            + traceback.format_exc()
                        )

            options = self.gather_export_options()
            self.stop_requested = False
            self.preview_render_timer.stop()
        except Exception:
            tb = traceback.format_exc()
            self.log_line("[EXPORT PREFLIGHT ERROR]\n" + tb)
            QMessageBox.critical(self, "Xuất Video", "Không thể chuẩn bị xuất video. Ứng dụng vẫn tiếp tục chạy.\n\n" + tb[-1800:])
            return

        def job(progress, log):
            outputs = []

            def next_target(source_path):
                stem = Path(source_path).stem
                base = out_dir / f"{stem}_MS.mp4"
                if not base.exists():
                    return base
                for n in range(2, 1000):
                    candidate = out_dir / f"{stem}_MS_{n}.mp4"
                    if not candidate.exists():
                        return candidate
                return out_dir / f"{stem}_MS_{int(datetime.datetime.now().timestamp())}.mp4"

            # Basic Editor timeline replaces batch sources when enabled.
            if (
                hasattr(self, "editor_use_timeline")
                and self.editor_use_timeline.isChecked()
                and self.editor_clips
            ):
                target = next_target("MachineStudio_Timeline.mp4")
                temp_target = target.with_name(
                    target.stem + ".__rendering__.mp4"
                )

                workspace = self.project_workspace_for(
                    self.current_video()
                    or self.editor_clips[0]["path"]
                )
                timeline_source = workspace / "editor_timeline_source.mp4"

                target_size = ffm.parse_resolution(
                    options.resolution
                )
                tw = target_size[0] if target_size else None
                th = target_size[1] if target_size else None

                log("===== BASIC EDITOR TIMELINE EXPORT =====")
                log(
                    f"[EDITOR] clips={len(self.editor_clips)} | "
                    f"duration={editor_engine.total_duration(self.editor_clips):.2f}s"
                )

                editor_engine.render_timeline(
                    self.editor_clips,
                    str(timeline_source),
                    target_width=tw,
                    target_height=th,
                    preview=False,
                    log=log,
                    process_holder=self.process_holder,
                )
                progress(1, 2)

                ffm.export_video(
                    str(timeline_source),
                    str(temp_target),
                    options,
                    log=log,
                    process_holder=self.process_holder,
                )
                if (
                    not temp_target.exists()
                    or temp_target.stat().st_size < 1024
                ):
                    raise RuntimeError(
                        "FFmpeg không tạo được output timeline hợp lệ."
                    )
                os.replace(str(temp_target), str(target))
                outputs.append(str(target))
                progress(2, 2)
                return outputs

            for i, source in enumerate(list(self.queue)):
                if self.stop_requested:
                    break

                target = next_target(source)
                temp_target = target.with_name(target.stem + ".__rendering__.mp4")
                try:
                    temp_target.unlink(missing_ok=True)
                except Exception:
                    pass

                log(f"===== [{i+1}/{len(self.queue)}] {Path(source).name} =====")
                log(f"[OUTPUT] {target}")

                try:
                    ffm.export_video(
                        source,
                        str(temp_target),
                        options,
                        log=log,
                        process_holder=self.process_holder,
                    )
                    if not temp_target.exists() or temp_target.stat().st_size < 1024:
                        raise RuntimeError("FFmpeg không tạo được output hợp lệ.")
                    os.replace(str(temp_target), str(target))
                except Exception:
                    try:
                        temp_target.unlink(missing_ok=True)
                    except Exception:
                        pass
                    raise

                outputs.append(str(target))
                progress(i + 1, len(self.queue))
            return outputs

        def done(outputs):
            if outputs:
                self.last_exported_path = outputs[-1]
            self.status(f"Xuất xong {len(outputs)} video.")
            QMessageBox.information(
                self, "Xuất Video",
                f"Đã xuất {len(outputs)} video vào:\n{out_dir}"
            )

        self.run_worker("Đang xuất video...", job, done)

    def stop_current(self):
        self.stop_requested = True
        process = self.process_holder.get("process")
        if process is not None:
            try:
                process.terminate()
            except Exception:
                pass
        self.status("Đã yêu cầu dừng.")

    def merge_selected(self):
        rows = sorted({idx.row() for idx in self.queue_list.selectedIndexes()})
        paths = [self.queue[row] for row in rows if 0 <= row < len(self.queue)]
        if len(paths) < 2:
            QMessageBox.warning(self, "Ghép Video", "Chọn ít nhất 2 video.")
            return

        default = str(Path(self.output_dir.text().strip() or ROOT / "exports") / "merged.mp4")
        out, _ = QFileDialog.getSaveFileName(self, "Ghép Video", default, "MP4 (*.mp4)")
        if not out:
            return
        if not out.lower().endswith(".mp4"):
            out += ".mp4"

        def job(progress, log):
            return ffm.merge_videos(paths, out, log=log, process_holder=self.process_holder)

        def done(path):
            self.add_paths([path])
            self.status("Ghép video xong.")

        self.run_worker("Đang ghép video...", job, done)

    # ==================================================================
    # PROCESSED PREVIEW
    # ==================================================================
    def schedule_processed_preview(self, *args):
        """Debounced background render.

        Repeated slider/toggle changes only restart the timer. If a preview render
        is already running, mark it dirty and render the newest state once more
        after the current render completes.
        """
        if self._restoring_state:
            return
        # Never compete with AI/TTS/Final Export. Live overlay remains responsive.
        if self.worker and self.worker.isRunning():
            self.preview_dirty = True
            return
        if not (self.current_video() or self.project.video_path):
            return

        self.preview_dirty = True
        self.preview_state.setText("⚡ Live Preview")
        if hasattr(self, "update_preview_btn"):
            self.update_preview_btn.setText("⏳ Cache ngầm...")

        self.preview_render_timer.start()


    def _silent_save_sub_editor(self):
        path = self.sub_path.text().strip()
        if (
            path
            and Path(path).suffix.lower() == ".srt"
            and self.sub_editor.toPlainText().strip()
        ):
            try:
                Path(path).write_text(
                    self.sub_editor.toPlainText(),
                    encoding="utf-8-sig",
                )
            except Exception:
                pass

    def _preview_resolution(self):
        target = ffm.parse_resolution(self.resolution.currentText())
        if not target:
            try:
                info = ffm.probe(self.current_video())
                target = (info["width"], info["height"])
            except Exception:
                target = (1080, 1920)

        w, h = target
        ratio = w / max(1, h)
        if ratio > 1.2:
            return "960x540"
        if ratio > 0.68:
            return "540x720"
        return "540x960"

    def refresh_processed_preview(self, background=True):
        source = self.current_video() or self.project.video_path
        if not source or not Path(source).exists():
            return
        if self.worker and self.worker.isRunning():
            self.preview_dirty = True
            return

        # Don't stack renders. Remember that settings changed while rendering.
        if self.preview_worker and self.preview_worker.isRunning():
            self.preview_dirty = True
            return

        try:
            workspace = self.project_workspace_for(source)
        except Exception:
            return

        self.preview_dirty = False
        self._silent_save_sub_editor()

        options = self.gather_export_options()
        options = replace(
            options,
            resolution=self._preview_resolution(),
            codec="H.264",
            encoder="CPU",
        )

        self.preview_render_seq += 1
        proxy_dir = workspace / "preview_cache"
        proxy_dir.mkdir(parents=True, exist_ok=True)
        out = proxy_dir / f"processed_preview_{self.preview_render_seq:04d}.mp4"

        if hasattr(self, "update_preview_btn"):
            self.update_preview_btn.setText("⏳ Cache ngầm...")
        # Do not disturb the live playback status while caching.

        # Capture a snapshot of the options. Current playback is untouched.
        def render_job(progress, log):
            return ffm.export_video(
                source,
                str(out),
                options,
                log=log,
                process_holder=None,
                fast_preview=True,
            )

        worker = Worker(render_job)
        self.preview_worker = worker
        self._retain_worker(worker)
        worker.log.connect(self.route_log)

        def render_error(tb):
            self.preview_state.setText("Preview background lỗi")
            if hasattr(self, "update_preview_btn"):
                self.update_preview_btn.setText("↻ Render Preview ngầm")
            self.log_line("[BACKGROUND PREVIEW ERROR]\\n" + tb[-3500:])

            # If state changed while rendering, try again after a pause.
            if self.preview_dirty:
                self.preview_render_timer.start()

        def render_done(path):
            try:
                info = ffm.probe(path)
                if info.get("duration", 0) <= 0 or info.get("width", 0) <= 0:
                    raise RuntimeError("Preview proxy không hợp lệ.")
            except Exception as e:
                self.preview_state.setText("Preview background lỗi")
                self.log_line(f"[BACKGROUND PREVIEW INVALID] {e}")
                if hasattr(self, "update_preview_btn"):
                    self.update_preview_btn.setText("↻ Render cache ngầm")
                if self.preview_dirty:
                    self.preview_render_timer.start()
                return

            # NEVER replace the media currently being watched.
            self.preview_pending_path = path
            self.project.processed_preview_path = path
            self.processed_preview_path = path
            self.autosave_project()

            self.preview_state.setText("✓ Render cache sẵn sàng")
            self.update_preview_btn.setText("✓ Xem bản render")
            self.cleanup_old_preview_proxies()

            if self.preview_dirty:
                self.preview_render_timer.start()

        worker.error.connect(render_error)
        worker.done.connect(render_done)
        worker.start()

    def cleanup_old_preview_proxies(self):
        current = ""
        if self.processed_preview_path:
            try:
                current = str(Path(self.processed_preview_path).resolve())
            except Exception:
                current = self.processed_preview_path

        source = self.current_video() or self.project.video_path
        if not source:
            return
        try:
            cache = self.project_workspace_for(source) / "preview_cache"
        except Exception:
            return
        if not cache.exists():
            return

        proxies = sorted(
            cache.glob("processed_preview_*.mp4"),
            key=lambda p: p.stat().st_mtime if p.exists() else 0,
            reverse=True,
        )

        # Keep current + two recent proxies; remove older ones if Windows allows.
        keep = set()
        for p in proxies[:3]:
            try:
                keep.add(str(p.resolve()))
            except Exception:
                keep.add(str(p))

        if current:
            keep.add(current)

        for p in proxies[3:]:
            try:
                rp = str(p.resolve())
            except Exception:
                rp = str(p)
            if rp in keep:
                continue
            try:
                p.unlink()
            except Exception:
                pass


    # ==================================================================
    # CAPCUT BRIDGE
    # ==================================================================
    def capcut_package(self):
        source = self.current_video() or self.project.video_path
        if not source or not Path(source).exists():
            QMessageBox.warning(self, "CapCut", "Chưa chọn video.")
            return

        out_root = Path(self.output_dir.text().strip() or ROOT / "exports")
        pack = out_root / f"{Path(source).stem}_CapCut_Package"
        pack.mkdir(parents=True, exist_ok=True)

        candidates = [
            self.last_exported_path,
            self.processed_preview_path,
            source,
            self.sub_path.text().strip(),
            self.narration_path,
            self.voice_file.text().strip(),
            self.music_file.text().strip(),
            self.accompaniment_path,
        ]

        copied = []
        seen = set()
        try:
            for item in candidates:
                if not item:
                    continue
                p = Path(item)
                if not p.exists():
                    continue
                key = str(p.resolve())
                if key in seen:
                    continue
                seen.add(key)
                target = pack / p.name
                shutil.copy2(p, target)
                copied.append(target.name)

            style_path = pack / "subtitle_style.json"
            subtitle_engine.save_style(
                str(style_path),
                self.current_subtitle_style(),
            )
            copied.append(style_path.name)

            project_path = self.project_autosave_path()
            if project_path and project_path.exists():
                target = pack / "project.json"
                shutil.copy2(project_path, target)
                copied.append(target.name)
        except Exception as e:
            QMessageBox.critical(self, "CapCut", str(e))
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(pack)))
        QMessageBox.information(
            self, "CapCut Package",
            "Đã tạo package:\n\n" + "\n".join(copied)
        )

    def choose_capcut_path(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Chọn CapCut.exe", "",
            "Executable (*.exe);;All files (*.*)"
        )
        if path:
            self.capcut_path.setText(path)

    def open_capcut(self):
        path = self.capcut_path.text().strip()
        if path and Path(path).exists():
            try:
                os.startfile(path)
            except Exception as e:
                QMessageBox.critical(self, "CapCut", str(e))
        else:
            QMessageBox.warning(
                self, "CapCut",
                "Chưa cấu hình CapCut.exe trong Settings."
            )

    # ==================================================================
    # DOWNLOADER
    # ==================================================================
    def choose_download_dir(self):
        path = QFileDialog.getExistingDirectory(
            self, "Thư mục tải", self.dl_dir.text().strip() or str(ROOT / "downloads")
        )
        if path:
            self.dl_dir.setText(path)

    def preview_download_url(self):
        raw = self.url.text().strip()
        try:
            cleaned = downloader.extract_video_url(raw)
            platform = downloader.detect_platform(cleaned)
        except Exception as e:
            self.dl_detected.setText("❌ " + str(e))
            return

        # Put the clean URL back into the field so the user can see what will
        # actually be sent to yt-dlp.
        self.url.setText(cleaned)
        self.dl_detected.setText(f"✓ {platform}: {cleaned}")

    def update_downloader_engine(self):
        self.dl_log.clear()

        def job(progress, log):
            return downloader.update_yt_dlp(log=log)

        def done(version):
            self.dl_engine_version.setText("yt-dlp: " + version)
            self.status("Đã cập nhật downloader engine.")
            QMessageBox.information(
                self,
                "Downloader",
                f"Đã cập nhật yt-dlp.\nVersion: {version}",
            )

        self.run_worker("Đang cập nhật yt-dlp...", job, done)

    def choose_downloader_cookie_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Chọn cookies.txt",
            self.cookies_file.text().strip() or "",
            "Netscape cookies (*.txt);;All files (*.*)",
        )
        if path:
            self.cookies_file.setText(path)
            self.cookies_browser.setCurrentText("cookies.txt")
            self.status("Đã chọn cookies.txt cho Downloader.")

    def start_download(self):
        raw = self.url.text().strip()
        out = self.dl_dir.text().strip() or str(ROOT / "downloads")
        quality = self.dl_quality.currentText()
        cookies = self.cookies_browser.currentText().strip() or "Auto (khuyến nghị)"
        cookies_file = self.cookies_file.text().strip()

        if cookies.lower() == "cookies.txt" and not cookies_file:
            QMessageBox.warning(
                self,
                "Downloader",
                "Bạn đã chọn cookies.txt nhưng chưa chọn file cookie.",
            )
            return

        try:
            cleaned = downloader.extract_video_url(raw)
            platform = downloader.detect_platform(cleaned)
        except Exception as e:
            QMessageBox.warning(self, "Downloader", str(e))
            return

        self.url.setText(cleaned)
        self.dl_detected.setText(f"✓ {platform}: {cleaned}")
        self.dl_log.clear()
        self.dl_log.appendPlainText(
            f"[Machine Studio] yt-dlp: {downloader.yt_dlp_version()}"
        )
        self.dl_log.appendPlainText(f"[Machine Studio] Platform: {platform}")
        self.dl_log.appendPlainText(f"[Machine Studio] URL: {cleaned}")

        def job(progress, log):
            return downloader.download_video(
                cleaned,
                out,
                quality,
                cookies,
                cookies_file=cookies_file,
                log=log,
            )

        def done(result):
            files = result.get("files") or []
            strategy = result.get("strategy", "")
            platform_name = result.get("platform", platform)

            self.status("Tải video xong.")
            message = (
                f"Đã tải từ {platform_name}.\n"
                f"Cách tải: {strategy}\n"
                f"Lưu tại: {result.get('output_dir', out)}"
            )
            if files:
                message += "\n\nFile:\n" + "\n".join(files[:8])

            QMessageBox.information(self, "Downloader", message)

        self.run_worker("Đang tải video...", job, done)


    # ==================================================================
    # AI PROVIDER TEST
    # ==================================================================
    def test_ai_provider(self):
        config = self.current_ai_config()

        if not config.api_key:
            QMessageBox.warning(
                self,
                "AI Provider",
                f"Chưa nhập API key cho {config.provider}.",
            )
            return

        def job(progress, log):
            if config.provider != "Google Gemini":
                endpoint = ai.chat_endpoint(config.base_url)
                log(f"[AI] Provider: {config.provider}")
                log(f"[AI] POST {endpoint}")
                log(f"[AI] Model: {config.model}")
            return ai.test(config, log=log)

        def done(text):
            self._stash_provider_fields()
            self.settings.set_provider_api_key(
                config.provider,
                config.api_key,
            )
            self.status(f"{config.provider} OK.")
            QMessageBox.information(
                self,
                "AI Provider",
                f"Kết nối {config.provider} thành công.\n"
                f"Model: {config.model}\n"
                f"Response: {text}",
            )

        self.run_worker(
            f"Đang test {config.provider}...",
            job,
            done,
        )


_FAULT_HANDLE = None


def install_crash_logging():
    global _FAULT_HANDLE
    try:
        log_dir = ROOT / "logs"
        log_dir.mkdir(parents=True, exist_ok=True)
        crash_path = log_dir / "crash.log"
        _FAULT_HANDLE = open(crash_path, "a", encoding="utf-8", buffering=1)
        _FAULT_HANDLE.write(
            "\n\n===== START " + datetime.datetime.now().isoformat() + f" | {VERSION} =====\n"
        )
        faulthandler.enable(_FAULT_HANDLE, all_threads=True)

        old_hook = sys.excepthook
        def hook(exc_type, exc_value, exc_tb):
            try:
                _FAULT_HANDLE.write("\n[UNHANDLED PYTHON EXCEPTION]\n")
                traceback.print_exception(exc_type, exc_value, exc_tb, file=_FAULT_HANDLE)
                _FAULT_HANDLE.flush()
            except Exception:
                pass
            old_hook(exc_type, exc_value, exc_tb)
        sys.excepthook = hook
    except Exception:
        pass


def main():
    install_crash_logging()
    app = QApplication(sys.argv)
    app.setApplicationName(APP_NAME)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
