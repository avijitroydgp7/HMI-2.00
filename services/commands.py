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
            screen_service.rebuild_reverse_index()
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


class AddAnchorCommand(Command):
    def __init__(self, screen_id, instance_id, index, point, props):
        super().__init__()
        self.screen_id = screen_id
        self.instance_id = instance_id
        self.index = index
        self.old_props = copy.deepcopy(props)
        self.new_props = copy.deepcopy(props)
        pts = self.new_props.get('points', [])
        pts.insert(index, copy.deepcopy(point))
        self.new_props['points'] = pts

    def redo(self):
        from services.screen_data_service import screen_service
        screen_service._perform_update_child_properties(self.screen_id, self.instance_id, self.new_props)

    def undo(self):
        from services.screen_data_service import screen_service
        screen_service._perform_update_child_properties(self.screen_id, self.instance_id, self.old_props)

    def _notify(self):
        from services.screen_data_service import screen_service
        screen_service.screen_modified.emit(self.screen_id)


class RemoveAnchorCommand(Command):
    def __init__(self, screen_id, instance_id, index, props):
        super().__init__()
        self.screen_id = screen_id
        self.instance_id = instance_id
        self.index = index
        self.old_props = copy.deepcopy(props)
        self.new_props = copy.deepcopy(props)
        pts = self.new_props.get('points', [])
        if 0 <= index < len(pts):
            pts.pop(index)
        self.new_props['points'] = pts

    def redo(self):
        from services.screen_data_service import screen_service
        screen_service._perform_update_child_properties(self.screen_id, self.instance_id, self.new_props)

    def undo(self):
        from services.screen_data_service import screen_service
        screen_service._perform_update_child_properties(self.screen_id, self.instance_id, self.old_props)

    def _notify(self):
        from services.screen_data_service import screen_service
        screen_service.screen_modified.emit(self.screen_id)


class MoveAnchorCommand(Command):
    def __init__(self, screen_id, instance_id, index, point, props):
        super().__init__()
        self.screen_id = screen_id
        self.instance_id = instance_id
        self.index = index
        self.old_props = copy.deepcopy(props)
        self.new_props = copy.deepcopy(props)
        pts = self.new_props.get('points', [])
        if 0 <= index < len(pts):
            pts[index] = copy.deepcopy(point)
        self.new_props['points'] = pts

    def redo(self):
        from services.screen_data_service import screen_service
        screen_service._perform_update_child_properties(self.screen_id, self.instance_id, self.new_props)

    def undo(self):
        from services.screen_data_service import screen_service
        screen_service._perform_update_child_properties(self.screen_id, self.instance_id, self.old_props)

    def _notify(self):
        from services.screen_data_service import screen_service
        screen_service.screen_modified.emit(self.screen_id)

# --- Comment Group Commands ---
class AddCommentGroupCommand(Command):
    def __init__(self, group_data, group_id=None):
        super().__init__(); self.group_data = copy.deepcopy(group_data); self.group_id = group_id
    def redo(self):
        from services.comment_data_service import comment_data_service
        self.group_id = comment_data_service._perform_add_group(self.group_data, self.group_id); self.group_data['id'] = self.group_id
    def undo(self):
        from services.comment_data_service import comment_data_service
        if self.group_id: comment_data_service._perform_remove_group(self.group_id)
    def _notify(self):
        from services.comment_data_service import comment_data_service
        comment_data_service.comment_group_list_changed.emit()

class RemoveCommentGroupCommand(Command):
    def __init__(self, group_id):
        from services.comment_data_service import comment_data_service
        super().__init__(); self.group_id = group_id; self.group_data = copy.deepcopy(comment_data_service.get_group(group_id))
    def redo(self):
        from services.comment_data_service import comment_data_service
        comment_data_service._perform_remove_group(self.group_id)
    def undo(self):
        from services.comment_data_service import comment_data_service
        if self.group_data: comment_data_service._perform_add_group(self.group_data, self.group_id)
    def _notify(self):
        from services.comment_data_service import comment_data_service
        comment_data_service.comment_group_list_changed.emit()

class RenameCommentGroupCommand(Command):
    def __init__(self, group_id, new_name, new_number, old_name, old_number):
        super().__init__(); self.group_id = group_id; self.new_name = new_name; self.new_number = new_number; self.old_name = old_name; self.old_number = old_number
    def redo(self):
        from services.comment_data_service import comment_data_service
        comment_data_service._perform_rename_group(self.group_id, self.new_name, self.new_number)
    def undo(self):
        from services.comment_data_service import comment_data_service
        comment_data_service._perform_rename_group(self.group_id, self.old_name, self.old_number)
    def _notify(self):
        from services.comment_data_service import comment_data_service
        comment_data_service.comment_group_list_changed.emit()

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

# --- Comment Table Commands ---
class UpdateCommentCellCommand(Command):
    def __init__(self, model, row, col, new_value, old_value, notify):
        super().__init__(); self.model = model; self.row = row; self.col = col; self.new_value = new_value; self.old_value = old_value; self.notify = notify
    def redo(self):
        self.model._suspend_history = True; self.model.setData(self.model.index(self.row, self.col), self.new_value); self.model._suspend_history = False
    def undo(self):
        self.model._suspend_history = True; self.model.setData(self.model.index(self.row, self.col), self.old_value); self.model._suspend_history = False
    def _notify(self):
        if self.notify: self.notify()

class UpdateCommentFormatCommand(Command):
    def __init__(self, model, row, col, new_fmt, old_fmt, notify):
        super().__init__(); self.model = model; self.row = row; self.col = col; self.new_fmt = copy.deepcopy(new_fmt); self.old_fmt = copy.deepcopy(old_fmt); self.notify = notify
    def redo(self):
        self.model._suspend_history = True; self.model.set_cell_format(self.row, self.col, self.new_fmt); self.model._suspend_history = False
    def undo(self):
        self.model._suspend_history = True; self.model.set_cell_format(self.row, self.col, self.old_fmt); self.model._suspend_history = False
    def _notify(self):
        if self.notify: self.notify()

class InsertCommentRowCommand(Command):
    def __init__(self, model, row, values, notify):
        super().__init__(); self.model = model; self.row = row; self.values = copy.deepcopy(values); self.notify = notify
    def redo(self):
        self.model._suspend_history = True; self.model.insertRow(self.row)
        for c, cell in enumerate(self.values, start=1):
            self.model.setData(self.model.index(self.row, c), cell.get('raw', ''))
            fmt = cell.get('format');
            if fmt: self.model.set_cell_format(self.row, c, fmt)
        self.model._suspend_history = False
    def undo(self):
        self.model._suspend_history = True; self.model.removeRow(self.row); self.model._suspend_history = False
    def _notify(self):
        if self.notify: self.notify()

class RemoveCommentRowsCommand(Command):
    def __init__(self, model, rows, rows_data, notify):
        super().__init__(); self.model = model; self.rows = rows; self.rows_data = copy.deepcopy(rows_data); self.notify = notify
    def redo(self):
        self.model._suspend_history = True
        for r in sorted(self.rows, reverse=True): self.model.removeRow(r)
        self.model._suspend_history = False
    def undo(self):
        self.model._suspend_history = True
        for r, data in sorted(zip(self.rows, self.rows_data)):
            self.model.insertRow(r)
            for c, cell in enumerate(data, start=1):
                self.model.setData(self.model.index(r, c), cell.get('raw', ''))
                fmt = cell.get('format');
                if fmt: self.model.set_cell_format(r, c, fmt)
        self.model._suspend_history = False
    def _notify(self):
        if self.notify: self.notify()

class InsertCommentColumnCommand(Command):
    def __init__(self, model, column, header, columns_list, notify):
        super().__init__(); self.model = model; self.column = column; self.header = header; self.columns_list = columns_list; self.notify = notify
    def redo(self):
        from PyQt6.QtCore import Qt
        self.model._suspend_history = True; self.model.insertColumn(self.column); self.model.setHeaderData(self.column, Qt.Orientation.Horizontal, self.header); self.model._suspend_history = False; self.columns_list.insert(self.column - 1, self.header)
    def undo(self):
        self.model._suspend_history = True; self.model.removeColumn(self.column); self.model._suspend_history = False; self.columns_list.pop(self.column - 1)
    def _notify(self):
        if self.notify: self.notify()

class RemoveCommentColumnCommand(Command):
    def __init__(self, model, column, header, column_data, columns_list, notify):
        super().__init__(); self.model = model; self.column = column; self.header = header; self.column_data = copy.deepcopy(column_data); self.columns_list = columns_list; self.notify = notify
    def redo(self):
        self.model._suspend_history = True; self.model.removeColumn(self.column); self.model._suspend_history = False; self.columns_list.pop(self.column - 1)
    def undo(self):
        from PyQt6.QtCore import Qt
        self.model._suspend_history = True; self.model.insertColumn(self.column); self.model.setHeaderData(self.column, Qt.Orientation.Horizontal, self.header)
        for r, cell in enumerate(self.column_data):
            self.model.setData(self.model.index(r, self.column), cell.get('raw', ''))
            fmt = cell.get('format');
            if fmt: self.model.set_cell_format(r, self.column, fmt)
        self.model._suspend_history = False; self.columns_list.insert(self.column - 1, self.header)
    def _notify(self):
        if self.notify: self.notify()

class BulkUpdateCellsCommand(Command):
    def __init__(self, model, updates, notify):
        super().__init__(); self.model = model; self.updates = updates; self.notify = notify
    def redo(self):
        self.model._suspend_history = True
        for row, col, new_val, _ in self.updates: self.model.setData(self.model.index(row, col), new_val)
        self.model._suspend_history = False
    def undo(self):
        self.model._suspend_history = True
        for row, col, _, old_val in self.updates: self.model.setData(self.model.index(row, col), old_val)
        self.model._suspend_history = False
    def _notify(self):
        if self.notify: self.notify()
