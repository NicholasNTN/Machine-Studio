"""Editor-domain foundations for Machine Studio."""

from .document import EditorDocument
from .selection_manager import SelectionManager, SelectionRef
from .timeline_state import TimelineState

__all__ = ["EditorDocument", "SelectionManager", "SelectionRef", "TimelineState"]
