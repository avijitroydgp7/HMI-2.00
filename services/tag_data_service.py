# services/tag_data_service.py
# Manages all data related to tag databases and tags.

import uuid
import copy
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Dict, Any, List, Optional

class TagDataService(QObject):
    """
    A service that manages all tag data for the project.
    It acts as the single source of truth for this data.
    """
    tags_changed = pyqtSignal()
    database_list_changed = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._tag_databases = {}

    def clear_all(self):
        """Resets the service by clearing all tag data."""
        self._tag_databases.clear()
        self.database_list_changed.emit()
        self.tags_changed.emit()

    def _create_default_array(self, dims, data_type):
        """Recursively creates a nested list for an array tag with default values."""
        if not dims:
            if data_type == 'BOOL': return False
            if data_type in ('INT', 'DINT', 'REAL'): return 0
            return ""
        return [self._create_default_array(dims[1:], data_type) for _ in range(dims[0])]

    # --- Tag Database Getters ---
    def get_tag_database(self, db_id):
        """Retrieves a tag database by its ID."""
        return self._tag_databases.get(db_id)

    def get_all_tag_databases(self):
        """Returns a dictionary of all tag databases."""
        return self._tag_databases

    def is_database_name_unique(self, name):
        """Checks if a tag database name is unique across the project."""
        for db in self._tag_databases.values():
            if db.get('name') == name: return False
        return True

    # MODIFIED: Added a helper method to find a DB by its name.
    def find_db_id_by_name(self, db_name: str) -> Optional[str]:
        """Finds a database ID by its unique name."""
        for db_id, db_data in self._tag_databases.items():
            if db_data.get('name') == db_name:
                return db_id
        return None

    # --- Tag Getters ---
    def get_tag(self, db_id, tag_name):
        """Gets a specific tag from a database."""
        if db_id in self._tag_databases:
            for tag in self._tag_databases[db_id]['tags']:
                if tag['name'] == tag_name: return tag
        return None
        
    def get_tag_element_value(self, db_id, tag_name, indices):
        """Gets the value of a tag or a specific element of an array tag."""
        tag = self.get_tag(db_id, tag_name)
        if not tag: return None
        value = tag.get('value')
        if not indices: return value
        try:
            for index in indices: value = value[index]
            return value
        except (TypeError, IndexError): return None

    def get_all_tags_as_strings(self) -> List[str]:
        """
        Returns a list of all tags from all databases, formatted for display.
        """
        tag_strings = []
        for db_id, db_data in self._tag_databases.items():
            db_name = db_data.get('name', 'Unknown')
            for tag in db_data.get('tags', []):
                tag_name = tag.get('name')
                if tag_name:
                    tag_strings.append(f"[{db_name}]::{tag_name}")
        return tag_strings

    def is_tag_name_unique(self, db_id, tag_name):
        """Checks if a tag name is unique within its database."""
        if db_id in self._tag_databases:
            for tag in self._tag_databases[db_id]['tags']:
                if tag['name'] == tag_name: return False
        return True

    # --- Internal "Perform" Methods for Commands ---
    def _perform_add_tag_database(self, db_data, db_id=None):
        new_id = db_id or str(uuid.uuid4())
        db_data['id'] = new_id
        if 'tags' not in db_data: db_data['tags'] = []
        self._tag_databases[new_id] = db_data
        return new_id

    def _perform_remove_tag_database(self, db_id):
        if db_id in self._tag_databases:
            return self._tag_databases.pop(db_id)
        return None

    def _perform_rename_tag_database(self, db_id, new_name):
        if db_id in self._tag_databases:
            self._tag_databases[db_id]['name'] = new_name
            return True
        return False

    def _perform_add_tag(self, db_id, tag_data):
        if db_id in self._tag_databases:
            self._tag_databases[db_id]['tags'].append(tag_data)
            return True
        return False

    def _perform_remove_tag(self, db_id, tag_name):
        if db_id in self._tag_databases:
            self._tag_databases[db_id]['tags'] = [t for t in self._tag_databases[db_id]['tags'] if t['name'] != tag_name]
            return True
        return False

    def _perform_update_tag(self, db_id, original_tag_name, new_tag_data):
        if db_id in self._tag_databases:
            for i, tag in enumerate(self._tag_databases[db_id]['tags']):
                if tag['name'] == original_tag_name:
                    self._tag_databases[db_id]['tags'][i] = new_tag_data
                    return True
        return False
        
    def _perform_update_tag_element_value(self, db_id, tag_name, indices, new_value):
        tag = self.get_tag(db_id, tag_name)
        if not tag: return False
        if not indices:
            tag['value'] = new_value
            return True
        else:
            value_ptr = tag.get('value')
            try:
                for index in indices[:-1]: value_ptr = value_ptr[index]
                value_ptr[indices[-1]] = new_value
                return True
            except (TypeError, IndexError): return False

    # --- Serialization ---
    def serialize_for_project(self):
        return {"tag_databases": self._tag_databases}

    def load_from_project(self, project_data):
        self.clear_all()
        self._tag_databases = project_data.get("tag_databases", {})
        self.database_list_changed.emit()
        self.tags_changed.emit()

tag_data_service = TagDataService()
