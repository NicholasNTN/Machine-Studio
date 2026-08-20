from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum
from uuid import uuid4


class TrackKind(str, Enum):
    TEXT = "text"
    SUBTITLE = "subtitle"
    EFFECT = "effect"
    VIDEO = "video"
    AUDIO = "audio"


@dataclass
class Track:
    name: str
    kind: TrackKind
    id: str = field(default_factory=lambda: uuid4().hex)
    locked: bool = False
    visible: bool = True
    muted: bool = False
    item_ids: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        data = asdict(self)
        data["kind"] = self.kind.value
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Track":
        values = dict(data or {})
        values["kind"] = TrackKind(values.get("kind", TrackKind.VIDEO.value))
        return cls(**values)


def default_tracks() -> list[Track]:
    return [
        Track("Text", TrackKind.TEXT),
        Track("Subtitles", TrackKind.SUBTITLE),
        Track("Effects", TrackKind.EFFECT),
        Track("Video", TrackKind.VIDEO),
        Track("Audio / AI Voice", TrackKind.AUDIO),
    ]
