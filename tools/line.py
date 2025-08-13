# tools/line.py
# Defines default properties for a line component.


def get_default_properties():
    """Returns a dictionary containing the default properties for a new line."""
    return {
        "start": {"x": 0, "y": 0},
        "end": {"x": 100, "y": 0},
        "color": "#000000",
        "width": 2,
        "style": "solid"
    }