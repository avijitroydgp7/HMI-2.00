# tools/image.py
# Helper utilities for the image tool.

from typing import Optional, Dict

from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QFileDialog


def get_default_properties(path: str) -> Dict:
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


def prompt_for_image(parent=None) -> Optional[Dict]:
    """Prompt the user to choose an image file and return its properties.

    Parameters
    ----------
    parent: QWidget, optional
        Parent widget for the dialog.

    Returns
    -------
    Optional[Dict]
        Default properties for the selected image or ``None`` if cancelled.
    """
    file_path, _ = QFileDialog.getOpenFileName(
        parent,
        "Select Image",
        "",
        "Images (*.jpg *.jpeg *.png *.svg)",
    )
    if not file_path:
        return None
    return get_default_properties(file_path)