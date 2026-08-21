from __future__ import annotations

from dataclasses import dataclass, field, asdict
from pathlib import Path
import json


@dataclass
class Scene:
    index: int
    start: float
    end: float
    frame_path: str
    visual: str = ""
    chinese_text: str = ""
    source_meaning: str = ""
    en_voice: str = ""
    vi_voice: str = ""

    # Exact TTS timing after voice generation. Subtitle uses these values.
    voice_start: float = 0.0
    voice_end: float = 0.0
    voice_file: str = ""
    voice_role: str = "single"
    voice_role_locked: bool = False
    voice_role_confidence: float = 0.0

    @property
    def duration(self) -> float:
        return max(0.1, self.end - self.start)


@dataclass
class AIProject:
    video_path: str = ""
    duration: float = 0.0
    interval: float = 6.0
    workspace: str = ""
    source_audio: str = ""
    transcript: str = ""
    analysis_summary: str = ""
    topic: str = ""
    narration_path: str = ""
    subtitle_path: str = ""
    voice_manifest_path: str = ""
    processed_preview_path: str = ""
    export_state: dict = field(default_factory=dict)
    scenes: list[Scene] = field(default_factory=list)
    active_sequence_id: str = ""
    sequences: list[dict] = field(default_factory=list)
    media_library: list[str] = field(default_factory=list)
    media_display_names: dict[str, str] = field(default_factory=dict)

    def save(self, path: str | Path):
        Path(path).write_text(
            json.dumps(asdict(self), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    @classmethod
    def load(cls, path: str | Path) -> "AIProject":
        raw = json.loads(Path(path).read_text(encoding="utf-8"))
        scenes = [Scene(**x) for x in raw.pop("scenes", [])]
        obj = cls(**raw)
        obj.scenes = scenes
        return obj


@dataclass
class SubtitleStyle:
    preset_name: str = "Documentary Clean"
    font_name: str = "Arial"
    font_size: int = 48
    primary_color: str = "#FFFFFF"
    outline_color: str = "#000000"
    background_color: str = "#000000"
    bold: bool = True
    italic: bool = False
    outline: float = 3.0
    shadow: float = 1.0
    background_box: bool = False
    background_opacity: int = 65
    x_percent: int = 50
    y_percent: int = 86
    width_percent: int = 80
    max_chars_per_line: int = 34
    single_line_auto: bool = True
    # Kept for backward project compatibility; v1.0.2 no longer shrinks font per cue.
    min_font_size: int = 24
    auto_layout: bool = True
    inner_margin_percent: int = 5
    uppercase: bool = False

    # Subtitle motion/effect. These are rendered both in Live Preview
    # and final ASS/FFmpeg export.
    animation: str = "Không"
    animation_duration_ms: int = 220
    animation_strength: int = 100
    karaoke_color: str = "#FFE600"

    # Word-by-word caption effect.
    word_pop_scale: int = 108
    word_pop_ms: int = 110


@dataclass
class ExportOptions:
    resolution: str = "Original"
    fit_mode: str = "Fit"
    canvas_background_mode: str = "none"
    canvas_background_image: str = ""
    canvas_background_image_fit: str = "cover"
    canvas_background_color: str = "#000000"
    canvas_background_opacity: int = 100
    canvas_background_blur: int = 24
    canvas_background_brightness: int = -15
    video_transform: dict = field(default_factory=dict)
    codec: str = "H.264"
    encoder: str = "Auto (GPU)"

    # Video transformations
    speed: float = 1.0
    zoom: float = 1.0
    auto_zoom: bool = False
    auto_zoom_max: float = 1.10
    auto_zoom_cycle: float = 3.0
    mirror: bool = False
    border: int = 0
    brightness: float = 0.0
    contrast: float = 1.0
    saturation: float = 1.0
    sharpen: float = 0.0
    vignette: bool = False
    strip_metadata: bool = True

    # Subtitle
    burn_subtitle: bool = False
    subtitle_path: str = ""
    subtitle_style: SubtitleStyle = field(default_factory=SubtitleStyle)

    # Logo / overlays
    logo_path: str = ""
    logo_position: str = "Top-right"
    logo_scale: float = 0.12
    logo_x_percent: float = 88.0
    logo_y_percent: float = 10.0
    overlay_text: str = ""
    overlay_position: str = "Top-left"
    overlay_font_name: str = "Arial"
    overlay_font_size: int = 34
    overlay_color: str = "#FFFFFF"
    overlay_x_percent: float = 12.0
    overlay_y_percent: float = 8.0

    # Basic Editor extra layers (multiple text/image overlays).
    # Every layer can have its own start/end timeline.
    editor_layers: list[dict] = field(default_factory=list)

    # Blur regions. Values inside blur_zones are percentages:
    # {"x":0,"y":70,"w":100,"h":20}
    blur_enabled: bool = False
    blur_x: int = 0
    blur_y: int = 0
    blur_w: int = 0
    blur_h: int = 0
    blur_zones: list[dict] = field(default_factory=list)
    blur_style: str = "Đen mờ"
    blur_opacity: int = 20
    auto_cover_source_subtitle: bool = False
    auto_subtitle_zone: dict = field(default_factory=dict)

    # Logo extras
    logo_opacity: int = 100
    logo_remove_white_bg: bool = False

    # Audio mixer
    source_audio_mode: str = "Giữ âm gốc"
    source_volume: float = 1.0
    accompaniment_path: str = ""
    narration_path: str = ""
    narration_volume: float = 1.0
    narration_speed: float = 1.0
    background_music_path: str = ""
    background_music_volume: float = 0.08
    background_music_loop: bool = True
    duck_source_under_voice: bool = True
