import os
import sys

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from services.command_history_service import CommandHistoryService
from services.commands import Command


class FaultyRedoCommand(Command):
    def redo(self):
        raise Exception("redo fail")

    def undo(self):
        pass

    def _notify(self):
        pass


def test_add_command_redo_failure(capsys):
    history = CommandHistoryService()
    cmd = FaultyRedoCommand()
    history.add_command(cmd)
    out, _ = capsys.readouterr()
    assert "redo fail" in out
    assert len(history._undo_stack) == 0
    assert len(history._redo_stack) == 0


class FaultyUndoCommand(Command):
    def redo(self):
        pass

    def undo(self):
        raise Exception("undo fail")

    def _notify(self):
        pass


def test_undo_failure(capsys):
    history = CommandHistoryService()
    cmd = FaultyUndoCommand()
    history.add_command(cmd)
    assert len(history._undo_stack) == 1
    history.undo()
    out, _ = capsys.readouterr()
    assert "undo fail" in out
    assert len(history._undo_stack) == 1
    assert len(history._redo_stack) == 0


class RedoFailAfterUndoCommand(Command):
    def __init__(self):
        self.times_redone = 0

    def redo(self):
        self.times_redone += 1
        if self.times_redone > 1:
            raise Exception("redo fail")

    def undo(self):
        pass

    def _notify(self):
        pass


def test_redo_failure(capsys):
    history = CommandHistoryService()
    cmd = RedoFailAfterUndoCommand()
    history.add_command(cmd)
    history.undo()
    assert len(history._redo_stack) == 1
    history.redo()
    out, _ = capsys.readouterr()
    assert "redo fail" in out
    assert len(history._redo_stack) == 1
    assert len(history._undo_stack) == 0


class NotifyFailCommand(Command):
    def redo(self):
        pass

    def undo(self):
        pass

    def _notify(self):
        raise Exception("notify fail")


def test_notify_failure_add(capsys):
    history = CommandHistoryService()
    cmd = NotifyFailCommand()
    history.add_command(cmd)
    out, _ = capsys.readouterr()
    assert "notify fail" in out
    assert len(history._undo_stack) == 1