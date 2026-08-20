from __future__ import annotations

from collections.abc import Callable

from PySide6.QtGui import QUndoCommand, QUndoStack


class CallbackCommand(QUndoCommand):
    """Small adapter used while legacy editor operations migrate to commands."""

    def __init__(self, text: str, redo: Callable[[], None], undo: Callable[[], None]):
        super().__init__(text)
        self._redo = redo
        self._undo = undo

    def redo(self) -> None:
        self._redo()

    def undo(self) -> None:
        self._undo()


class CommandManager:
    def __init__(self, parent=None):
        self.stack = QUndoStack(parent)

    def execute(self, command: QUndoCommand) -> None:
        self.stack.push(command)

    def clear(self) -> None:
        self.stack.clear()


class TimelineSnapshotCommand(QUndoCommand):
    """Undoable replacement of the legacy clip list during migration."""
    def __init__(self, text, before, after, apply_callback):
        super().__init__(text); self.before = [dict(item) for item in before]; self.after = [dict(item) for item in after]; self.apply_callback = apply_callback

    def undo(self): self.apply_callback(self.before)
    def redo(self): self.apply_callback(self.after)
