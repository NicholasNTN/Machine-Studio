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
