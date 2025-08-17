# tools/polygon.py
"""Default properties for the polygon tool."""

import copy

DEFAULT_PROPERTIES = {
    "points": [
        {"x": 0, "y": 0},
        {"x": 100, "y": 0},
        {"x": 50, "y": 50},
    ],
    "fill_color": "#ffffff",
    "stroke_color": "#000000",
    "stroke_width": 1,
    "stroke_style": "solid",
}


def get_default_properties():
    """Return a copy of the default polygon properties."""
    return copy.deepcopy(DEFAULT_PROPERTIES)


def set_default_properties(props):
    """Update the default properties for polygons."""
    global DEFAULT_PROPERTIES
    DEFAULT_PROPERTIES = copy.deepcopy(props)