# services/command_history_service.py
# Manages the undo/redo stacks for the application.

from PyQt6.QtCore import QObject, pyqtSignal
from collections import deque
import logging
from .commands import Command
from .project_service import project_service  # Safe: project_service only imports this module at runtime inside a method

logger = logging.getLogger(__name__)
# Avoid emitting logs unless the app configures handlers.
if not logger.handlers:
    logger.addHandler(logging.NullHandler())
logger.setLevel(logging.WARNING)

class CommandHistoryService(QObject):
    """
    A service that manages the undo and redo stacks for the application,
    allowing actions to be reversed and re-applied.
    """
    history_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._undo_stack = deque(maxlen=100)
        self._redo_stack = deque(maxlen=100)

    def _execute(self, command: Command, action: str) -> bool:
        """
        Executes the given action ("undo"/"redo") on the command and then
        calls its notify().

        - Returns True if the action executes successfully.
        - Returns False if action execution raises; _notify is skipped then.
        - Any exceptions from _notify are logged but do not fail the action.
        """
        try:
            getattr(command, action)()
        except Exception as e:
            logger.exception("Command %s failed: %s", action, e)
            return False

        try:
            command.notify()
        except Exception as e:
            logger.exception("Command notify failed after %s: %s", action, e)
        return True

    def add_command(self, command: Command):
        """
        Adds a new command to the history, executing it and clearing the redo stack.
        """
        if not self._execute(command, "redo"):
            return

        self._undo_stack.append(command)
        self._redo_stack.clear()
        
        self.history_changed.emit()
        project_service.set_dirty(True)

    def undo(self):
        """
        Pops a command from the undo stack, executes its undo method,
        and pushes it to the redo stack.
        """
        if self.can_undo():
            command = self._undo_stack[-1]
            if not self._execute(command, "undo"):
                return

            self._undo_stack.pop()
            self._redo_stack.append(command)
            self.history_changed.emit()
            project_service.set_dirty(True)

    def redo(self):
        """
        Pops a command from the redo stack, executes its redo method,
        and pushes it back to the undo stack.
        """
        if self.can_redo():
            command = self._redo_stack[-1]
            if not self._execute(command, "redo"):
                return

            self._redo_stack.pop()
            self._undo_stack.append(command)
            self.history_changed.emit()
            project_service.set_dirty(True)

    def can_undo(self):
        """Returns True if there are commands on the undo stack."""
        return bool(self._undo_stack)

    def can_redo(self):
        """Returns True if there are commands on the redo stack."""
        return bool(self._redo_stack)

    def clear(self):
        """Clears both the undo and redo stacks."""
        self._undo_stack.clear()
        self._redo_stack.clear()
        self.history_changed.emit()

command_history_service = CommandHistoryService()
