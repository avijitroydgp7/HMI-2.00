# tools/polygon.py
# Defines default properties for a polygon component.


def get_default_properties():
    """Returns a dictionary containing the default properties for a new polygon."""
    return {
        "points": [
            {"x": 0, "y": 0},
            {"x": 100, "y": 0},
            {"x": 50, "y": 50}
        ],
        "fill_color": "#ffffff",
        "stroke_color": "#000000",
        "stroke_width": 1,
        "stroke_style": "solid"
    }