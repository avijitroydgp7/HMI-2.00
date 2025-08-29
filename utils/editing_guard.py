"""Qt editing guard utility with explicit begin/end methods.

Provides a small helper to guard programmatic updates and collapse
intermediate UI refreshes into a single, final notification.
"""

from __future__ import annotations

from typing import Callable, Optional, List

from PyQt6.QtCore import QTimer
from PyQt6.QtCore import QObject
from PyQt6.QtCore import QSignalBlocker


class EditingGuard:
    """
    Guard for batch edits that should suppress cascaded updates.

    Usage:
        guard = EditingGuard(owner, screen_service, emit_final=callback).begin()
        # ... perform updates ...
        guard.mark_changed()
        guard.end()

    - While active, sets `owner._is_editing = True`.
    - Blocks signals on `screen_service` and (optionally) an active widget.
    - On `end()`, unblocks signals, and if any changes were marked,
      invokes `emit_final` while still guarded; then clears the guard on
      the next event-loop tick.
    """

    def __init__(
        self,
        owner: QObject,
        screen_service: QObject,
        active_widget: Optional[QObject] = None,
        emit_final: Optional[Callable[[], None]] = None,
    ):
        self._owner = owner
        self._screen_service = screen_service
        self._active_widget = active_widget
        self._emit_final = emit_final
        self._blockers: List[QSignalBlocker] = []
        self._changed = False
        self._begun = False

    def begin(self) -> "EditingGuard":
        if self._begun:
            return self
        # Mark editing
        try:
            setattr(self._owner, "_is_editing", True)
        except Exception:
            pass
        # Block global service signals
        try:
            self._blockers.append(QSignalBlocker(self._screen_service))
        except Exception:
            pass
        # Optionally block active widget
        if self._active_widget is not None:
            try:
                self._blockers.append(QSignalBlocker(self._active_widget))
            except Exception:
                pass
        self._begun = True
        return self

    def mark_changed(self) -> None:
        self._changed = True

    def end(self) -> None:
        if not self._begun:
            return

        def _finalize_post_update():
            # Unblock first so emissions propagate
            for blocker in self._blockers:
                try:
                    blocker.unblock()
                except Exception:
                    pass
            self._blockers.clear()
            # Emit final consolidated notification while still guarded
            try:
                if self._changed and self._emit_final is not None:
                    self._emit_final()
            finally:
                # Clear the guard on the next turn
                QTimer.singleShot(0, lambda: setattr(self._owner, "_is_editing", False))

        QTimer.singleShot(0, _finalize_post_update)

