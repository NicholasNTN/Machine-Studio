from __future__ import annotations

from dataclasses import asdict, dataclass
from math import cos, radians, sin
from uuid import uuid4

from editor.canvas import CanvasRect, calculate_video_layout


@dataclass(frozen=True)
class BlurZone:
    """A blur rectangle stored in normalized source-video coordinates."""
    id: str
    coordinate_space: str = "source_video"
    x: float = 0.0
    y: float = 0.0
    width: float = 1.0
    height: float = 0.2
    kind: str = "blur"
    source: str = "manual"
    style: str = ""
    strength: float = 20.0
    enabled: bool = True
    visible: bool = True
    confidence: float | None = None

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
        source = str(data.get("source") or ("auto_subtitle" if data.get("auto") else "manual"))
        confidence = data.get("confidence")
        try: confidence = None if confidence is None else float(confidence)
        except (TypeError, ValueError): confidence = None
        return cls(
            str(data.get("id") or uuid4().hex), "source_video", x, y, width, height,
            str(data.get("kind") or "blur"), source,
            str(data.get("style") or ""), float(data.get("strength", 20) or 20),
            bool(data.get("enabled", True)), bool(data.get("visible", True)), confidence,
        )


def normalize_blur_zones(zones, legacy_auto_zone=None):
    """Return one canonical collection while accepting pre-3D split projects."""
    result = []
    seen = set()
    candidates = list(zones or []) if isinstance(zones, list) else []
    if isinstance(legacy_auto_zone, dict) and legacy_auto_zone:
        candidates.append({**legacy_auto_zone, "source": "auto_subtitle", "auto": True})
    for value in candidates:
        if not isinstance(value, dict):
            continue
        try: zone = BlurZone.from_dict(value)
        except (TypeError, ValueError, OverflowError):
            continue
        if zone.id in seen:
            continue
        seen.add(zone.id)
        item = zone.to_dict()
        item["auto"] = zone.source == "auto_subtitle"
        result.append(item)
    return result


def source_zone_canvas_rect(zone, source_width, source_height, canvas_width, canvas_height, transform=None):
    """Map a source-normalized zone through Fit/Fill and VideoTransform."""
    z = zone if isinstance(zone, BlurZone) else BlurZone.from_dict(zone)
    t = dict(transform or {})
    video = calculate_video_layout(source_width, source_height, canvas_width, canvas_height, t)
    left, top, width, height = video.x, video.y, video.width, video.height
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


def resize_normalized_zone(zone: BlurZone, corner: str, dx: float, dy: float, minimum=.03) -> BlurZone:
    x, y, right, bottom = zone.x, zone.y, zone.x + zone.width, zone.y + zone.height
    if "left" in corner: x = min(right-minimum, max(0.0, x+dx))
    else: right = max(x+minimum, min(1.0, right+dx))
    if "top" in corner: y = min(bottom-minimum, max(0.0, y+dy))
    else: bottom = max(y+minimum, min(1.0, bottom+dy))
    return BlurZone(zone.id, zone.coordinate_space, x, y, right-x, bottom-y)
