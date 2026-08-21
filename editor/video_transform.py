from __future__ import annotations

from dataclasses import asdict, dataclass


@dataclass
class VideoTransform:
    position_x: float = 50.0
    position_y: float = 50.0
    scale_x: float = 100.0
    scale_y: float = 100.0
    uniform_scale: bool = True
    rotation: float = 0.0
    opacity: float = 100.0
    fit_mode: str = "fit"
    flip_horizontal: bool = False
    flip_vertical: bool = False

    def to_dict(self): return asdict(self)

    @classmethod
    def from_dict(cls, data):
        allowed = cls.__dataclass_fields__
        return cls(**{key: value for key, value in dict(data or {}).items() if key in allowed})
