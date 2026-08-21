from __future__ import annotations

from copy import deepcopy
from dataclasses import asdict, dataclass, field
from pathlib import Path
import re

from core.models import ExportOptions, SubtitleStyle
from editor.blur_zone import normalize_blur_zones
from editor.canvas import CanvasBackground
from editor.sequence_manager import SequenceDocument
from editor.video_transform import VideoTransform


def _dict(value):
    return deepcopy(value) if isinstance(value, dict) else {}


def _list(value):
    return deepcopy(value) if isinstance(value, list) else []


def _text(value, fallback=""):
    return str(value).strip() if isinstance(value, (str, Path)) else fallback


def _number(value, fallback, low=None, high=None):
    try:
        result = float(value)
    except (TypeError, ValueError):
        result = float(fallback)
    if low is not None: result = max(low, result)
    if high is not None: result = min(high, result)
    return result


def snapshot_resolution(output: dict) -> str:
    resolution = _text(output.get("resolution"), "Original")
    aspect_text = _text(output.get("aspect_ratio"), "Original")
    dimensions = output.get("canvas_dimensions")
    if resolution == "Original" and aspect_text != "Original" and isinstance(dimensions, (list, tuple)) and len(dimensions) == 2:
        width = int(_number(dimensions[0], 0, 2)); height = int(_number(dimensions[1], 0, 2))
        width -= width % 2; height -= height % 2
        return f"{width}x{height}"
    if aspect_text == "Original" or ":" not in aspect_text:
        return resolution
    match = re.search(r"(\d+)\s*x\s*(\d+)", resolution, re.I)
    if not match:
        return resolution
    left, right = aspect_text.split(":", 1)
    try:
        aspect = float(left) / float(right)
    except (TypeError, ValueError, ZeroDivisionError):
        return resolution
    long_edge = max(int(match.group(1)), int(match.group(2)))
    if aspect >= 1.0:
        width, height = long_edge, round(long_edge / aspect)
    else:
        width, height = round(long_edge * aspect), long_edge
    width -= width % 2; height -= height % 2
    return f"{max(2, width)}x{max(2, height)}"


@dataclass(frozen=True)
class SnapshotValidation:
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


@dataclass(frozen=True)
class SequenceRenderSnapshot:
    sequence_id: str
    sequence_name: str
    duration: float
    clips: tuple[dict, ...]
    canvas: dict
    video_transform: dict
    audio: dict
    blur: dict
    subtitle: dict
    logo: dict
    overlay_text: dict
    layers: tuple[dict, ...]
    effects: dict
    output: dict
    legacy_fallbacks: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self):
        return asdict(self)

    def validate(self) -> SnapshotValidation:
        errors, warnings = [], []
        if not self.sequence_id: errors.append("Missing sequence id.")
        if self.output.get("editor_use_timeline") and not self.clips: errors.append("Sequence has no enabled video clips.")
        for clip in self.clips:
            if not Path(_text(clip.get("path"))).is_file():
                errors.append(f"Video clip is missing: {_text(clip.get('path'))}")
        canvas_mode = self.canvas.get("mode")
        if canvas_mode not in {"none", "blur", "solid", "image"}:
            errors.append(f"Invalid canvas background mode: {canvas_mode}")
        if canvas_mode == "image" and not Path(_text(self.canvas.get("image_path"))).is_file():
            errors.append("Canvas image background is enabled but its file is missing.")
        narration = self.audio.get("narration_path", "")
        if self.audio.get("narration_enabled") and not Path(_text(narration)).is_file():
            errors.append("Narration is enabled but its file is missing.")
        if self.logo.get("enabled") and not Path(_text(self.logo.get("path"))).is_file():
            errors.append("Logo is enabled but its file is missing.")
        if self.subtitle.get("enabled") and not Path(_text(self.subtitle.get("path"))).is_file():
            errors.append("Subtitle burn-in is enabled but its file is missing.")
        for layer in self.layers:
            if layer.get("enabled", True) and layer.get("type") in {"image", "video"}:
                path = _text(layer.get("path"))
                if not path or not Path(path).is_file():
                    warnings.append(f"Layer asset is missing: {layer.get('id', '<unknown>')} ({path})")
        return SnapshotValidation(tuple(errors), tuple(warnings))

    def export_options(self) -> ExportOptions:
        audio, blur, subtitle = self.audio, self.blur, self.subtitle
        logo, overlay, effects, output = self.logo, self.overlay_text, self.effects, self.output
        return ExportOptions(
            resolution=snapshot_resolution(output), fit_mode=_text(self.video_transform.get("fit_mode"), "Fit"),
            canvas_background_mode=_text(self.canvas.get("mode"), "none"),
            canvas_background_image=_text(self.canvas.get("image_path")),
            canvas_background_image_fit=_text(self.canvas.get("image_fit"), "cover"),
            canvas_background_color=_text(self.canvas.get("color"), "#000000"),
            canvas_background_opacity=int(_number(self.canvas.get("opacity"), 100, 0, 100)),
            canvas_background_blur=int(_number(self.canvas.get("blur_strength"), 24, 1, 80)),
            canvas_background_brightness=int(_number(self.canvas.get("brightness"), -15, -100, 100)),
            video_transform=deepcopy(self.video_transform), codec=_text(output.get("codec"), "H.264"),
            encoder=_text(output.get("encoder"), "Auto (GPU)"), speed=_number(effects.get("speed"), 1.0, 0.05, 8.0),
            zoom=_number(effects.get("zoom"), 1.0, 1.0, 2.0), auto_zoom=bool(effects.get("auto_zoom", False)),
            mirror=bool(effects.get("mirror", False)), border=int(_number(effects.get("border"), 0, 0, 100)),
            brightness=_number(effects.get("brightness"), 0, -1, 1), contrast=_number(effects.get("contrast"), 1, .1, 3),
            saturation=_number(effects.get("saturation"), 1, 0, 3), sharpen=_number(effects.get("sharpen"), 0, 0, 2),
            vignette=bool(effects.get("vignette", False)), strip_metadata=bool(output.get("strip_metadata", True)),
            burn_subtitle=bool(subtitle.get("enabled")), subtitle_path=_text(subtitle.get("path")),
            subtitle_style=SubtitleStyle(**{k: v for k, v in _dict(subtitle.get("style")).items() if k in SubtitleStyle.__dataclass_fields__}),
            logo_path=_text(logo.get("path")) if logo.get("enabled") else "", logo_position=_text(logo.get("position"), "Top-right"),
            logo_scale=_number(logo.get("scale"), 12, 1, 50) / 100.0, logo_x_percent=_number(logo.get("x"), 88, 1, 99),
            logo_y_percent=_number(logo.get("y"), 10, 1, 99), logo_opacity=int(_number(logo.get("opacity"), 100, 0, 100)),
            logo_remove_white_bg=bool(logo.get("remove_white_bg", False)),
            overlay_text=_text(overlay.get("text")) if overlay.get("enabled") else "",
            overlay_position=_text(overlay.get("position"), "Top-left"), overlay_font_name=_text(overlay.get("font"), "Arial"),
            overlay_font_size=int(_number(overlay.get("size"), 34, 6, 300)), overlay_color=_text(overlay.get("color"), "#FFFFFF"),
            overlay_x_percent=_number(overlay.get("x"), 12, 0, 100), overlay_y_percent=_number(overlay.get("y"), 8, 0, 100),
            editor_layers=[deepcopy(layer) for layer in self.layers], blur_enabled=bool(blur.get("enabled")),
            blur_zones=_list(blur.get("zones")), blur_style=_text(blur.get("style"), "Đen mờ"),
            blur_opacity=int(_number(blur.get("opacity"), 20, 0, 100)),
            auto_cover_source_subtitle=bool(blur.get("auto_cover_source_subtitle")),
            auto_subtitle_zone=_dict(blur.get("auto_subtitle_zone")), source_audio_mode=_text(audio.get("source_audio_mode"), "Giữ âm gốc"),
            source_volume=_number(audio.get("source_volume"), 1, 0, 2), accompaniment_path=_text(audio.get("accompaniment_path")),
            narration_path=_text(audio.get("narration_path")) if audio.get("narration_enabled") else "",
            narration_volume=_number(audio.get("narration_volume"), 1, 0, 1.5), narration_speed=1.0,
            background_music_path=_text(audio.get("music_path")), background_music_volume=_number(audio.get("music_volume"), 0, 0, 2),
            background_music_loop=bool(audio.get("music_loop", True)), duck_source_under_voice=True,
        )


def build_render_snapshot(sequences, sequence_id: str) -> SequenceRenderSnapshot:
    sequence = next((item for item in sequences if item.id == sequence_id), None)
    if not isinstance(sequence, SequenceDocument):
        raise KeyError(f"Unknown sequence id: {sequence_id}")
    state = _dict(sequence.state)
    fallbacks = []
    clips = tuple(deepcopy(item) for item in _list(state.get("editor_clips")) if isinstance(item, dict) and item.get("enabled", True))
    layers = tuple(deepcopy(item) for item in _list(state.get("editor_layers")) if isinstance(item, dict))
    canvas_raw = state.get("canvas_background")
    if not isinstance(canvas_raw, dict):
        fallbacks.append("canvas_background")
    canvas = CanvasBackground.from_dict(canvas_raw).to_dict()
    transform = VideoTransform.from_dict(clips[0].get("transform", {}) if clips else {}).to_dict()
    narration = _text(state.get("narration_path"))
    accompaniment = _text(state.get("accompaniment_path"))
    source_muted = bool(state.get("mute_original_voice", False))
    source_mode = "Chỉ nhạc nền đã tách" if source_muted and accompaniment else "Tắt toàn bộ âm gốc" if source_muted else "Giữ âm gốc"
    duration = sum(max(0.0, _number(c.get("source_end"), 0) - _number(c.get("source_start"), 0)) for c in clips)
    return SequenceRenderSnapshot(
        sequence.id, sequence.name, duration, clips, canvas, transform,
        {"source_audio_mode": source_mode, "source_muted": source_muted, "source_volume": _number(state.get("source_volume"), 100, 0, 200) / 100,
         "narration_path": narration, "narration_enabled": bool(narration), "narration_volume": _number(state.get("narration_volume"), 100, 0, 150) / 100,
         "accompaniment_path": accompaniment, "accompaniment_volume": _number(state.get("source_volume"), 100, 0, 200) / 100,
         "music_path": _text(state.get("music_file")), "music_volume": 0 if state.get("mute_music", False) else _number(state.get("music_volume"), 8, 0, 200) / 100,
         "music_loop": True},
        {"enabled": bool(state.get("blur_enabled", False)), "zones": normalize_blur_zones(state.get("blur_zones"), state.get("auto_subtitle_zone")),
         "style": _text(state.get("blur_style"), "Đen mờ"), "opacity": state.get("blur_opacity", 20),
         "auto_cover_source_subtitle": bool(state.get("auto_cover_source_subtitle", False)), "auto_subtitle_zone": _dict(state.get("auto_subtitle_zone"))},
        {"enabled": bool(state.get("sub_enabled", False)), "path": _text(state.get("subtitle_path")), "cues": _list(state.get("preview_cues")),
         "style": _dict(state.get("subtitle_style")), "editor_text": _text(state.get("subtitle_editor_text")), "groups": _dict(state.get("subtitle_groups"))},
        {"enabled": bool(state.get("logo_enabled", False)), "path": _text(state.get("logo_path")), "position": state.get("logo_position", "Top-right"),
         "scale": state.get("logo_scale", 12), "x": state.get("logo_x", 88), "y": state.get("logo_y", 10), "opacity": state.get("logo_opacity", 100),
         "remove_white_bg": bool(state.get("logo_remove_bg", False))},
        {"enabled": bool(state.get("overlay_enabled", False)), "text": _text(state.get("overlay_text")), "position": state.get("overlay_position", "Top-left"),
         "font": state.get("overlay_font", "Arial"), "size": state.get("overlay_size", 34), "color": state.get("overlay_color", "#FFFFFF"),
         "x": state.get("overlay_x", 12), "y": state.get("overlay_y", 8)},
        layers,
        {"speed": _number(state.get("play_speed"), 1) if state.get("speed_enabled", False) else 1.0, "zoom": 1.0, "auto_zoom": False,
         "mirror": False, "border": 0, "brightness": 0.0, "contrast": 1.0, "saturation": 1.0, "sharpen": 0.0, "vignette": False},
        {"resolution": _text(state.get("resolution"), "Original"), "aspect_ratio": _text(state.get("project_aspect_ratio"), "Original"),
         "canvas_dimensions": deepcopy(state.get("project_canvas_dimensions", [])),
         "editor_use_timeline": bool(state.get("editor_use_timeline", False)),
         "codec": _text(state.get("codec"), "H.264"), "encoder": _text(state.get("encoder"), "Auto (GPU)"), "strip_metadata": bool(state.get("strip_metadata", True))},
        tuple(fallbacks),
    )
