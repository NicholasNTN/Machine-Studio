from __future__ import annotations

from PySide6.QtCore import QObject, Signal

from .command_manager import CommandManager
from .layer_manager import LayerManager
from .selection_manager import SelectionManager
from .snap_engine import SnapEngine
from .timeline_state import TimelineState


class EditorDocument(QObject):
    """Project-scoped editor state independent of any specific panel."""

    changed = Signal()
    durationChanged = Signal(float)
    playheadChanged = Signal(float)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self.timeline = TimelineState()
        self.selection = SelectionManager(self)
        self.commands = CommandManager(self)
        self.snap_engine = SnapEngine()
        self.layers = LayerManager(self.timeline.layers)
        self.panel_sizes: dict[str, list[int]] = {}
        self.aspect_ratio = "Original"

    @property
    def duration(self) -> float:
        return self.timeline.duration

    def set_playhead(self, seconds: float) -> None:
        value = self.timeline.set_playhead(seconds)
        self.playheadChanged.emit(value)

    def replace_legacy_state(self, clips: list[dict], layers: list[dict]) -> None:
        """Copy external state into document-owned lists (migration boundary only)."""
        before = self.duration
        self.timeline.clips[:] = clips
        self.timeline.layers[:] = layers
        self.layers.layers = self.timeline.layers
        self.timeline.rebuild_items_from_legacy()
        self.changed.emit()
        if abs(before - self.duration) > 0.0001:
            self.durationChanged.emit(self.duration)

    def synchronize_legacy_items(self) -> None:
        before = self.duration
        self.timeline.rebuild_items_from_legacy()
        self.changed.emit()
        if abs(before - self.duration) > 0.0001:
            self.durationChanged.emit(self.duration)
