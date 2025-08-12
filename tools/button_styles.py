# tools/button_styles.py
# A library defining different visual styles for button components.

def get_styles():
    """
    Returns a list of available button style definitions.
    Each style has a unique ID, a display name, and a set of properties.
    """
    return [
        {
            "id": "default_rounded",
            "name": "Default Rounded",
            "properties": {
                "background_color": "#5a6270",
                "text_color": "#ffffff",
                "border_radius": 20,
            }
        },
        {
            "id": "success_square",
            "name": "Success Square",
            "properties": {
                "background_color": "#4CAF50",
                "text_color": "#ffffff",
                "border_radius": 5,
            }
        },
        {
            "id": "warning_pill",
            "name": "Warning Pill",
            "properties": {
                "background_color": "#ff9800",
                "text_color": "#000000",
                "border_radius": 20, # Height will make it a pill
            }
        },
        {
            "id": "danger_flat",
            "name": "Danger Flat",
            "properties": {
                "background_color": "#f44336",
                "text_color": "#ffffff",
                "border_radius": 0,
            }
        }
    ]

def get_style_by_id(style_id):
    """Finds and returns a style dictionary by its unique ID."""
    for style in get_styles():
        if style["id"] == style_id:
            return style
    return get_styles()[0] # Return default if not found
