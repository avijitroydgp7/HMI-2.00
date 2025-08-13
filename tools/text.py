# tools/text.py
# Defines default properties for a text component.


def get_default_properties():
    """Returns a dictionary containing the default properties for a new text element."""
    return {
        "content": "Text",
        "font": {
            "family": "Arial",
            "size": 14,
            "bold": False,
            "italic": False
        },
        "color": "#000000"
    }