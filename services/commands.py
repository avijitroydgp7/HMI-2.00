# services/commands.py
# Defines the command classes for the undo/redo framework.

import copy
from abc import ABC, abstractmethod

class Command(ABC):
    def __init__(self): pass
    @abstractmethod
    def redo(self): pass
    @abstractmethod
    def undo(self): pass
    def _notify(self): pass

# --- Project Commands ---
class UpdateProjectInfoCommand(Command):
    def __init__(self, new_info_partial, old_info_full):
        super().__init__(); self.new_info_partial = copy.deepcopy(new_info_partial); self.old_info_full = copy.deepcopy(old_info_full)
    def redo(self):
        from services.project_service import project_service
        full_new_info = copy.deepcopy(self.old_info_full); full_new_info.update(self.new_info_partial)
        project_service._perform_update_project_info(full_new_info)
    def undo(self):
        from services.project_service import project_service
        project_service._perform_update_project_info(self.old_info_full)
    def _notify(self):
        from services.project_service import project_service
        project_service.project_state_changed.emit()

# --- Screen Commands ---
class AddScreenCommand(Command):
    def __init__(self, screen_data):
        super().__init__(); self.screen_data = copy.deepcopy(screen_data); self.screen_id = None
    def redo(self):
        from services.screen_data_service import screen_service
        self.screen_id = screen_service._perform_add_screen(self.screen_data); self.screen_data['id'] = self.screen_id
    def undo(self):
        from services.screen_data_service import screen_service
        if self.screen_id: screen_service._perform_remove_screen(self.screen_id)
    def _notify(self):
        from services.screen_data_service import screen_service
        screen_service.screen_list_changed.emit()

class RemoveScreenCommand(Command):
    def __init__(self, screen_id):
        from services.screen_data_service import screen_service
        super().__init__(); self.screen_id = screen_id
        self.screen_data = copy.deepcopy(screen_service.get_screen(screen_id))
        self.child_references = screen_service._find_child_references(screen_id)
    def redo(self):
        from services.screen_data_service import screen_service
        screen_service._perform_remove_screen(self.screen_id)
    def undo(self):
        from services.screen_data_service import screen_service
        if self.screen_data:
            screen_service._perform_add_screen(self.screen_data, self.screen_id)
            for parent_id, instance_data in self.child_references:
                parent_screen = screen_service.get_screen(parent_id)
                if parent_screen: parent_screen['children'].append(instance_data)
    def _notify(self):
        from services.screen_data_service import screen_service
        screen_service.screen_list_changed.emit()
        for parent_id, _ in self.child_references: screen_service.screen_modified.emit(parent_id)

class UpdateScreenPropertiesCommand(Command):
    def __init__(self, screen_id, new_data, old_data):
        super().__init__(); self.screen_id = screen_id
        self.new_data = copy.deepcopy(new_data); self.old_data = copy.deepcopy(old_data)
    def redo(self):
        from services.screen_data_service import screen_service
        screen_service._perform_update_screen(self.screen_id, self.new_data)
    def undo(self):
        from services.screen_data_service import screen_service
        screen_service._perform_update_screen(self.screen_id, self.old_data)
    def _notify(self):
        from services.screen_data_service import screen_service
        screen_service.screen_list_changed.emit()
        screen_service.notify_screen_update(self.screen_id)

# --- Child/Tool Instance Commands ---
class AddChildCommand(Command):
    def __init__(self, parent_id, child_data):
        super().__init__(); self.parent_id = parent_id; self.child_data = copy.deepcopy(child_data)
        self.instance_id = self.child_data['instance_id']
    def redo(self):
        from services.screen_data_service import screen_service
        screen_service._perform_add_child(self.parent_id, self.child_data)
    def undo(self):
        from services.screen_data_service import screen_service
        screen_service._perform_remove_child(self.parent_id, self.instance_id)
    def _notify(self):
        from services.screen_data_service import screen_service
        screen_service.screen_modified.emit(self.parent_id)

class RemoveChildCommand(Command):
    def __init__(self, parent_id, instance_data):
        super().__init__(); self.parent_id = parent_id; self.instance_data = copy.deepcopy(instance_data)
        self.instance_id = self.instance_data['instance_id']
    def redo(self):
        from services.screen_data_service import screen_service
        screen_service._perform_remove_child(self.parent_id, self.instance_id)
    def undo(self):
        from services.screen_data_service import screen_service
        screen_service._perform_add_child(self.parent_id, self.instance_data)
    def _notify(self):
        from services.screen_data_service import screen_service
        screen_service.screen_modified.emit(self.parent_id)

# MODIFIED: Re-added the missing MoveChildCommand
class MoveChildCommand(Command):
    def __init__(self, parent_id, instance_id, new_pos, old_pos):
        super().__init__(); self.parent_id = parent_id; self.instance_id = instance_id
        self.new_pos = copy.deepcopy(new_pos); self.old_pos = copy.deepcopy(old_pos)
    def redo(self):
        from services.screen_data_service import screen_service
        screen_service._perform_update_child_position(self.parent_id, self.instance_id, self.new_pos)
    def undo(self):
        from services.screen_data_service import screen_service
        screen_service._perform_update_child_position(self.parent_id, self.instance_id, self.old_pos)
    def _notify(self):
        from services.screen_data_service import screen_service
        screen_service.screen_modified.emit(self.parent_id)

class BulkMoveChildCommand(Command):
    def __init__(self, parent_id, move_list):
        super().__init__()
        self.parent_id = parent_id
        # move_list is a list of tuples: (instance_id, new_pos, old_pos)
        self.move_list = copy.deepcopy(move_list)

    def redo(self):
        from services.screen_data_service import screen_service
        for instance_id, new_pos, _ in self.move_list:
            screen_service._perform_update_child_position(self.parent_id, instance_id, new_pos)

    def undo(self):
        from services.screen_data_service import screen_service
        for instance_id, _, old_pos in self.move_list:
            screen_service._perform_update_child_position(self.parent_id, instance_id, old_pos)

    def _notify(self):
        from services.screen_data_service import screen_service
        screen_service.screen_modified.emit(self.parent_id)

class UpdateChildPropertiesCommand(Command):
    def __init__(self, screen_id, instance_id, new_props, old_props):
        super().__init__(); self.screen_id = screen_id; self.instance_id = instance_id
        self.new_props = copy.deepcopy(new_props); self.old_props = copy.deepcopy(old_props)
    def redo(self):
        from services.screen_data_service import screen_service
        screen_service._perform_update_child_properties(self.screen_id, self.instance_id, self.new_props)
    def undo(self):
        from services.screen_data_service import screen_service
        screen_service._perform_update_child_properties(self.screen_id, self.instance_id, self.old_props)
    def _notify(self):
        from services.screen_data_service import screen_service
        screen_service.screen_modified.emit(self.screen_id)

class BulkUpdateChildPropertiesCommand(Command):
    def __init__(self, screen_id, update_list):
        super().__init__()
        self.screen_id = screen_id
        self.update_list = copy.deepcopy(update_list)

    def redo(self):
        from services.screen_data_service import screen_service
        for instance_id, new_props, _ in self.update_list:
            screen_service._perform_update_child_properties(self.screen_id, instance_id, new_props)

    def undo(self):
        from services.screen_data_service import screen_service
        for instance_id, _, old_props in self.update_list:
            screen_service._perform_update_child_properties(self.screen_id, instance_id, old_props)

    def _notify(self):
        from services.screen_data_service import screen_service
        screen_service.screen_modified.emit(self.screen_id)

# --- Tag Database Commands ---
class AddTagDatabaseCommand(Command):
    def __init__(self, db_data, db_id=None):
        super().__init__(); self.db_data = copy.deepcopy(db_data); self.db_id = db_id
    def redo(self):
        from services.tag_data_service import tag_data_service
        self.db_id = tag_data_service._perform_add_tag_database(self.db_data, self.db_id); self.db_data['id'] = self.db_id
    def undo(self):
        from services.tag_data_service import tag_data_service
        if self.db_id: tag_data_service._perform_remove_tag_database(self.db_id)
    def _notify(self):
        from services.tag_data_service import tag_data_service
        tag_data_service.database_list_changed.emit()

class RemoveTagDatabaseCommand(Command):
    def __init__(self, db_id):
        from services.tag_data_service import tag_data_service
        super().__init__(); self.db_id = db_id; self.db_data = copy.deepcopy(tag_data_service.get_tag_database(db_id))
    def redo(self):
        from services.tag_data_service import tag_data_service
        tag_data_service._perform_remove_tag_database(self.db_id)
    def undo(self):
        from services.tag_data_service import tag_data_service
        if self.db_data: tag_data_service._perform_add_tag_database(self.db_data, self.db_id)
    def _notify(self):
        from services.tag_data_service import tag_data_service
        tag_data_service.database_list_changed.emit()

class RenameTagDatabaseCommand(Command):
    def __init__(self, db_id, new_name, old_name):
        super().__init__(); self.db_id = db_id; self.new_name = new_name; self.old_name = old_name
    def redo(self):
        from services.tag_data_service import tag_data_service
        tag_data_service._perform_rename_tag_database(self.db_id, self.new_name)
    def undo(self):
        from services.tag_data_service import tag_data_service
        tag_data_service._perform_rename_tag_database(self.db_id, self.old_name)
    def _notify(self):
        from services.tag_data_service import tag_data_service
        tag_data_service.database_list_changed.emit()

# --- Tag Commands ---
class AddTagCommand(Command):
    def __init__(self, db_id, tag_data):
        super().__init__(); self.db_id = db_id; self.tag_data = copy.deepcopy(tag_data)
    def redo(self):
        from services.tag_data_service import tag_data_service
        tag_data_service._perform_add_tag(self.db_id, self.tag_data)
    def undo(self):
        from services.tag_data_service import tag_data_service
        tag_data_service._perform_remove_tag(self.db_id, self.tag_data['name'])
    def _notify(self):
        from services.tag_data_service import tag_data_service
        tag_data_service.tags_changed.emit()
        
class BulkAddTagsCommand(Command):
    def __init__(self, db_id, tags_data):
        super().__init__(); self.db_id = db_id; self.tags_data = copy.deepcopy(tags_data)
    def redo(self):
        from services.tag_data_service import tag_data_service
        for tag_data in self.tags_data: tag_data_service._perform_add_tag(self.db_id, tag_data)
    def undo(self):
        from services.tag_data_service import tag_data_service
        for tag_data in self.tags_data: tag_data_service._perform_remove_tag(self.db_id, tag_data['name'])
    def _notify(self):
        from services.tag_data_service import tag_data_service
        tag_data_service.tags_changed.emit()

class RemoveTagCommand(Command):
    def __init__(self, db_id, tag_name):
        from services.tag_data_service import tag_data_service
        super().__init__(); self.db_id = db_id; self.tag_name = tag_name
        self.tag_data = copy.deepcopy(tag_data_service.get_tag(db_id, tag_name))
    def redo(self):
        from services.tag_data_service import tag_data_service
        tag_data_service._perform_remove_tag(self.db_id, self.tag_name)
    def undo(self):
        from services.tag_data_service import tag_data_service
        if self.tag_data: tag_data_service._perform_add_tag(self.db_id, self.tag_data)
    def _notify(self):
        from services.tag_data_service import tag_data_service
        tag_data_service.tags_changed.emit()

class UpdateTagCommand(Command):
    def __init__(self, db_id, original_tag_name, new_tag_data):
        from services.tag_data_service import tag_data_service
        super().__init__(); self.db_id = db_id; self.original_tag_name = original_tag_name
        self.new_tag_data = copy.deepcopy(new_tag_data)
        self.old_tag_data = copy.deepcopy(tag_data_service.get_tag(db_id, original_tag_name))
    def redo(self):
        from services.tag_data_service import tag_data_service
        tag_data_service._perform_update_tag(self.db_id, self.original_tag_name, self.new_tag_data)
    def undo(self):
        from services.tag_data_service import tag_data_service
        if self.old_tag_data: tag_data_service._perform_update_tag(self.db_id, self.new_tag_data['name'], self.old_tag_data)
    def _notify(self):
        from services.tag_data_service import tag_data_service
        tag_data_service.tags_changed.emit()

class UpdateTagValueCommand(Command):
    def __init__(self, db_id, tag_name, indices, new_value, old_value):
        super().__init__(); self.db_id = db_id; self.tag_name = tag_name
        self.indices = indices; self.new_value = new_value; self.old_value = old_value
    def redo(self):
        from services.tag_data_service import tag_data_service
        tag_data_service._perform_update_tag_element_value(self.db_id, self.tag_name, self.indices, self.new_value)
    def undo(self):
        from services.tag_data_service import tag_data_service
        tag_data_service._perform_update_tag_element_value(self.db_id, self.tag_name, self.indices, self.old_value)
    def _notify(self):
        from services.tag_data_service import tag_data_service
        tag_data_service.tags_changed.emit()
