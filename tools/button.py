# tools/button.py
# Defines the default properties and styles for a button component.

from . import button_styles

def get_default_properties():
    """
    Returns a dictionary containing the default properties for a new button,
    based on the default style from the library.
    """
    default_style = button_styles.get_style_by_id("default_rounded")
    
    return {
        "label": "Button",
        "size": {"width": 100, "height": 40},
        "style_id": default_style["id"],
        **default_style["properties"]
    }
