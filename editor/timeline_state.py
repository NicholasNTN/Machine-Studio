from __future__ import annotations

from dataclasses import dataclass, field

from core import editor_engine
from .track import Track, default_tracks


@dataclass
class TimelineState:
    clips: list[dict] = field(default_factory=list)
    layers: list[dict] = field(default_factory=list)
    tracks: list[Track] = field(default_factory=default_tracks)
    playhead_seconds: float = 0.0
    frame_rate: float = 30.0

    @property
    def duration(self) -> float:
        return editor_engine.total_duration(self.clips)

    def set_playhead(self, seconds: float) -> float:
        self.playhead_seconds = max(0.0, min(float(seconds or 0.0), self.duration))
        return self.playhead_seconds

    def to_dict(self) -> dict:
        return {
            "clips": [dict(item) for item in self.clips],
            "layers": [dict(item) for item in self.layers],
            "tracks": [track.to_dict() for track in self.tracks],
            "playhead_seconds": self.playhead_seconds,
            "frame_rate": self.frame_rate,
        }
