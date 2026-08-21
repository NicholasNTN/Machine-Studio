from __future__ import annotations

from dataclasses import asdict, dataclass
from math import cos, radians, sin
from uuid import uuid4

from editor.canvas import CanvasRect, calculate_media_rect


@dataclass(frozen=True)
class BlurZone:
    """A blur rectangle stored in normalized source-video coordinates."""
    id: str
    coordinate_space: str = "source_video"
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 0.2

    def to_dict(self): return asdict(self)

    @classmethod
    def from_dict(cls, value):
        data = dict(value or {})
        if "width" in data or "height" in data:
            x, y = float(data.get("x", 0)), float(data.get("y", 0))
            width, height = float(data.get("width", 1)), float(data.get("height", .2))
        else:
            x, y = float(data.get("x", 0)) / 100, float(data.get("y", 0)) / 100
            width, height = float(data.get("w", 100)) / 100, float(data.get("h", 20)) / 100
        x = max(0.0, min(1.0, x)); y = max(0.0, min(1.0, y))
        width = max(0.001, min(1.0 - x, width)); height = max(0.001, min(1.0 - y, height))
        return cls(str(data.get("id") or uuid4().hex), "source_video", x, y, width, height)


def source_zone_canvas_rect(zone, source_width, source_height, canvas_width, canvas_height, transform=None):
    """Map a source-normalized zone through Fit/Fill and VideoTransform."""
    z = zone if isinstance(zone, BlurZone) else BlurZone.from_dict(zone)
    t = dict(transform or {})
    media = calculate_media_rect(source_width, source_height, canvas_width, canvas_height, t.get("fit_mode", "fit"))
    sx = max(.01, float(t.get("scale_x", 100)) / 100); sy = max(.01, float(t.get("scale_y", 100)) / 100)
    width, height = media.width * sx, media.height * sy
    left = (canvas_width - width) * float(t.get("position_x", 50)) / 100
    top = (canvas_height - height) * float(t.get("position_y", 50)) / 100
    zx = 1 - z.x - z.width if t.get("flip_horizontal") else z.x
    zy = 1 - z.y - z.height if t.get("flip_vertical") else z.y
    points = [(left + width*zx, top + height*zy), (left + width*(zx+z.width), top + height*zy),
              (left + width*(zx+z.width), top + height*(zy+z.height)), (left + width*zx, top + height*(zy+z.height))]
    angle = radians(float(t.get("rotation", 0) or 0)); cx, cy = left + width/2, top + height/2
    if abs(angle) > 1e-9:
        c, s = cos(angle), sin(angle)
        points = [(cx+(px-cx)*c-(py-cy)*s, cy+(px-cx)*s+(py-cy)*c) for px, py in points]
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    x0, y0 = max(0.0, min(xs)), max(0.0, min(ys)); x1, y1 = min(float(canvas_width), max(xs)), min(float(canvas_height), max(ys))
    return CanvasRect(x0, y0, max(0.0, x1-x0), max(0.0, y1-y0))
