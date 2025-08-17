# tools/text.py
"""Default properties for the text tool."""

import copy

DEFAULT_PROPERTIES = {
    "content": "Text",
    "font": {
        "family": "Arial",
        "size": 14,
        "bold": False,
        "italic": False,
    },
    "color": "#000000",
}


def get_default_properties():
    """Return a copy of the default text properties."""
    return copy.deepcopy(DEFAULT_PROPERTIES)


def set_default_properties(props):
    """Update the default properties for text items."""
    global DEFAULT_PROPERTIES
    DEFAULT_PROPERTIES = copy.deepcopy(props)