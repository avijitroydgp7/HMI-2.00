# tools/image.py
# Helper utilities for the image tool.

"""Helper utilities for the image tool."""

import copy
from typing import Optional, Dict

from PyQt6.QtGui import QImage
from PyQt6.QtWidgets import QFileDialog

DEFAULT_PROPERTIES = {
    "path": "",
    "size": {"width": 100, "height": 100},
}


def get_default_properties(path: str = "") -> Dict:
    """Return image properties for ``path`` or the stored defaults if empty."""
    if path:
        image = QImage(path)
        if image.isNull():
            width = DEFAULT_PROPERTIES["size"]["width"]
            height = DEFAULT_PROPERTIES["size"]["height"]
        else:
            width = image.width()
            height = image.height()
        return {
            "path": path,
            "size": {"width": width, "height": height},
        }
    return copy.deepcopy(DEFAULT_PROPERTIES)


def set_default_properties(props: Dict):
    """Update the default image properties."""
    global DEFAULT_PROPERTIES
    DEFAULT_PROPERTIES = copy.deepcopy(props)


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