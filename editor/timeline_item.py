from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4


class TimelineItemKind(str, Enum):
    VIDEO = "video"
    AUDIO = "audio"
    SUBTITLE = "subtitle"
    TEXT = "text"
    EFFECT = "effect"
    BLUR = "blur"
    IMAGE = "image"
    LOGO = "logo"


@dataclass
class TimelineItem:
    kind: TimelineItemKind
    track_id: str
    start: float
    end: float
    id: str = field(default_factory=lambda: uuid4().hex)
    group_id: str = ""
    source_ref: str = ""
    locked: bool = False
    visible: bool = True
    muted: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> float:
        return max(0.0, float(self.end) - float(self.start))

    def to_dict(self) -> dict:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "TimelineItem":
        values = dict(data or {})
        values["kind"] = TimelineItemKind(values.get("kind", "video"))
        return cls(**values)
