"""Default properties for the line drawing tool."""

import copy

DEFAULT_PROPERTIES = {
    "start": {"x": 0, "y": 0},
    "end": {"x": 100, "y": 0},
    "color": "#000000",
    "width": 2,
    "style": "solid",
}


def get_default_properties():
    """Return a copy of the default line properties."""
    return copy.deepcopy(DEFAULT_PROPERTIES)


def set_default_properties(props):
    """Update the default properties for lines."""
    global DEFAULT_PROPERTIES
    DEFAULT_PROPERTIES = copy.deepcopy(props)