# services/command_history_service.py
# Manages the undo/redo stacks for the application.

from PyQt6.QtCore import QObject, pyqtSignal
from collections import deque
from .commands import Command

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

    def add_command(self, command: Command):
        """
        Adds a new command to the history, executing it and clearing the redo stack.
        """
        from .project_service import project_service
        
        command.redo()
        
        self._undo_stack.append(command)
        self._redo_stack.clear()
        
        # FIX: Notify the UI that the data has changed after the initial "do"
        command._notify()
        
        self.history_changed.emit()
        project_service.set_dirty(True)

    def undo(self):
        """
        Pops a command from the undo stack, executes its undo method,
        and pushes it to the redo stack.
        """
        from .project_service import project_service
        
        if self.can_undo():
            command = self._undo_stack.pop()
            command.undo()
            command._notify()
            self._redo_stack.append(command)
            self.history_changed.emit()
            project_service.set_dirty(True)

    def redo(self):
        """
        Pops a command from the redo stack, executes its redo method,
        and pushes it back to the undo stack.
        """
        from .project_service import project_service
        
        if self.can_redo():
            command = self._redo_stack.pop()
            command.redo()
            command._notify()
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
