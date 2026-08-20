from __future__ import annotations

from PySide6.QtCore import QObject, Signal
from .selection_ref import SelectionRef


class SelectionManager(QObject):
    """Single source of truth shared by timeline, preview, and inspector."""

    selectionChanged = Signal(object)

    def __init__(self, parent: QObject | None = None):
        super().__init__(parent)
        self._selection: SelectionRef | None = None

    @property
    def current(self) -> SelectionRef | None:
        return self._selection

    def select(self, kind: str, object_id: str, group_id: str = "") -> None:
        selection = SelectionRef(str(kind), str(object_id), str(group_id))
        if selection != self._selection:
            self._selection = selection
            self.selectionChanged.emit(selection)

    def clear(self) -> None:
        if self._selection is not None:
            self._selection = None
            self.selectionChanged.emit(None)
