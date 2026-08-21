from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class TextStyle:
    preset: str = "Documentary Clean"
    font_name: str = "Arial"
    font_size: int = 52
    color: str = "#FFFFFF"
    outline_width: float = 2.0
    outline_color: str = "#000000"
    bold: bool = True
    italic: bool = False
    background_box: bool = False
    background_color: str = "#000000"
    background_opacity: int = 65
    uppercase: bool = False
    shadow: float = 1.0
    width: float = 80.0
    alignment: str = "Center"
    animation: str = "Không"
    animation_duration_ms: int = 220
    animation_strength: int = 100
    scale: float = 100.0
    rotation: float = 0.0
    opacity: int = 100

    def to_dict(self): return asdict(self)

    @classmethod
    def from_dict(cls, value):
        data = dict(value or {})
        return cls(**{key: data[key] for key in cls.__dataclass_fields__ if key in data})

    @classmethod
    def from_subtitle_preset(cls, preset):
        return cls(
            preset=str(getattr(preset, "preset_name", "Documentary Clean")), font_name=str(getattr(preset, "font_name", "Arial")),
            font_size=int(getattr(preset, "font_size", 52)), color=str(getattr(preset, "primary_color", "#FFFFFF")),
            outline_width=float(getattr(preset, "outline", 2.0)), outline_color=str(getattr(preset, "outline_color", "#000000")),
            bold=bool(getattr(preset, "bold", True)), italic=bool(getattr(preset, "italic", False)),
            background_box=bool(getattr(preset, "background_box", False)), background_color=str(getattr(preset, "background_color", "#000000")),
            background_opacity=int(getattr(preset, "background_opacity", 65)), uppercase=bool(getattr(preset, "uppercase", False)),
            shadow=float(getattr(preset, "shadow", 1.0)), width=float(getattr(preset, "width_percent", 80)),
            animation=str(getattr(preset, "animation", "Không")), animation_duration_ms=int(getattr(preset, "animation_duration_ms", 220)),
            animation_strength=int(getattr(preset, "animation_strength", 100)),
        )
