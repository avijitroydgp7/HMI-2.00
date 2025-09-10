"""Property editors for HMI objects.

This module provides property editors for HMI objects:
- PropertyEditor: Basic property editor showing geometry fields
- ButtonTreePropertyEditor: Advanced tree-based property editor with inline editing capabilities
"""

from __future__ import annotations

import copy

from PyQt6.QtCore import pyqtSlot
from PyQt6.QtWidgets import (
    QFormLayout, QSpinBox, QVBoxLayout, QWidget,
    QStackedWidget
)

from services.command_history_service import command_history_service
from services.commands import MoveChildCommand, UpdateChildPropertiesCommand
from services.data_context import data_context
from services.screen_data_service import screen_service
from utils.editing_guard import EditingGuard
from utils import constants


class PropertyEditor(QWidget):
    """Property editor that uses specialized editors for different object types.
    
    This editor automatically switches between:
    - Basic geometry editor for standard objects
    - Specialized button editor for button objects
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_object_id: str | None = None
        self.current_parent_id: str | None = None
        self.current_properties: dict = {}
        self.current_position = {"x": 0, "y": 0}
        self.current_size = {"width": 0, "height": 0}
        self._is_editing = False

        # Create main layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create editor stack to switch between different editors
        self.editor_stack = QStackedWidget(self)
        layout.addWidget(self.editor_stack)
        
        # Create basic geometry editor
        self.basic_editor = QWidget()
        basic_layout = QVBoxLayout(self.basic_editor)
        form_layout = QFormLayout()
        self.x_spin = QSpinBox()
        self.y_spin = QSpinBox()
        self.width_spin = QSpinBox()
        self.height_spin = QSpinBox()
        for sb in (self.x_spin, self.y_spin):
            sb.setRange(-100000, 100000)
        for sb in (self.width_spin, self.height_spin):
            sb.setRange(0, 100000)
        form_layout.addRow("X", self.x_spin)
        form_layout.addRow("Y", self.y_spin)
        form_layout.addRow("W", self.width_spin)
        form_layout.addRow("H", self.height_spin)
        self.geometry_form = QWidget()
        self.geometry_form.setLayout(form_layout)
        basic_layout.addWidget(self.geometry_form)
        
        # Create tree editor (will be created later to avoid circular imports)
        self.button_editor = None
        
        # Add basic editor to stack
        self.editor_stack.addWidget(self.basic_editor)
        
        # Set initial editor
        self.editor_stack.setCurrentWidget(self.basic_editor)
        
        # We'll add the button editor later after initialization

        # Connect signals
        self.x_spin.valueChanged.connect(lambda v: self._on_position_changed("x", v))
        self.y_spin.valueChanged.connect(lambda v: self._on_position_changed("y", v))
        self.width_spin.valueChanged.connect(lambda v: self._on_size_changed("width", v))
        self.height_spin.valueChanged.connect(lambda v: self._on_size_changed("height", v))

        self._update_geometry_fields(None)
        data_context.screens_changed.connect(self._handle_screen_event)

    # ------------------------------------------------------------------
    # Geometry helpers
    def _block_geometry_signals(self, block: bool) -> None:
        for sb in (self.x_spin, self.y_spin, self.width_spin, self.height_spin):
            sb.blockSignals(block)

    def _update_geometry_fields(self, selection_data) -> None:
        if not selection_data or isinstance(selection_data, list):
            self._block_geometry_signals(True)
            self.x_spin.setValue(0)
            self.y_spin.setValue(0)
            self.width_spin.setValue(0)
            self.height_spin.setValue(0)
            self._block_geometry_signals(False)
            self.geometry_form.setDisabled(True)
            self.current_position = {"x": 0, "y": 0}
            self.current_size = {"width": 0, "height": 0}
            return

        pos = selection_data.get("position") or selection_data.get("properties", {}).get("position", {})
        size = selection_data.get("properties", {}).get("size", {})
        x = int(pos.get("x", 0) or 0)
        y = int(pos.get("y", 0) or 0)
        w = int(size.get("width", 0) or 0)
        h = int(size.get("height", 0) or 0)

        self.geometry_form.setDisabled(False)
        self._block_geometry_signals(True)
        self.x_spin.setValue(x)
        self.y_spin.setValue(y)
        self.width_spin.setValue(w)
        self.height_spin.setValue(h)
        self._block_geometry_signals(False)
        self.current_position = {"x": x, "y": y}
        self.current_size = {"width": w, "height": h}

    def _on_position_changed(self, key: str, value: int) -> None:
        if not self.current_object_id or isinstance(self.current_object_id, list):
            return
        old_pos = dict(self.current_position)
        if old_pos.get(key) == value:
            return
        new_pos = dict(old_pos)
        new_pos[key] = value
        guard = self._begin_edit()
        try:
            command = MoveChildCommand(
                str(self.current_parent_id) if self.current_parent_id else "",
                self.current_object_id,
                new_pos,
                old_pos,
            )
            command_history_service.add_command(command)
            guard.mark_changed()
            self.current_position = new_pos
        finally:
            guard.end()

    def _on_size_changed(self, key: str, value: int) -> None:
        if not self.current_object_id or isinstance(self.current_object_id, list):
            return
        old_props = copy.deepcopy(self.current_properties)
        new_props = copy.deepcopy(self.current_properties)
        size = new_props.setdefault("size", {})
        if size.get(key) == value:
            return
        size[key] = value
        guard = self._begin_edit()
        try:
            command = UpdateChildPropertiesCommand(
                str(self.current_parent_id) if self.current_parent_id else "",
                self.current_object_id,
                new_props,
                old_props,
            )
            command_history_service.add_command(command)
            guard.mark_changed()
            self.current_properties = new_props
            self.current_size = size
        finally:
            guard.end()

    # ------------------------------------------------------------------
    # Editing guards
    def _active_canvas_widget(self):
        try:
            win = self.window()
            if win and hasattr(win, "tab_widget"):
                tab_widget = getattr(win, "tab_widget")
                if tab_widget:
                    return tab_widget.currentWidget()
        except Exception:
            pass
        return None

    def _begin_edit(self) -> EditingGuard:
        active_widget = self._active_canvas_widget()

        def _emit_final():
            try:
                if self.current_parent_id and self.current_object_id:
                    screen_service.screen_modified.emit(self.current_parent_id)
            except Exception:
                pass

        return EditingGuard(
            self, screen_service, active_widget=active_widget, emit_final=_emit_final
        ).begin()

    # ------------------------------------------------------------------
    # External API
    def _handle_screen_event(self, event: dict) -> None:
        if event.get("action") == "screen_modified":
            self._on_screen_modified(event.get("screen_id", ""))

    def _on_screen_modified(self, screen_id: str) -> None:
        if self._is_editing or screen_id != self.current_parent_id or not self.current_object_id:
            return
        instance = screen_service.get_child_instance(
            self.current_parent_id, self.current_object_id
        )
        if instance is not None:
            selection = {
                "instance_id": instance.get("instance_id"),
                "properties": copy.deepcopy(instance.get("properties") or {}),
                "position": instance.get("position") or {},
            }
            self.current_properties = selection.get("properties", {})
            self._update_geometry_fields(selection)
        else:
            self._clear_selection()

    def _clear_selection(self) -> None:
        self.current_object_id = None
        self.current_parent_id = None
        self.current_properties = {}
        self._update_geometry_fields(None)

    @pyqtSlot(str, object)
    def set_current_object(self, parent_id: str, selection_data: object) -> None:
        if self._is_editing:
            return
        if not selection_data:
            self._clear_selection()
            return
        if isinstance(selection_data, list):
            if len(selection_data) == 1:
                selection_data = selection_data[0]
            else:
                self._clear_selection()
                return
                
        # Store basic info using safer approach
        try:
            # Try dictionary access first
            if isinstance(selection_data, dict):
                self.current_object_id = selection_data.get("instance_id")
                props = selection_data.get("properties", {})
                self.current_properties = copy.deepcopy(props) if props else {}
            # Fall back to attribute access
            elif hasattr(selection_data, "instance_id"):
                self.current_object_id = getattr(selection_data, "instance_id")
                if hasattr(selection_data, "properties"):
                    props = getattr(selection_data, "properties") or {}
                    self.current_properties = copy.deepcopy(props)
                else:
                    self.current_properties = {}
            else:
                self.current_object_id = None
                self.current_properties = {}
                
            self.current_parent_id = parent_id
        except Exception:
            self.current_object_id = None
            self.current_parent_id = parent_id
            self.current_properties = {}
        
        # Convert to dictionary for safer handling
        selection_dict = {}
        if isinstance(selection_data, dict):
            selection_dict = selection_data
        else:
            # Try to extract attributes if it's an object
            try:
                if hasattr(selection_data, "instance_id"):
                    selection_dict["instance_id"] = getattr(selection_data, "instance_id")
                if hasattr(selection_data, "tool_id"):
                    selection_dict["tool_id"] = getattr(selection_data, "tool_id")
                if hasattr(selection_data, "tool_type"):
                    selection_dict["tool_type"] = getattr(selection_data, "tool_type")
                if hasattr(selection_data, "properties"):
                    selection_dict["properties"] = getattr(selection_data, "properties")
            except Exception:
                pass
                
        # Check if this is a button (support both legacy 'tool_id' and enum 'tool_type')
        tool_id = selection_dict.get("tool_id", "")
        tool_type_val = selection_dict.get("tool_type")
        tool_type = constants.tool_type_from_str(tool_type_val) if tool_type_val is not None else None
        is_button = (
            (isinstance(tool_id, str) and tool_id.startswith("button"))
            or (tool_type == constants.ToolType.BUTTON)
        )
        
        # Initialize tree editor if needed
        if is_button and self.button_editor is None:
            # Import here to avoid circular imports
            from .button_property_editor import ButtonTreePropertyEditor
            self.button_editor = ButtonTreePropertyEditor(self)
            self.editor_stack.addWidget(self.button_editor)
        
        if is_button and self.button_editor is not None:
            # Use specialized tree editor
            self.editor_stack.setCurrentWidget(self.button_editor)
            self.button_editor.set_current_object(parent_id, selection_data)
        else:
            # Use basic geometry editor
            self.editor_stack.setCurrentWidget(self.basic_editor)
            self._update_geometry_fields(selection_data)

    def set_active_tool(self, tool_id) -> None:  # compatibility stub
        pass

