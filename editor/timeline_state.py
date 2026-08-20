from __future__ import annotations

from dataclasses import dataclass, field

from core import editor_engine
from .track import Track, default_tracks
from .timeline_item import TimelineItem, TimelineItemKind


@dataclass
class TimelineState:
    clips: list[dict] = field(default_factory=list)
    layers: list[dict] = field(default_factory=list)
    tracks: list[Track] = field(default_factory=default_tracks)
    items: list[TimelineItem] = field(default_factory=list)
    supplemental_items: list[TimelineItem] = field(default_factory=list)
    playhead_seconds: float = 0.0
    frame_rate: float = 30.0

    @property
    def duration(self) -> float:
        video_baseline = editor_engine.total_duration(self.clips)
        latest_item_end = max((float(item.end) for item in self.items), default=0.0)
        return max(video_baseline, latest_item_end)

    def track_for_kind(self, kind: TimelineItemKind) -> Track:
        role = {
            TimelineItemKind.TEXT: "text",
            TimelineItemKind.SUBTITLE: "subtitle",
            TimelineItemKind.EFFECT: "effect",
            TimelineItemKind.BLUR: "effect",
            TimelineItemKind.VIDEO: "video",
            TimelineItemKind.AUDIO: "audio",
            TimelineItemKind.IMAGE: "text",
            TimelineItemKind.LOGO: "text",
        }[kind]
        return next(track for track in self.tracks if track.kind.value == role)

    def rebuild_items_from_legacy(self) -> None:
        """Bridge old dictionaries into canonical, stable timeline items."""
        previous = {item.id: item for item in self.items}
        rebuilt: list[TimelineItem] = []
        cursor = 0.0
        for clip in self.clips:
            duration = editor_engine.clip_duration(clip)
            item_id = str(clip.get("id") or "")
            track = self.track_for_kind(TimelineItemKind.VIDEO)
            item = TimelineItem(
                id=item_id,
                kind=TimelineItemKind.VIDEO,
                track_id=track.id,
                start=cursor,
                end=cursor + duration,
                source_ref=str(clip.get("path", "")),
                locked=bool(clip.get("locked", False)),
                visible=bool(clip.get("enabled", True)),
                muted=bool(clip.get("muted", False)),
                metadata=clip,
            )
            if item.id:
                rebuilt.append(item)
            cursor += duration

        for layer in self.layers:
            raw_kind = str(layer.get("type", "effect") or "effect").lower()
            if raw_kind == "blur_zone":
                raw_kind = "blur"
            try:
                kind = TimelineItemKind(raw_kind)
            except ValueError:
                kind = TimelineItemKind.EFFECT
            item_id = str(layer.get("id") or "")
            track = self.track_for_kind(kind)
            group_id = str(layer.get("group_id", "") or "")
            old = previous.get(item_id)
            rebuilt.append(TimelineItem(
                id=item_id,
                kind=kind,
                track_id=track.id,
                start=max(0.0, float(layer.get("start", 0.0) or 0.0)),
                end=max(0.0, float(layer.get("end", video_baseline(self.clips)) or 0.0)),
                group_id=group_id,
                source_ref=str(layer.get("path", "")),
                locked=bool(layer.get("locked", old.locked if old else False)),
                visible=bool(layer.get("enabled", True)),
                muted=bool(layer.get("muted", False)),
                metadata=layer,
            ))
        self.items[:] = [item for item in rebuilt if item.id] + list(self.supplemental_items)
        self.synchronize_tracks()

    def set_supplemental_items(self, items: list[TimelineItem]) -> None:
        self.supplemental_items[:] = items
        self.rebuild_items_from_legacy()

    def synchronize_tracks(self) -> None:
        by_track = {track.id: [] for track in self.tracks}
        for item in self.items:
            by_track.setdefault(item.track_id, []).append(item.id)
        for track in self.tracks:
            track.item_ids[:] = by_track.get(track.id, [])

    def restore_tracks(self, values: list[dict]) -> None:
        if values:
            self.tracks[:] = [Track.from_dict(value) for value in values]
            self.rebuild_items_from_legacy()

    def set_playhead(self, seconds: float) -> float:
        self.playhead_seconds = max(0.0, min(float(seconds or 0.0), self.duration))
        return self.playhead_seconds

    def to_dict(self) -> dict:
        return {
            "clips": [dict(item) for item in self.clips],
            "layers": [dict(item) for item in self.layers],
            "tracks": [track.to_dict() for track in self.tracks],
            "items": [item.to_dict() for item in self.items],
            "playhead_seconds": self.playhead_seconds,
            "frame_rate": self.frame_rate,
        }


def video_baseline(clips: list[dict]) -> float:
    return editor_engine.total_duration(clips)
