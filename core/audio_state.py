from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path


@dataclass(frozen=True)
class AudioState:
    original_audio_muted: bool = False
    original_audio_volume: float = 1.0
    narration_muted: bool = False
    narration_volume: float = 1.0
    music_muted: bool = False
    music_volume: float = 0.3


@dataclass(frozen=True)
class NarrationReplacement:
    source: str
    state: AudioState


def replace_narration_source(state: AudioState, source: str) -> NarrationReplacement:
    """Describe source replacement without mutating any user mixer choice."""
    return NarrationReplacement(str(source or ""), replace(state))


def audio_source_is_loadable(source: str) -> bool:
    path = Path(str(source or ""))
    return path.is_file() and path.stat().st_size > 0
