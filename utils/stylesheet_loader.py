# utils/stylesheet_loader.py
import os

def get_available_themes(styles_dir="styles"):
    """
    Scans the styles directory for theme subdirectories.

    Args:
        styles_dir (str): The directory containing theme folders.

    Returns:
        list: A list of theme names (directory names).
    """
    try:
        base_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        styles_path = os.path.join(base_dir, styles_dir)
        if not os.path.isdir(styles_path):
            return []
        
        themes = [d for d in os.listdir(styles_path) if os.path.isdir(os.path.join(styles_path, d))]
        return sorted(themes)
    except Exception as e:
        print(f"Warning: Could not scan for themes. {e}")
        return []

def load_all_stylesheets(theme_name, styles_dir="styles"):
    """
    Loads and concatenates all .qss files from a given theme directory.
    This allows for splitting styles into multiple organized files.

    Args:
        theme_name (str): The name of the theme directory inside the styles_dir.
        styles_dir (str): The root directory containing theme folders.

    Returns:
        str: A single string containing all combined stylesheets.
    """

    full_stylesheet = ""
    try:
        # Assume this script is in 'utils', so '..' goes up to the project root.
        base_dir = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
        theme_path = os.path.join(base_dir, styles_dir, theme_name)
        
        if not os.path.isdir(theme_path):
            print(f"Warning: Theme directory not found at '{theme_path}'")
            return ""

        # Load files alphabetically to ensure a consistent order.
        files = sorted([f for f in os.listdir(theme_path) if f.endswith(".qss")])

        
        # Ensure global_fix.qss is loaded early to establish base styles
        priority_files = ["global_fix.qss"]
        for priority_file in priority_files:
            if priority_file in files:
                full_path = os.path.join(theme_path, priority_file)
                with open(full_path, 'r') as f:
                    full_stylesheet += f.read() + "\n"
                files.remove(priority_file)
        
        # Load remaining files
        for file_name in files:
            full_path = os.path.join(theme_path, file_name)
            with open(full_path, 'r') as f:
                full_stylesheet += f.read() + "\n"
        return full_stylesheet
    except Exception as e:
        print(f"Warning: Could not load stylesheets for theme '{theme_name}'. {e}")
        return ""
