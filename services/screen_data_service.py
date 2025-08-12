# services/screen_data_service.py
# MODIFIED: Centralized the notification logic for parent screen updates.

import uuid
import copy
from PyQt6.QtCore import QObject, pyqtSignal

class ScreenDataService(QObject):
    """
    A service that manages all screen data for the project.
    It acts as the single source of truth for this data.
    """
    screen_list_changed = pyqtSignal()
    screen_modified = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._screens = {}

    def clear_all(self):
        self._screens.clear()
        self.screen_list_changed.emit()
        
    def get_default_style(self):
        return {'opacity': 1.0, 'border_style': 'None', 'border_color': '#7a828e', 'border_width': 1, 'color1': '#ffffff'}

    def get_screen(self, screen_id):
        return self._screens.get(screen_id)

    def get_all_screens(self):
        return self._screens

    def is_screen_number_unique(self, screen_type, number, excluding_id=None):
        for screen_id, screen in self._screens.items():
            if screen_id == excluding_id: continue
            if screen.get('type') == screen_type and screen.get('number') == number: return False
        return True

    def get_child_instance(self, parent_id, instance_id):
        if parent_id in self._screens:
            for inst in self._screens[parent_id].get('children', []):
                if inst['instance_id'] == instance_id: return inst
        return None

    def reorder_child(self, parent_id, instance_id, direction):
        if parent_id not in self._screens: return
        children = self._screens[parent_id].get('children', [])
        indices = [i for i, child in enumerate(children) if child['instance_id'] == instance_id]
        if not indices: return
        idx = indices[0]
        
        if direction == 'front':
            children.append(children.pop(idx))
        elif direction == 'back':
            children.insert(0, children.pop(idx))
        elif direction == 'forward':
            children.insert(idx + 1, children.pop(idx))
        elif direction == 'backward':
            children.insert(idx - 1, children.pop(idx))
        else:
            return
            
        self.screen_modified.emit(parent_id)

    def reorder_children(self, parent_id, instance_ids, direction):
        if parent_id not in self._screens: return
        
        children = self._screens[parent_id].get('children', [])
        instance_id_set = set(instance_ids)

        selected_group = [child for child in children if child['instance_id'] in instance_id_set]
        unselected = [child for child in children if child['instance_id'] not in instance_id_set]

        if not selected_group: return

        if direction == 'front':
            self._screens[parent_id]['children'] = unselected + selected_group
        elif direction == 'back':
            self._screens[parent_id]['children'] = selected_group + unselected
        else:
            return

        self.screen_modified.emit(parent_id)
        
    def get_parent_screens(self, child_screen_id):
        """Finds all screens that contain an instance of the given child_screen_id."""
        parents = []
        for parent_id, screen_data in self._screens.items():
            if parent_id == child_screen_id: continue
            for child in screen_data.get('children', []):
                if child.get('screen_id') == child_screen_id:
                    parents.append(parent_id)
                    break 
        return parents

    def notify_screen_update(self, screen_id):
        """
        Notifies the UI that a screen was modified, and also notifies
        any parent screens that embed it.
        """
        self.screen_modified.emit(screen_id)
        
        parent_ids = self.get_parent_screens(screen_id)
        for parent_id in parent_ids:
            self.screen_modified.emit(parent_id)

    def _perform_add_screen(self, screen_data, screen_id=None):
        new_id = screen_id or str(uuid.uuid4())
        screen_data['id'] = new_id
        if 'style' not in screen_data: screen_data['style'] = self.get_default_style()
        if 'children' not in screen_data: screen_data['children'] = []
        self._screens[new_id] = screen_data
        return new_id

    def _perform_remove_screen(self, screen_id):
        if screen_id in self._screens:
            del self._screens[screen_id]
            for pid in self._screens:
                self._screens[pid]['children'] = [c for c in self._screens[pid].get('children', []) if c.get('screen_id') != screen_id]
        return True
        
    def _perform_update_screen(self, screen_id, new_data):
        """
        MODIFIED: This method now ONLY updates the data.
        Notification is handled by the command via notify_screen_update.
        """
        if screen_id in self._screens:
            self._screens[screen_id] = new_data
            return True
        return False

    def _find_child_references(self, screen_id):
        return [(pid, copy.deepcopy(c)) for pid, pdata in self._screens.items() for c in pdata.get('children', []) if c.get('screen_id') == screen_id]

    def _perform_add_child(self, parent_id, child_data):
        if parent_id in self._screens:
            if 'children' not in self._screens[parent_id]:
                self._screens[parent_id]['children'] = []
            self._screens[parent_id]['children'].append(child_data)
            return True
        return False

    def _perform_remove_child(self, parent_id, instance_id):
        if parent_id in self._screens:
            self._screens[parent_id]['children'] = [i for i in self._screens[parent_id].get('children', []) if i['instance_id'] != instance_id]
            return True
        return False

    def _perform_update_child_position(self, parent_id, instance_id, position):
        instance = self.get_child_instance(parent_id, instance_id)
        if instance:
            if 'position' in instance:
                instance['position'] = position
            elif 'properties' in instance and 'position' in instance['properties']:
                instance['properties']['position'] = position
            return True
        return False

    def _perform_update_child_properties(self, parent_id, instance_id, new_props):
        instance = self.get_child_instance(parent_id, instance_id)
        if instance and 'properties' in instance:
            instance['properties'] = new_props
            return True
        return False

    def serialize_for_project(self):
        return {"screens": self._screens}

    def load_from_project(self, project_data):
        self.clear_all()
        self._screens = project_data.get("screens", {})
        self.screen_list_changed.emit()

screen_service = ScreenDataService()
