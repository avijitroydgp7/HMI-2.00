# tools/image.py
# Helper utilities for the image tool.

from PyQt6.QtGui import QImage


def get_default_properties(path: str) -> dict:
    """Return image properties derived from the file at ``path``.

    Parameters
    ----------
    path: str
        The filesystem path to the image file.
    """
    image = QImage(path)
    if image.isNull():
        width = 100
        height = 100
    else:
        width = image.width()
        height = image.height()
    return {
        "path": path,
        "size": {"width": width, "height": height},
    }