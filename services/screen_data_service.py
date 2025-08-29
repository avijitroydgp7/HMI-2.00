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
        self._child_to_parents = {}

    def _index_add_child(self, parent_id, child_screen_id):
        if not child_screen_id:
            return
        parents = self._child_to_parents.get(child_screen_id)
        if parents is None:
            self._child_to_parents[child_screen_id] = {parent_id}
        else:
            parents.add(parent_id)

    def _index_remove_child(self, parent_id, child_screen_id):
        parents = self._child_to_parents.get(child_screen_id)
        if not parents:
            return
        parents.discard(parent_id)
        if not parents:
            self._child_to_parents.pop(child_screen_id, None)

    def rebuild_reverse_index(self):
        self._child_to_parents = {}
        for parent_id, screen_data in self._screens.items():
            for child in screen_data.get('children', []):
                self._index_add_child(parent_id, child.get('screen_id'))

    def clear_all(self):
        self._screens.clear()
        self._child_to_parents.clear()
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
        """
        Reorder a single child by delegating to the generic helper.
        """
        self._reorder_children(parent_id, [instance_id], direction, group=False)

    def reorder_children(self, parent_id, instance_ids, direction):
        """
        Reorder multiple children by delegating to the generic helper.
        """
        self._reorder_children(parent_id, instance_ids, direction, group=True)

    def _reorder_children(self, parent_id, instance_ids, direction, group=False):
        """
        Generic helper to reorder one or more children under a given parent.

        - parent existence checks handled here
        - supports directions: 'front', 'back', 'forward', 'backward'
        - emits screen_modified exactly once after a successful reorder

        The 'group' flag is reserved for potential future semantics tweaks for
        forward/backward moves; current implementation preserves relative order
        of selected items for 'front'/'back', and moves contiguous runs by one
        step for 'forward'/'backward'.
        """
        if parent_id not in self._screens:
            return

        children = self._screens[parent_id].get('children', [])
        if not children:
            return

        # Filter provided IDs to those actually present under the parent
        id_set = set(instance_ids or [])
        if not id_set:
            return

        selected = [c for c in children if c.get('instance_id') in id_set]
        if not selected:
            return

        changed = False

        if direction == 'front':
            # Move selected to the end, preserving relative order
            unselected = [c for c in children if c.get('instance_id') not in id_set]
            new_children = unselected + selected
            if new_children != children:
                self._screens[parent_id]['children'] = new_children
                changed = True
        elif direction == 'back':
            # Move selected to the beginning, preserving relative order
            unselected = [c for c in children if c.get('instance_id') not in id_set]
            new_children = selected + unselected
            if new_children != children:
                self._screens[parent_id]['children'] = new_children
                changed = True
        elif direction == 'forward':
            # Move selected items one step toward the front.
            # Operate in-place by swapping selected runs with the next unselected item.
            i = len(children) - 2
            while i >= 0:
                cur = children[i]
                nxt = children[i + 1]
                cur_sel = cur.get('instance_id') in id_set
                nxt_sel = nxt.get('instance_id') in id_set
                if cur_sel and not nxt_sel:
                    children[i], children[i + 1] = nxt, cur
                    changed = True
                i -= 1
        elif direction == 'backward':
            # Move selected items one step toward the back.
            i = 1
            n = len(children)
            while i < n:
                prev = children[i - 1]
                cur = children[i]
                prev_sel = prev.get('instance_id') in id_set
                cur_sel = cur.get('instance_id') in id_set
                if cur_sel and not prev_sel:
                    children[i - 1], children[i] = cur, prev
                    changed = True
                i += 1
        else:
            # Unknown direction; do nothing
            return

        if changed:
            self.screen_modified.emit(parent_id)
        
    def get_parent_screens(self, child_screen_id):
        return list(self._child_to_parents.get(child_screen_id, set()))

    def notify_screen_update(self, screen_id):
        """
        Notifies the UI that a screen was modified, and also notifies
        any parent screens that embed it.
        """
        self.screen_modified.emit(screen_id)
        for parent_id in self._child_to_parents.get(screen_id, set()):
            self.screen_modified.emit(parent_id)

    def _perform_add_screen(self, screen_data, screen_id=None):
        new_id = screen_id or str(uuid.uuid4())
        screen_data['id'] = new_id
        if 'style' not in screen_data: screen_data['style'] = self.get_default_style()
        if 'children' not in screen_data: screen_data['children'] = []
        self._screens[new_id] = screen_data
        for child in screen_data.get('children', []):
            self._index_add_child(new_id, child.get('screen_id'))
        return new_id

    def _perform_remove_screen(self, screen_id):
        if screen_id in self._screens:
            for child in self._screens[screen_id].get('children', []):
                self._index_remove_child(screen_id, child.get('screen_id'))

            del self._screens[screen_id]

            for pid in self._screens:
                before = self._screens[pid].get('children', [])
                self._screens[pid]['children'] = [c for c in before if c.get('screen_id') != screen_id]

            self._child_to_parents.pop(screen_id, None)
        return True
        
    def _perform_update_screen(self, screen_id, new_data):
        """
        MODIFIED: This method now ONLY updates the data.
        Notification is handled by the command via notify_screen_update.
        """
        if screen_id in self._screens:
            # Keep reverse index consistent if children changed via a full screen update
            old_children = self._screens[screen_id].get('children', [])
            new_children = new_data.get('children', [])
            old_set = {c.get('screen_id') for c in old_children if c.get('screen_id')}
            new_set = {c.get('screen_id') for c in new_children if c.get('screen_id')}

            # Remove parent link for children no longer present
            for cid in old_set - new_set:
                self._index_remove_child(screen_id, cid)
            # Add parent link for newly added children
            for cid in new_set - old_set:
                self._index_add_child(screen_id, cid)

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
            self._index_add_child(parent_id, child_data.get('screen_id'))
            return True
        return False

    def _perform_remove_child(self, parent_id, instance_id):
        if parent_id in self._screens:
            children = self._screens[parent_id].get('children', [])
            removed_child_ids = [i.get('screen_id') for i in children if i.get('instance_id') == instance_id]
            new_children = [i for i in children if i.get('instance_id') != instance_id]
            self._screens[parent_id]['children'] = new_children
            for cid in removed_child_ids:
                # Only remove parent mapping if no other instance of this child remains in this parent
                if not any(i.get('screen_id') == cid for i in new_children):
                    self._index_remove_child(parent_id, cid)
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
        # Rebuild reverse index from loaded data
        self.rebuild_reverse_index()
        self.screen_list_changed.emit()

screen_service = ScreenDataService()
