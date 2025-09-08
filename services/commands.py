"""
services/commands.py

Command classes implementing undo/redo operations. Each concrete command
encapsulates the data necessary to perform and revert an action, and emits
the appropriate notifications via a consistent notify() method.
"""

from __future__ import annotations

import copy
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple, Callable

# Hoisted recurring imports to module level to avoid repeated per-method imports
from PyQt6.QtCore import Qt
from services.project_service import project_service
from services.screen_data_service import screen_service
from services.tag_data_service import tag_data_service
from services.comment_data_service import comment_data_service


class Command(ABC):
    """Abstract base for all undo/redo commands."""

    def __init__(self) -> None:
        pass

    @abstractmethod
    def redo(self) -> None:
        """Apply the command's effect."""
        raise NotImplementedError

    @abstractmethod
    def undo(self) -> None:
        """Revert the command's effect."""
        raise NotImplementedError

    def notify(self) -> None:
        """
        Emit any relevant notifications/signals after redo/undo.
        Subclasses override to notify the appropriate services/UI.
        """
        # Default: no notification
        return

# --- Project Commands ---
class UpdateProjectInfoCommand(Command):
    """Updates partial project info and supports undo back to the full original."""

    def __init__(self, new_info_partial: Dict[str, Any], old_info_full: Dict[str, Any]):
        super().__init__()
        # Keep originals safe in case external code mutates the input dicts
        self.new_info_partial: Dict[str, Any] = copy.deepcopy(new_info_partial)
        self.old_info_full: Dict[str, Any] = copy.deepcopy(old_info_full)

    def redo(self) -> None:
        # Shallow clone is sufficient for merge, originals kept via deepcopy above
        full_new_info: Dict[str, Any] = dict(self.old_info_full)
        full_new_info.update(self.new_info_partial)
        project_service._perform_update_project_info(full_new_info)

    def undo(self) -> None:
        project_service._perform_update_project_info(self.old_info_full)

    def notify(self) -> None:
        project_service.project_state_changed.emit()

# --- Screen Commands ---
class AddScreenCommand(Command):
    """Adds a new screen to the project."""

    def __init__(self, screen_data: Dict[str, Any]):
        super().__init__()
        self.screen_data: Dict[str, Any] = copy.deepcopy(screen_data)
        self.screen_id: Optional[str] = None

    def redo(self) -> None:
        self.screen_id = screen_service._perform_add_screen(self.screen_data)
        self.screen_data['id'] = self.screen_id

    def undo(self) -> None:
        if self.screen_id:
            screen_service._perform_remove_screen(self.screen_id)

    def notify(self) -> None:
        screen_service.screen_list_changed.emit()

class RemoveScreenCommand(Command):
    """Removes a screen and restores it with its references on undo."""

    def __init__(self, screen_id: str):
        super().__init__()
        self.screen_id: str = screen_id
        self.screen_data: Optional[Dict[str, Any]] = copy.deepcopy(
            screen_service.get_screen(screen_id)
        )
        self.child_references: List[Tuple[str, Dict[str, Any]]] = (
            screen_service._find_child_references(screen_id)
        )

    def redo(self) -> None:
        screen_service._perform_remove_screen(self.screen_id)

    def undo(self) -> None:
        if self.screen_data:
            screen_service._perform_add_screen(self.screen_data, self.screen_id)
            for parent_id, instance_data in self.child_references:
                parent_screen = screen_service.get_screen(parent_id)
                if parent_screen:
                    parent_screen['children'].append(instance_data)
            screen_service.rebuild_reverse_index()

    def notify(self) -> None:
        screen_service.screen_list_changed.emit()
        for parent_id, _ in self.child_references:
            screen_service.screen_modified.emit(parent_id)

class UpdateScreenPropertiesCommand(Command):
    """Replaces a screen's data with new_data; undo restores old_data."""

    def __init__(self, screen_id: str, new_data: Dict[str, Any], old_data: Dict[str, Any]):
        super().__init__()
        self.screen_id: str = screen_id
        self.new_data: Dict[str, Any] = copy.deepcopy(new_data)
        self.old_data: Dict[str, Any] = copy.deepcopy(old_data)

    def redo(self) -> None:
        screen_service._perform_update_screen(self.screen_id, self.new_data)

    def undo(self) -> None:
        screen_service._perform_update_screen(self.screen_id, self.old_data)

    def notify(self) -> None:
        screen_service.screen_list_changed.emit()
        screen_service.notify_screen_update(self.screen_id)

# --- Child/Tool Instance Commands ---
class AddChildCommand(Command):
    """Adds a child instance to a parent screen."""

    def __init__(self, parent_id: str, child_data: Dict[str, Any]):
        super().__init__()
        self.parent_id: str = parent_id
        self.child_data: Dict[str, Any] = copy.deepcopy(child_data)
        self.instance_id: Any = self.child_data['instance_id']

    def redo(self) -> None:
        screen_service._perform_add_child(self.parent_id, self.child_data)

    def undo(self) -> None:
        screen_service._perform_remove_child(self.parent_id, self.instance_id)

    def notify(self) -> None:
        screen_service.screen_modified.emit(self.parent_id)

class RemoveChildCommand(Command):
    """Removes a child instance from a parent screen."""

    def __init__(self, parent_id: str, instance_data: Dict[str, Any]):
        super().__init__()
        self.parent_id: str = parent_id
        self.instance_data: Dict[str, Any] = copy.deepcopy(instance_data)
        self.instance_id: Any = self.instance_data['instance_id']

    def redo(self) -> None:
        screen_service._perform_remove_child(self.parent_id, self.instance_id)

    def undo(self) -> None:
        screen_service._perform_add_child(self.parent_id, self.instance_data)

    def notify(self) -> None:
        screen_service.screen_modified.emit(self.parent_id)

# Re-added the missing MoveChildCommand
class MoveChildCommand(Command):
    """Moves a child to a new position; undo restores the previous position."""

    def __init__(self, parent_id: str, instance_id: Any, new_pos: Dict[str, Any], old_pos: Dict[str, Any]):
        super().__init__()
        self.parent_id: str = parent_id
        self.instance_id: Any = instance_id
        # Shallow copies are sufficient for simple position dicts
        self.new_pos: Dict[str, Any] = dict(new_pos)
        self.old_pos: Dict[str, Any] = dict(old_pos)

    def redo(self) -> None:
        screen_service._perform_update_child_position(
            self.parent_id,
            self.instance_id,
            self.new_pos,
        )

    def undo(self) -> None:
        screen_service._perform_update_child_position(
            self.parent_id,
            self.instance_id,
            self.old_pos,
        )

    def notify(self) -> None:
        screen_service.screen_modified.emit(self.parent_id)

class BulkMoveChildCommand(Command):
    """Moves multiple children; undo restores their previous positions."""

    def __init__(self, parent_id: str, move_list: List[Tuple[Any, Dict[str, Any], Dict[str, Any]]]):
        super().__init__()
        self.parent_id: str = parent_id
        # Shallow copies for simple position dicts to avoid unnecessary deep clones
        self.move_list: List[Tuple[Any, Dict[str, Any], Dict[str, Any]]] = [
            (iid, dict(new_pos), dict(old_pos)) for iid, new_pos, old_pos in move_list
        ]

    def redo(self) -> None:
        for instance_id, new_pos, _ in self.move_list:
            screen_service._perform_update_child_position(
                self.parent_id,
                instance_id,
                new_pos,
            )

    def undo(self) -> None:
        for instance_id, _, old_pos in self.move_list:
            screen_service._perform_update_child_position(
                self.parent_id,
                instance_id,
                old_pos,
            )

    def notify(self) -> None:
        screen_service.screen_modified.emit(self.parent_id)

class UpdateChildPropertiesCommand(Command):
    """Updates properties of a child instance; undo restores previous props."""

    def __init__(self, screen_id: str, instance_id: Any, new_props: Dict[str, Any], old_props: Dict[str, Any]):
        super().__init__()
        self.screen_id: str = screen_id
        self.instance_id: Any = instance_id
        self.new_props: Dict[str, Any] = copy.deepcopy(new_props)
        self.old_props: Dict[str, Any] = copy.deepcopy(old_props)

    def redo(self) -> None:
        screen_service._perform_update_child_properties(
            self.screen_id,
            self.instance_id,
            self.new_props,
        )

    def undo(self) -> None:
        screen_service._perform_update_child_properties(
            self.screen_id,
            self.instance_id,
            self.old_props,
        )

    def notify(self) -> None:
        screen_service.screen_modified.emit(self.screen_id)

class BulkUpdateChildPropertiesCommand(Command):
    """Applies multiple child property updates; undo restores old properties."""

    def __init__(self, screen_id: str, update_list: List[Tuple[Any, Dict[str, Any], Dict[str, Any]]]):
        super().__init__()
        self.screen_id: str = screen_id
        self.update_list: List[Tuple[Any, Dict[str, Any], Dict[str, Any]]] = copy.deepcopy(update_list)

    def redo(self) -> None:
        for instance_id, new_props, _ in self.update_list:
            screen_service._perform_update_child_properties(
                self.screen_id,
                instance_id,
                new_props,
            )

    def undo(self) -> None:
        for instance_id, _, old_props in self.update_list:
            screen_service._perform_update_child_properties(
                self.screen_id,
                instance_id,
                old_props,
            )

    def notify(self) -> None:
        screen_service.screen_modified.emit(self.screen_id)


class AddAnchorCommand(Command):
    """Inserts an anchor point into a polygon-like child's points array."""

    def __init__(self, screen_id: str, instance_id: Any, index: int, point: Dict[str, Any], props: Dict[str, Any]):
        super().__init__()
        self.screen_id: str = screen_id
        self.instance_id: Any = instance_id
        self.index: int = index
        self.old_props: Dict[str, Any] = copy.deepcopy(props)
        self.new_props: Dict[str, Any] = copy.deepcopy(props)
        pts = self.new_props.get('points', [])
        pts.insert(index, copy.deepcopy(point))
        self.new_props['points'] = pts

    def redo(self) -> None:
        screen_service._perform_update_child_properties(
            self.screen_id,
            self.instance_id,
            self.new_props,
        )

    def undo(self) -> None:
        screen_service._perform_update_child_properties(
            self.screen_id,
            self.instance_id,
            self.old_props,
        )

    def notify(self) -> None:
        screen_service.screen_modified.emit(self.screen_id)


class RemoveAnchorCommand(Command):
    """Removes an anchor point at the given index from a points array."""

    def __init__(self, screen_id: str, instance_id: Any, index: int, props: Dict[str, Any]):
        super().__init__()
        self.screen_id: str = screen_id
        self.instance_id: Any = instance_id
        self.index: int = index
        self.old_props: Dict[str, Any] = copy.deepcopy(props)
        self.new_props: Dict[str, Any] = copy.deepcopy(props)
        pts = self.new_props.get('points', [])
        if 0 <= index < len(pts):
            pts.pop(index)
        self.new_props['points'] = pts

    def redo(self) -> None:
        screen_service._perform_update_child_properties(
            self.screen_id,
            self.instance_id,
            self.new_props,
        )

    def undo(self) -> None:
        screen_service._perform_update_child_properties(
            self.screen_id,
            self.instance_id,
            self.old_props,
        )

    def notify(self) -> None:
        screen_service.screen_modified.emit(self.screen_id)


class MoveAnchorCommand(Command):
    """Moves an existing anchor point to a new position."""

    def __init__(self, screen_id: str, instance_id: Any, index: int, point: Dict[str, Any], props: Dict[str, Any]):
        super().__init__()
        self.screen_id: str = screen_id
        self.instance_id: Any = instance_id
        self.index: int = index
        self.old_props: Dict[str, Any] = copy.deepcopy(props)
        self.new_props: Dict[str, Any] = copy.deepcopy(props)
        pts = self.new_props.get('points', [])
        if 0 <= index < len(pts):
            pts[index] = copy.deepcopy(point)
        self.new_props['points'] = pts

    def redo(self) -> None:
        screen_service._perform_update_child_properties(
            self.screen_id,
            self.instance_id,
            self.new_props,
        )

    def undo(self) -> None:
        screen_service._perform_update_child_properties(
            self.screen_id,
            self.instance_id,
            self.old_props,
        )

    def notify(self) -> None:
        screen_service.screen_modified.emit(self.screen_id)

# --- Comment Group Commands ---
class AddCommentGroupCommand(Command):
    """Adds a new comment group."""

    def __init__(self, group_data: Dict[str, Any], group_id: Optional[str] = None):
        super().__init__()
        self.group_data: Dict[str, Any] = copy.deepcopy(group_data)
        self.group_id: Optional[str] = group_id

    def redo(self) -> None:
        self.group_id = comment_data_service._perform_add_group(
            self.group_data,
            self.group_id,
        )
        self.group_data['id'] = self.group_id

    def undo(self) -> None:
        if self.group_id:
            comment_data_service._perform_remove_group(self.group_id)

    def notify(self) -> None:
        comment_data_service.comment_group_list_changed.emit()

class RemoveCommentGroupCommand(Command):
    """Removes an existing comment group; undo re-adds it."""

    def __init__(self, group_id: str):
        super().__init__()
        self.group_id: str = group_id
        self.group_data: Optional[Dict[str, Any]] = copy.deepcopy(
            comment_data_service.get_group(group_id)
        )

    def redo(self) -> None:
        comment_data_service._perform_remove_group(self.group_id)

    def undo(self) -> None:
        if self.group_data:
            comment_data_service._perform_add_group(self.group_data, self.group_id)

    def notify(self) -> None:
        comment_data_service.comment_group_list_changed.emit()

class RenameCommentGroupCommand(Command):
    """Renames a comment group and updates its number; undo restores previous."""

    def __init__(self, group_id: str, new_name: str, new_number: Any, old_name: str, old_number: Any):
        super().__init__()
        self.group_id: str = group_id
        self.new_name: str = new_name
        self.new_number: Any = new_number
        self.old_name: str = old_name
        self.old_number: Any = old_number

    def redo(self) -> None:
        comment_data_service._perform_rename_group(
            self.group_id,
            self.new_name,
            self.new_number,
        )

    def undo(self) -> None:
        comment_data_service._perform_rename_group(
            self.group_id,
            self.old_name,
            self.old_number,
        )

    def notify(self) -> None:
        comment_data_service.comment_group_list_changed.emit()

# --- Tag Database Commands ---
class AddTagDatabaseCommand(Command):
    """Adds a new tag database; undo removes it."""

    def __init__(self, db_data: Dict[str, Any], db_id: Optional[str] = None):
        super().__init__()
        self.db_data: Dict[str, Any] = copy.deepcopy(db_data)
        self.db_id: Optional[str] = db_id

    def redo(self) -> None:
        self.db_id = tag_data_service._perform_add_tag_database(
            self.db_data,
            self.db_id,
        )
        self.db_data['id'] = self.db_id

    def undo(self) -> None:
        if self.db_id:
            tag_data_service._perform_remove_tag_database(self.db_id)

    def notify(self) -> None:
        tag_data_service.database_list_changed.emit()

class RemoveTagDatabaseCommand(Command):
    """Removes a tag database; undo re-adds it."""

    def __init__(self, db_id: str):
        super().__init__()
        self.db_id: str = db_id
        self.db_data: Optional[Dict[str, Any]] = copy.deepcopy(
            tag_data_service.get_tag_database(db_id)
        )

    def redo(self) -> None:
        tag_data_service._perform_remove_tag_database(self.db_id)

    def undo(self) -> None:
        if self.db_data:
            tag_data_service._perform_add_tag_database(self.db_data, self.db_id)

    def notify(self) -> None:
        tag_data_service.database_list_changed.emit()

class RenameTagDatabaseCommand(Command):
    """Renames a tag database; undo restores previous name."""

    def __init__(self, db_id: str, new_name: str, old_name: str):
        super().__init__()
        self.db_id: str = db_id
        self.new_name: str = new_name
        self.old_name: str = old_name

    def redo(self) -> None:
        tag_data_service._perform_rename_tag_database(self.db_id, self.new_name)

    def undo(self) -> None:
        tag_data_service._perform_rename_tag_database(self.db_id, self.old_name)

    def notify(self) -> None:
        tag_data_service.database_list_changed.emit()

# --- Tag Commands ---
class AddTagCommand(Command):
    """Adds a tag to a database; undo removes it."""

    def __init__(self, db_id: str, tag_data: Dict[str, Any]):
        super().__init__()
        self.db_id: str = db_id
        self.tag_data: Dict[str, Any] = copy.deepcopy(tag_data)

    def redo(self) -> None:
        tag_data_service._perform_add_tag(self.db_id, self.tag_data)

    def undo(self) -> None:
        tag_data_service._perform_remove_tag(self.db_id, self.tag_data['name'])

    def notify(self) -> None:
        tag_data_service.tags_changed.emit()
        
class BulkAddTagsCommand(Command):
    """Adds multiple tags; undo removes them."""

    def __init__(self, db_id: str, tags_data: List[Dict[str, Any]]):
        super().__init__()
        self.db_id: str = db_id
        self.tags_data: List[Dict[str, Any]] = copy.deepcopy(tags_data)

    def redo(self) -> None:
        for tag_data in self.tags_data:
            tag_data_service._perform_add_tag(self.db_id, tag_data)

    def undo(self) -> None:
        for tag_data in self.tags_data:
            tag_data_service._perform_remove_tag(self.db_id, tag_data['name'])

    def notify(self) -> None:
        tag_data_service.tags_changed.emit()

class RemoveTagCommand(Command):
    """Removes a tag; undo re-adds it."""

    def __init__(self, db_id: str, tag_name: str):
        super().__init__()
        self.db_id: str = db_id
        self.tag_name: str = tag_name
        self.tag_data: Optional[Dict[str, Any]] = copy.deepcopy(
            tag_data_service.get_tag(db_id, tag_name)
        )

    def redo(self) -> None:
        tag_data_service._perform_remove_tag(self.db_id, self.tag_name)

    def undo(self) -> None:
        if self.tag_data:
            tag_data_service._perform_add_tag(self.db_id, self.tag_data)

    def notify(self) -> None:
        tag_data_service.tags_changed.emit()

class UpdateTagCommand(Command):
    """Updates a tag's data; undo restores the previous tag data."""

    def __init__(self, db_id: str, original_tag_name: str, new_tag_data: Dict[str, Any]):
        super().__init__()
        self.db_id: str = db_id
        self.original_tag_name: str = original_tag_name
        self.new_tag_data: Dict[str, Any] = copy.deepcopy(new_tag_data)
        self.old_tag_data: Optional[Dict[str, Any]] = copy.deepcopy(
            tag_data_service.get_tag(db_id, original_tag_name)
        )

    def redo(self) -> None:
        tag_data_service._perform_update_tag(
            self.db_id,
            self.original_tag_name,
            self.new_tag_data,
        )

    def undo(self) -> None:
        if self.old_tag_data:
            tag_data_service._perform_update_tag(
                self.db_id,
                self.new_tag_data['name'],
                self.old_tag_data,
            )

    def notify(self) -> None:
        tag_data_service.tags_changed.emit()

class UpdateTagValueCommand(Command):
    """Updates a single element value in a tag array; undo restores it."""

    def __init__(self, db_id: str, tag_name: str, indices: List[int], new_value: Any, old_value: Any):
        super().__init__()
        self.db_id: str = db_id
        self.tag_name: str = tag_name
        self.indices: List[int] = indices
        self.new_value: Any = new_value
        self.old_value: Any = old_value

    def redo(self) -> None:
        tag_data_service._perform_update_tag_element_value(
            self.db_id,
            self.tag_name,
            self.indices,
            self.new_value,
        )

    def undo(self) -> None:
        tag_data_service._perform_update_tag_element_value(
            self.db_id,
            self.tag_name,
            self.indices,
            self.old_value,
        )

    def notify(self) -> None:
        tag_data_service.tags_changed.emit()

# --- Comment Table Commands ---
class UpdateCommentCellCommand(Command):
    """Updates a single cell in the comment table model."""

    def __init__(self, model: Any, row: int, col: int, new_value: Any, old_value: Any, notify: Optional[Callable[[], None]]):
        super().__init__()
        self.model: Any = model
        self.row: int = row
        self.col: int = col
        self.new_value: Any = new_value
        self.old_value: Any = old_value
        self._notify_cb: Optional[Callable[[], None]] = notify

    def redo(self) -> None:
        self.model._suspend_history = True
        self.model.setData(self.model.index(self.row, self.col), self.new_value)
        self.model._suspend_history = False

    def undo(self) -> None:
        self.model._suspend_history = True
        self.model.setData(self.model.index(self.row, self.col), self.old_value)
        self.model._suspend_history = False

    def notify(self) -> None:
        if self._notify_cb:
            self._notify_cb()

class UpdateCommentFormatCommand(Command):
    """Updates the format payload for a comment table cell."""

    def __init__(self, model: Any, row: int, col: int, new_fmt: Dict[str, Any], old_fmt: Dict[str, Any], notify: Optional[Callable[[], None]]):
        super().__init__()
        self.model: Any = model
        self.row: int = row
        self.col: int = col
        self.new_fmt: Dict[str, Any] = copy.deepcopy(new_fmt)
        self.old_fmt: Dict[str, Any] = copy.deepcopy(old_fmt)
        self._notify_cb: Optional[Callable[[], None]] = notify

        
    def redo(self) -> None:
        self.model._suspend_history = True
        self.model.set_cell_format(self.row, self.col, self.new_fmt)
        self.model._suspend_history = False

    def undo(self) -> None:
        self.model._suspend_history = True
        self.model.set_cell_format(self.row, self.col, self.old_fmt)
        self.model._suspend_history = False

    def notify(self) -> None:
        if self._notify_cb:
            self._notify_cb()

class InsertCommentRowCommand(Command):
    """Inserts a row with provided values into the comment table."""

    def __init__(self, model: Any, row: int, values: List[Dict[str, Any]], notify: Optional[Callable[[], None]]):
        super().__init__()
        self.model: Any = model
        self.row: int = row
        self.values: List[Dict[str, Any]] = copy.deepcopy(values)
        self._notify_cb: Optional[Callable[[], None]] = notify

    def redo(self) -> None:
        self.model._suspend_history = True
        self.model.insertRow(self.row)
        for c, cell in enumerate(self.values, start=1):
            self.model.setData(self.model.index(self.row, c), cell.get('raw', ''))
            fmt = cell.get('format')
            if fmt:
                self.model.set_cell_format(self.row, c, fmt)
        self.model._suspend_history = False

    def undo(self) -> None:
        self.model._suspend_history = True
        self.model.removeRow(self.row)
        self.model._suspend_history = False

    def notify(self) -> None:
        if self._notify_cb:
            self._notify_cb()

class RemoveCommentRowsCommand(Command):
    """Removes multiple rows from the comment table; undo re-inserts them."""

    def __init__(self, model: Any, rows: List[int], rows_data: List[List[Dict[str, Any]]], notify: Optional[Callable[[], None]]):
        super().__init__()
        self.model: Any = model
        self.rows: List[int] = rows
        self.rows_data: List[List[Dict[str, Any]]] = copy.deepcopy(rows_data)
        self._notify_cb: Optional[Callable[[], None]] = notify

    def redo(self) -> None:
        self.model._suspend_history = True
        for r in sorted(self.rows, reverse=True):
            self.model.removeRow(r)
        self.model._suspend_history = False

    def undo(self) -> None:
        self.model._suspend_history = True
        for r, data in sorted(zip(self.rows, self.rows_data)):
            self.model.insertRow(r)
            for c, cell in enumerate(data, start=1):
                self.model.setData(self.model.index(r, c), cell.get('raw', ''))
                fmt = cell.get('format')
                if fmt:
                    self.model.set_cell_format(r, c, fmt)
        self.model._suspend_history = False

    def notify(self) -> None:
        if self._notify_cb:
            self._notify_cb()

class InsertCommentColumnCommand(Command):
    """Inserts a column into the comment table and updates headers list."""

    def __init__(self, model: Any, column: int, header: str, columns_list: List[str], notify: Optional[Callable[[], None]]):
        super().__init__()
        self.model: Any = model
        self.column: int = column
        self.header: str = header
        self.columns_list: List[str] = columns_list
        self._notify_cb: Optional[Callable[[], None]] = notify

    def redo(self) -> None:
        self.model._suspend_history = True
        self.model.insertColumn(self.column)
        self.model.setHeaderData(
            self.column,
            Qt.Orientation.Horizontal,
            self.header,
        )
        self.model._suspend_history = False
        self.columns_list.insert(self.column - 1, self.header)

    def undo(self) -> None:
        self.model._suspend_history = True
        self.model.removeColumn(self.column)
        self.model._suspend_history = False
        self.columns_list.pop(self.column - 1)

    def notify(self) -> None:
        if self._notify_cb:
            self._notify_cb()

class RemoveCommentColumnCommand(Command):
    """Removes a column from the comment table; undo re-inserts it with data."""

    def __init__(self, model: Any, column: int, header: str, column_data: List[Dict[str, Any]], columns_list: List[str], notify: Optional[Callable[[], None]]):
        super().__init__()
        self.model: Any = model
        self.column: int = column
        self.header: str = header
        self.column_data: List[Dict[str, Any]] = copy.deepcopy(column_data)
        self.columns_list: List[str] = columns_list
        self._notify_cb: Optional[Callable[[], None]] = notify

    def redo(self) -> None:
        self.model._suspend_history = True
        self.model.removeColumn(self.column)
        self.model._suspend_history = False
        self.columns_list.pop(self.column - 1)

    def undo(self) -> None:
        self.model._suspend_history = True
        self.model.insertColumn(self.column)
        self.model.setHeaderData(
            self.column,
            Qt.Orientation.Horizontal,
            self.header,
        )
        for r, cell in enumerate(self.column_data):
            self.model.setData(
                self.model.index(r, self.column),
                cell.get('raw', ''),
            )
            fmt = cell.get('format')
            if fmt:
                self.model.set_cell_format(r, self.column, fmt)
        self.model._suspend_history = False
        self.columns_list.insert(self.column - 1, self.header)

    def notify(self) -> None:
        if self._notify_cb:
            self._notify_cb()

class BulkUpdateCellsCommand(Command):
    """Applies multiple cell value updates in the comment table."""

    def __init__(self, model: Any, updates: List[Tuple[int, int, Any, Any]], notify: Optional[Callable[[], None]]):
        super().__init__()
        self.model: Any = model
        self.updates: List[Tuple[int, int, Any, Any]] = updates
        self._notify_cb: Optional[Callable[[], None]] = notify

    def redo(self) -> None:
        self.model._suspend_history = True
        for row, col, new_val, _ in self.updates:
            self.model.setData(self.model.index(row, col), new_val)
        self.model._suspend_history = False

    def undo(self) -> None:
        self.model._suspend_history = True
        for row, col, _, old_val in self.updates:
            self.model.setData(self.model.index(row, col), old_val)
        self.model._suspend_history = False

    def notify(self) -> None:
        if self._notify_cb:
            self._notify_cb()
