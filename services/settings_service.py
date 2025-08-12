# services/settings_service.py
# A simple service for persisting application settings.

import json
import os

class SettingsService:
    """
    Manages loading and saving application settings from a JSON file.
    This includes window geometry, dock positions, and other user preferences.
    """
    def __init__(self, file_name="app_settings.json"):
        """
        Initializes the service and loads existing settings from the file.
        """
        self.file_path = file_name
        self.settings = self._load()

    def _load(self):
        """
        Loads the settings from the JSON file.
        Returns an empty dictionary if the file doesn't exist or is invalid.
        """
        try:
            if os.path.exists(self.file_path):
                with open(self.file_path, 'r') as f:
                    return json.load(f)
        except (IOError, json.JSONDecodeError) as e:
            print(f"Could not load settings: {e}")
        return {}

    def save(self):
        """Saves the current settings dictionary to the JSON file."""
        try:
            with open(self.file_path, 'w') as f:
                json.dump(self.settings, f, indent=4)
        except IOError as e:
            print(f"Could not save settings: {e}")

    def get_value(self, key, default=None):
        """
        Retrieves a value from the settings for a given key.

        Args:
            key (str): The key for the setting.
            default: The value to return if the key is not found.

        Returns:
            The setting value or the default.
        """
        return self.settings.get(key, default)

    def set_value(self, key, value):
        """
        Sets a value in the settings for a given key.
        """
        self.settings[key] = value

# Create a singleton instance to be used throughout the application
settings_service = SettingsService()
