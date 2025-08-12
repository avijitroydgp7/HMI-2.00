# services/clipboard_service.py
# A service to manage in-application clipboard content with proper type handling.

import copy
import uuid

class ClipboardService:
    """
    A singleton service that acts as a clipboard for the application,
    storing copied or cut items with proper type handling.
    """
    def __init__(self):
        self.clear()

    def set_content(self, content_type, data):
        """
        Sets the clipboard's content with proper type handling.

        Args:
            content_type (str): The type of content (e.g., 'screen', 'embedded_screen').
            data: The data to be stored. Can be a single item or a list of items.
                 Each item will be deep-copied.
        """
        if content_type == 'embedded_screen':
            # Handle both single items and lists
            items = data if isinstance(data, list) else [data]
            copied_items = []
            
            for item in items:
                # For embedded screens, we only store essential data
                copied_data = {
                    'screen_id': item['screen_id'],
                    'position': copy.deepcopy(item.get('position', {'x': 0, 'y': 0})),
                    'style': copy.deepcopy(item.get('style', {})),
                    'properties': copy.deepcopy(item.get('properties', {}))
                }
                copied_items.append(copied_data)
            
            self._content_type = content_type
            self._data = copied_items if isinstance(data, list) else copied_items[0]
        else:
            # For other types, do a full deep copy
            self._content_type = content_type
            self._data = copy.deepcopy(data)

    def get_content(self):
        """
        Retrieves the clipboard's content.

        Returns:
            tuple: A tuple containing the content_type and the data.
                  For embedded screens, each item will have a new instance ID.
        """
        if self._content_type == 'embedded_screen':
            if isinstance(self._data, list):
                # Handle multiple items
                data_copies = []
                for item in self._data:
                    data_copy = copy.deepcopy(item)
                    data_copy['instance_id'] = str(uuid.uuid4())
                    data_copies.append(data_copy)
                return self._content_type, data_copies
            else:
                # Handle single item
                data_copy = copy.deepcopy(self._data)
                data_copy['instance_id'] = str(uuid.uuid4())
                return self._content_type, data_copy
        return self._content_type, copy.deepcopy(self._data)

    def clear(self):
        """Clears the clipboard."""
        self._content_type = None
        self._data = None

    def is_empty(self):
        """Checks if the clipboard is empty."""
        return self._content_type is None

    def get_preview(self):
        """
        Gets a human-readable preview of the clipboard content.
        
        Returns:
            str: A description of what's in the clipboard.
        """
        if self.is_empty() or not self._data:
            return "Empty clipboard"
            
        if self._content_type == 'embedded_screen':
            if isinstance(self._data, list):
                count = len(self._data)
                if count == 0:
                    return "Empty clipboard"
                if count == 1:
                    item = self._data[0]
                    if isinstance(item, dict):
                        return f"Embedded Screen (ID: {item.get('screen_id', 'unknown')})"
                    else:
                        return "Empty clipboard"
                return f"{count} Embedded Screens"
            elif isinstance(self._data, dict):
                return f"Embedded Screen (ID: {self._data.get('screen_id', 'unknown')})"
            else:
                return "Empty clipboard"
        else:
            return f"Content type: {self._content_type}"

# Create a singleton instance
clipboard_service = ClipboardService()
