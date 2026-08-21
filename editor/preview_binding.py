from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PreviewBinding:
    source: str | None
    duration: float
    playhead: float
    playing: bool


def binding_after_clip_change(clips, current: PreviewBinding) -> PreviewBinding:
    if not clips:
        return PreviewBinding(None, 0.0, 0.0, False)
    return current
