# services/tag_data_service.py
# Manages all data related to tag databases and tags.

import uuid
import copy
from PyQt6.QtCore import QObject, pyqtSignal
from typing import Dict, Any, List, Optional
from .data_context import DataContext, data_context

class TagDataService(QObject):
    """
    A service that manages all tag data for the project.
    It acts as the single source of truth for this data.
    """
    tags_changed = pyqtSignal()
    database_list_changed = pyqtSignal()

    def __init__(self, bus: DataContext):
        super().__init__()
        self._bus = bus
        self._tag_databases = {}
        # Dictionaries for O(1) lookups
        self._db_name_index: Dict[str, str] = {}  # database name -> id
        self._tag_name_index: Dict[str, Dict[str, Dict[str, Any]]] = {}

        # Bridge existing signals into the shared data context
        self.tags_changed.connect(
            lambda: self._bus.tags_changed.emit({"action": "tags_changed"})
        )
        self.database_list_changed.connect(
            lambda: self._bus.tags_changed.emit({"action": "database_list_changed"})
        )

    def clear_all(self):
        """Resets the service by clearing all tag data."""
        self._tag_databases.clear()
        self.database_list_changed.emit()
        self._db_name_index.clear()
        self._tag_name_index.clear()
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
        return name not in self._db_name_index

    # Helper method to find a database ID by its name.
    def find_db_id_by_name(self, db_name: str) -> Optional[str]:
        """Finds a database ID by its unique name."""
        return self._db_name_index.get(db_name)

    # --- Tag Getters ---
    def get_tag(self, db_id, tag_name):
        """Gets a specific tag from a database."""
        return self._tag_name_index.get(db_id, {}).get(tag_name)
        
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
        return tag_name not in self._tag_name_index.get(db_id, {})

    # --- Internal "Perform" Methods for Commands ---
    def _perform_add_tag_database(self, db_data, db_id=None):
        new_id = db_id or str(uuid.uuid4())
        db_data['id'] = new_id
        if 'tags' not in db_data: db_data['tags'] = []
        self._tag_databases[new_id] = db_data
        db_name = db_data.get('name')
        if db_name:
            self._db_name_index[db_name] = new_id
        # build tag index for this database
        tag_dict: Dict[str, Dict[str, Any]] = {}
        for tag in db_data['tags']:
            tag_name = tag.get('name')
            if tag_name:
                tag_dict[tag_name] = tag
        self._tag_name_index[new_id] = tag_dict
        return new_id

    def _perform_remove_tag_database(self, db_id):
        if db_id in self._tag_databases:
            db_data = self._tag_databases.pop(db_id)
            db_name = db_data.get('name')
            if db_name:
                self._db_name_index.pop(db_name, None)
            self._tag_name_index.pop(db_id, None)
            return db_data
        return None

    def _perform_rename_tag_database(self, db_id, new_name):
        if db_id in self._tag_databases:
            old_name = self._tag_databases[db_id].get('name')
            self._tag_databases[db_id]['name'] = new_name
            if old_name:
                self._db_name_index.pop(old_name, None)
            self._db_name_index[new_name] = db_id
            return True
        return False

    def _perform_add_tag(self, db_id, tag_data):
        if db_id in self._tag_databases:
            self._tag_databases[db_id]['tags'].append(tag_data)
            tag_name = tag_data.get('name')
            if db_id not in self._tag_name_index:
                self._tag_name_index[db_id] = {}
            if tag_name:
                self._tag_name_index[db_id][tag_name] = tag_data
            return True
        return False

    def _perform_remove_tag(self, db_id, tag_name):
        if db_id in self._tag_databases:
            self._tag_databases[db_id]['tags'] = [t for t in self._tag_databases[db_id]['tags'] if t['name'] != tag_name]
            if db_id in self._tag_name_index:
                self._tag_name_index[db_id].pop(tag_name, None)
            return True
        return False

    def _perform_update_tag(self, db_id, original_tag_name, new_tag_data):
        if db_id in self._tag_databases:
            for i, tag in enumerate(self._tag_databases[db_id]['tags']):
                if tag['name'] == original_tag_name:
                    self._tag_databases[db_id]['tags'][i] = new_tag_data
                    # update name index
                    if db_id not in self._tag_name_index:
                        self._tag_name_index[db_id] = {}
                    self._tag_name_index[db_id].pop(original_tag_name, None)
                    new_name = new_tag_data.get('name')
                    if new_name:
                        self._tag_name_index[db_id][new_name] = new_tag_data
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
        # rebuild indexes
        for db_id, db_data in self._tag_databases.items():
            db_name = db_data.get('name')
            if db_name:
                self._db_name_index[db_name] = db_id
            tag_dict: Dict[str, Dict[str, Any]] = {}
            for tag in db_data.get('tags', []):
                tag_name = tag.get('name')
                if tag_name:
                    tag_dict[tag_name] = tag
            self._tag_name_index[db_id] = tag_dict
        self.database_list_changed.emit()
        self.tags_changed.emit()

tag_data_service = TagDataService(data_context)
