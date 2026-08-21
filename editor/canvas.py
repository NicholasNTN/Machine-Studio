from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CanvasRect:
    x: float
    y: float
    width: float
    height: float


def calculate_media_rect(source_width, source_height, canvas_width, canvas_height, mode="fit"):
    """Return centered source geometry in project-canvas coordinates."""
    sw, sh = max(1.0, float(source_width)), max(1.0, float(source_height))
    cw, ch = max(1.0, float(canvas_width)), max(1.0, float(canvas_height))
    scale = (max if str(mode).lower() == "fill" else min)(cw / sw, ch / sh)
    width, height = sw * scale, sh * scale
    return CanvasRect((cw - width) / 2.0, (ch - height) / 2.0, width, height)


def calculate_fit_rect(source_width, source_height, canvas_width, canvas_height):
    return calculate_media_rect(source_width, source_height, canvas_width, canvas_height, "fit")


def calculate_fill_rect(source_width, source_height, canvas_width, canvas_height):
    return calculate_media_rect(source_width, source_height, canvas_width, canvas_height, "fill")


@dataclass
class CanvasBackground:
    mode: str = "none"
    image_path: str = ""
    image_fit: str = "cover"
    color: str = "#000000"
    opacity: int = 100
    blur_strength: int = 24
    brightness: int = -15

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, data):
        allowed = cls.__dataclass_fields__
        return cls(**{key: value for key, value in dict(data or {}).items() if key in allowed})
