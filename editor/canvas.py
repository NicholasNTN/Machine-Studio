from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CanvasRect:
    x: float
    y: float
    width: float
    height: float


def output_canvas_size(canvas_width, canvas_height, requested_width=None, requested_height=None):
    """Choose even output dimensions while preserving the authoritative canvas aspect."""
    cw, ch = max(2, int(canvas_width)), max(2, int(canvas_height))
    if requested_width and requested_height:
        long_edge = max(2, int(requested_width), int(requested_height))
        aspect = cw / ch
        if aspect >= 1.0:
            width, height = long_edge, round(long_edge / aspect)
        else:
            width, height = round(long_edge * aspect), long_edge
    else:
        width, height = cw, ch
    width -= width % 2; height -= height % 2
    return max(2, width), max(2, height)


def calculate_media_rect(source_width, source_height, canvas_width, canvas_height, mode="fit"):
    """Return centered source geometry in project-canvas coordinates."""
    sw, sh = max(1.0, float(source_width)), max(1.0, float(source_height))
    cw, ch = max(1.0, float(canvas_width)), max(1.0, float(canvas_height))
    scale = (max if str(mode).lower() == "fill" else min)(cw / sw, ch / sh)
    width, height = sw * scale, sh * scale
    return CanvasRect((cw - width) / 2.0, (ch - height) / 2.0, width, height)


def calculate_video_layout(source_width, source_height, canvas_width, canvas_height, transform=None):
    """Canonical displayed main-video rect in project-canvas coordinates."""
    t = dict(transform or {})
    media = calculate_media_rect(
        source_width, source_height, canvas_width, canvas_height, t.get("fit_mode", "fit"),
    )
    sx = max(.01, float(t.get("scale_x", 100)) / 100)
    sy = max(.01, float(t.get("scale_y", 100)) / 100)
    width, height = media.width * sx, media.height * sy
    left = (float(canvas_width) - width) * float(t.get("position_x", 50)) / 100
    top = (float(canvas_height) - height) * float(t.get("position_y", 50)) / 100
    return CanvasRect(left, top, width, height)


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
