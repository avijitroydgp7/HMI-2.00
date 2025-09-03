import sys
import traceback
from PyQt6.QtWidgets import QApplication, QMessageBox


class ExceptionSafeApplication(QApplication):
    """QApplication subclass that displays exceptions in a message box."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Handle exceptions that occur outside the Qt event loop
        sys.excepthook = self._handle_exception

    def notify(self, receiver, event):
        try:
            return super().notify(receiver, event)
        except Exception as exc:  # pylint: disable=broad-except
            self._handle_exception(type(exc), exc, exc.__traceback__)
            return False

    def _handle_exception(self, exc_type, exc_value, exc_traceback):
        """Show unhandled exceptions using a critical message box."""
        formatted = ''.join(
            traceback.format_exception(exc_type, exc_value, exc_traceback)
        )
        QMessageBox.critical(
            None,
            "Unhandled Exception",
            formatted,
        )
