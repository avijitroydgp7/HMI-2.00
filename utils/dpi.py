"""Utilities for scaling UI elements according to display DPI."""

from PyQt6.QtGui import QGuiApplication

_BASE_DPI = 96.0


def dpi_scale(value: float) -> int:
    """Return ``value`` scaled for the current screen's logical DPI."""
    screen = QGuiApplication.primaryScreen()
    dpi = screen.logicalDotsPerInch() if screen else _BASE_DPI
    return int(round(value * dpi / _BASE_DPI))

