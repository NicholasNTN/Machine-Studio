from __future__ import annotations

from dataclasses import dataclass


@dataclass
class PreviewState:
    media_path: str = ""
    position_ms: int = 0
    zoom_percent: int = 100
    fit_mode: str = "Fit"
    aspect_ratio: str = "Original"


class PreviewService:
    """Keeps lightweight preview state separate from render jobs."""

    ZOOM_LEVELS = (50, 75, 100, 125, 150, 200, 300)

    def __init__(self):
        self.state = PreviewState()

    def set_zoom(self, percent: int) -> int:
        self.state.zoom_percent = min(self.ZOOM_LEVELS, key=lambda item: abs(item - int(percent)))
        return self.state.zoom_percent
