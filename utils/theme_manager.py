# utils/theme_manager.py
import re
import os
from functools import lru_cache

@lru_cache(maxsize=1)
def get_theme_colors(theme_name):
    """
    Parses a theme's QSS file to extract key color definitions.
    """
    colors = {
        "icon_color": "#cccccc",
        "icon_color_active": "#ffffff",
        "highlight_color": "#2d2d30"
    }

    try:
        # We need to construct the path to the stylesheet
        base_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        style_path = os.path.join(base_dir, 'styles', theme_name, 'main.qss')

        if not os.path.exists(style_path):
            return colors

        with open(style_path, 'r') as f:
            content = f.read()

            # Extract colors using regex
            icon_color_match = re.search(r"/\* icon_color:\s*(#[0-9a-fA-F]{6})\s*\*/", content)
            if icon_color_match:
                colors["icon_color"] = icon_color_match.group(1)

            icon_color_active_match = re.search(r"/\* icon_color_active:\s*(#[0-9a-fA-F]{6})\s*\*/", content)
            if icon_color_active_match:
                colors["icon_color_active"] = icon_color_active_match.group(1)
            
            highlight_color_match = re.search(r"/\* highlight_color:\s*(#[0-9a-fA-F]{6})\s*\*/", content)
            if highlight_color_match:
                colors["highlight_color"] = highlight_color_match.group(1)

    except Exception as e:
        print(f"Warning: Could not parse theme colors. {e}")

    return colors

def clear_theme_cache():
    get_theme_colors.cache_clear()
