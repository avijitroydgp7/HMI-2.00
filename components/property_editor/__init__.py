"""
Property Editor package
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QStackedWidget,
    QLabel,
    QLineEdit,
    QFormLayout,
    QSpinBox,
)
from PyQt6.QtCore import pyqtSlot
from dataclasses import dataclass
from typing import Callable, Dict
import copy
from services.screen_data_service import screen_service
from services.data_context import data_context
from utils import constants
from utils.editing_guard import EditingGuard
from services.command_history_service import command_history_service
from services.commands import MoveChildCommand, UpdateChildPropertiesCommand
from .factory import get_editor

# Module-level tool imports (dispatch via mapping below)
from tools import button as button_tool


@dataclass(frozen=True)
class ToolSchema:
    """Schema describing how to handle a specific tool type in the editor."""
    type_id: str
    defaults_fn: Callable[[dict], dict]  # incoming props -> merged props with defaults
    editor_builder: Callable[[], QWidget]  # bound method that builds the editor widget


class PropertyEditor(QWidget):
    """Property panel that displays and edits object properties by tool type."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_object_id = None
        self.current_parent_id = None
        self.current_properties = {}
        self.current_tool_type = None
        self.active_tool = constants.ToolType.SELECT
        # Track current geometry for command emission
        self.current_position = {"x": 0, "y": 0}
        self.current_size = {"width": 0, "height": 0}
        # Guard to avoid refresh loops while applying edits
        self._is_editing = False
        # Tool schema registry
        self._schemas: Dict[object, ToolSchema] = {}

        # Layout wrapper around the stacked widget so we can place a geometry form above
        root_layout = QVBoxLayout(self)

        # --- Geometry Form ---
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
        root_layout.addWidget(self.geometry_form)

        # Connect geometry edits
        self.x_spin.valueChanged.connect(lambda v: self._on_position_changed("x", v))
        self.y_spin.valueChanged.connect(lambda v: self._on_position_changed("y", v))
        self.width_spin.valueChanged.connect(lambda v: self._on_size_changed("width", v))
        self.height_spin.valueChanged.connect(lambda v: self._on_size_changed("height", v))

        # --- Stacked Widget for tool-specific editors ---
        self.stack = QStackedWidget()
        root_layout.addWidget(self.stack)

        # --- Create Pages ---
        self.blank_page = QWidget()
        self.blank_page_layout = QVBoxLayout(self.blank_page)
        self.blank_page_layout.addWidget(QLabel("No object selected."))

        self.multi_select_page = QWidget()
        multi_layout = QVBoxLayout(self.multi_select_page)
        multi_layout.addWidget(QLabel("Multiple objects selected."))

        self.addWidget(self.blank_page)
        self.addWidget(self.multi_select_page)

        self.setCurrentWidget(self.blank_page)
        self._update_geometry_fields(None)

        # Refresh properties when the underlying screen data changes
        data_context.screens_changed.connect(self._handle_screen_event)

        # Initialize tool schema registry
        self._init_schemas()

    # --- Geometry helpers ---
    def _block_geometry_signals(self, block: bool) -> None:
        for sb in (self.x_spin, self.y_spin, self.width_spin, self.height_spin):
            sb.blockSignals(block)

    def _update_geometry_fields(self, selection_data):
        """Refresh the geometry spin boxes based on selection_data.

        If selection_data is None or represents multi-selection, the fields are disabled.
        """
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
                self.current_parent_id,
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
                self.current_parent_id,
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

    # --- Proxies to mimic QStackedWidget API ---
    def addWidget(self, widget):
        return self.stack.addWidget(widget)

    def removeWidget(self, widget):
        self.stack.removeWidget(widget)

    def setCurrentWidget(self, widget):
        self.stack.setCurrentWidget(widget)

    def widget(self, index):
        return self.stack.widget(index)

    def count(self):
        return self.stack.count()

    # --- Utility: explicit begin/end edit guard ---
    def _active_canvas_widget(self):
        try:
            win = self.window()
            if hasattr(win, "tab_widget"):
                return win.tab_widget.currentWidget()
        except Exception:
            return None
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

    def _handle_screen_event(self, event: dict):
        """Dispatch screen events from the shared data context."""
        if event.get("action") == "screen_modified":
            self._on_screen_modified(event.get("screen_id", ""))

    def _init_schemas(self):
        """Build the tool schema registry to reduce branching."""
        self._schemas = {
            constants.ToolType.BUTTON: ToolSchema(
                constants.ToolType.BUTTON.value,
                lambda incoming: self._merge_properties(
                    button_tool.get_default_properties(), incoming
                ),
                lambda: get_editor(constants.ToolType.BUTTON).build(self),
            ),
        }

    @pyqtSlot(str)
    def _on_screen_modified(self, screen_id: str):
        """Refresh the editor when the parent screen's data changes."""
        # Skip refreshes while we are applying a local edit
        if getattr(self, "_is_editing", False):
            return
        if screen_id != self.current_parent_id:
            return
        if self.current_object_id:
            if isinstance(self.current_object_id, list):
                selection = []
                for iid in self.current_object_id:
                    instance = screen_service.get_child_instance(
                        self.current_parent_id, iid
                    )
                    if instance is not None:
                        selection.append(
                            {
                                "instance_id": instance.get("instance_id"),
                                "tool_type": instance.get("tool_type"),
                                "properties": copy.deepcopy(
                                    instance.get("properties") or {}
                                ),
                            }
                        )
                if selection:
                    self.set_current_object(self.current_parent_id, selection)
                else:
                    self.set_current_object(None, None)
            else:
                instance = screen_service.get_child_instance(
                    self.current_parent_id, self.current_object_id
                )
                if instance is not None:
                    minimal = {
                        "instance_id": instance.get("instance_id"),
                        "tool_type": instance.get("tool_type"),
                        "properties": copy.deepcopy(
                            instance.get("properties") or {}
                        ),
                    }
                    self.set_current_object(self.current_parent_id, minimal)
                else:
                    self.set_current_object(None, None)

    def set_active_tool(self, tool_id):
        """Update the active tool."""
        # Accept either ToolType or string identifiers
        self.active_tool = constants.tool_type_from_str(tool_id) or tool_id
        if self.current_object_id is None:
            self.setCurrentWidget(self.blank_page)

    @pyqtSlot(str, object)
    def set_current_object(self, parent_id: str, selection_data: object):
        """Sets the currently selected object(s) to be edited."""
        # If we are in the middle of applying an edit from the editor,
        # skip rebuilding the editor to avoid re-entrancy/refresh loops.
        if getattr(self, "_is_editing", False):
            return
        # Normalize selection_data
        if not selection_data:
            self._clear_selection()
            return

        if isinstance(selection_data, list):
            if self._handle_multi_select(parent_id, selection_data):
                return
            elif len(selection_data) == 1:
                selection_data = selection_data[0]
            else:  # Empty list
                self.set_current_object(None, None)
                return

        # Update geometry fields for the single selection
        self._update_geometry_fields(selection_data)

        # Extract targets
        new_instance_id = selection_data.get("instance_id")
        new_parent_id = parent_id
        new_tool_type = None
        if "screen_id" in selection_data:
            new_tool_type = "screen"
        elif "tool_type" in selection_data:
            new_tool_type = constants.tool_type_from_str(selection_data.get("tool_type"))

        # Decide if selection truly changed (different object or type)
        selection_changed = (
            new_instance_id != self.current_object_id
            or new_parent_id != self.current_parent_id
            or new_tool_type != self.current_tool_type
        )

        # Properties from selection (raw)
        incoming_props = (
            selection_data.get("properties", {})
            if new_tool_type and new_tool_type != "screen"
            else {}
        )

        # Capture currently focused line edit so we can restore caret after rebuild/update
        restore_name = None
        restore_cursor = None
        try:
            from PyQt6.QtWidgets import QLineEdit as _QLineEdit

            fw = self.window().focusWidget()
            if isinstance(fw, _QLineEdit) and self.isAncestorOf(fw):
                restore_name = fw.objectName() or None
                try:
                    restore_cursor = fw.cursorPosition()
                except Exception:
                    restore_cursor = None
        except Exception:
            restore_name = None
            restore_cursor = None

        if not selection_changed and new_tool_type and new_tool_type != "screen":
            # Same object/type: update properties and refresh existing widgets in place
            schema = self._schemas.get(new_tool_type)
            if schema is not None:
                merged = schema.defaults_fn(incoming_props)
                self.current_properties = merged
                # Update existing input widgets without rebuilding
                self._update_editor_fields(new_tool_type, merged)
            else:
                # Fallback to incoming properties if unknown type
                self.current_properties = incoming_props or {}

            # Attempt to restore caret position in focused line edit
            if restore_name:
                editor = self.widget(2) if self.count() > 2 else None
                if editor is not None:
                    from PyQt6.QtWidgets import QLineEdit as _QLineEdit

                    target = editor.findChild(_QLineEdit, restore_name)
                    if target is not None and restore_cursor is not None:
                        try:
                            pos = min(restore_cursor, len(target.text()))
                            target.setCursorPosition(pos)
                        except Exception:
                            pass
            # Ensure geometry reflects latest selection
            self._update_geometry_fields(selection_data)
            return

        # Selection changed or it's a screen: rebuild editor view accordingly
        # First, clear previous editor if it exists
        if self.count() > 2:
            old_widget = self.widget(2)
            self.removeWidget(old_widget)
            old_widget.deleteLater()

        # Update tracked selection
        self.current_object_id = new_instance_id
        self.current_parent_id = new_parent_id
        self.current_tool_type = new_tool_type

        if new_tool_type == "screen" or not new_tool_type:
            # Show placeholder for screens or unknown types
            self.current_properties = {}
            self.setCurrentWidget(self.blank_page)
            self._update_geometry_fields(selection_data)
            return

        # Build editor using schema
        self._build_editor(
            new_tool_type, incoming_props, restore_name, restore_cursor
        )
        self._update_geometry_fields(selection_data)

    # --- Helpers extracted from set_current_object ---
    def _clear_selection(self) -> None:
        self.current_object_id = None
        self.current_parent_id = None
        self.current_properties = {}
        self.current_tool_type = None
        self._update_geometry_fields(None)
        # Clear editor widget if it exists
        if self.count() > 2:
            old_widget = self.widget(2)
            self.removeWidget(old_widget)
            old_widget.deleteLater()
        self.setCurrentWidget(self.blank_page)

    def _handle_multi_select(self, parent_id, selection_list) -> bool:
        if len(selection_list) <= 1:
            return False

        tool_types = {
            constants.tool_type_from_str(sel.get("tool_type"))
            for sel in selection_list
            if sel.get("tool_type")
        }
        if len(tool_types) != 1:
            # Different tool types; show placeholder
            self.setCurrentWidget(self.multi_select_page)
            self.current_object_id = None
            self.current_parent_id = None
            self.current_properties = {}
            self.current_tool_type = None
            self._update_geometry_fields(None)
            if self.count() > 2:
                old_widget = self.widget(2)
                self.removeWidget(old_widget)
                old_widget.deleteLater()
            return True

        tool_type = next(iter(tool_types))
        schema = self._schemas.get(tool_type)
        if schema is None:
            self.setCurrentWidget(self.multi_select_page)
            self.current_object_id = None
            self.current_parent_id = None
            self.current_properties = {}
            self.current_tool_type = None
            self._update_geometry_fields(None)
            if self.count() > 2:
                old_widget = self.widget(2)
                self.removeWidget(old_widget)
                old_widget.deleteLater()
            return True

        ids = [sel.get("instance_id") for sel in selection_list if sel.get("instance_id")]
        props_list = [
            schema.defaults_fn(sel.get("properties") or {}) for sel in selection_list
        ]

        def _merge(dicts):
            keys = set().union(*(d.keys() for d in dicts))
            merged = {}
            for k in keys:
                values = [d.get(k) for d in dicts]
                first = values[0]
                if all(v == first for v in values):
                    if isinstance(first, dict):
                        merged[k] = _merge(values)  # type: ignore[arg-type]
                    else:
                        merged[k] = copy.deepcopy(first)
                else:
                    if None not in values and all(
                        isinstance(v, dict) for v in values
                    ):
                        merged[k] = _merge(values)  # type: ignore[arg-type]
                    else:
                        merged[k] = None
            return merged

        merged_props = _merge(props_list)

        # Replace existing editor if present
        if self.count() > 2:
            old_widget = self.widget(2)
            self.removeWidget(old_widget)
            old_widget.deleteLater()

        self.current_object_id = ids
        self.current_parent_id = parent_id
        self.current_tool_type = tool_type
        self._update_geometry_fields(None)
        self._build_editor(tool_type, merged_props)
        return True

    def _build_editor(
        self, tool_type, incoming_props: dict, restore_name=None, restore_cursor=None
    ):
        schema = self._schemas.get(tool_type)
        if schema is None:
            self.current_properties = {}
            self.setCurrentWidget(self.blank_page)
            return None
        props = schema.defaults_fn(incoming_props)
        self.current_properties = props
        editor = schema.editor_builder()
        if editor:
            self.addWidget(editor)
            self.setCurrentWidget(editor)
            # Try to restore focus to the same logical field
            if restore_name:
                from PyQt6.QtWidgets import QLineEdit as _QLineEdit

                target = editor.findChild(_QLineEdit, restore_name)
                if target is not None:
                    target.setFocus()
                    if restore_cursor is not None:
                        try:
                            # Clamp cursor to current text length
                            pos = min(restore_cursor, len(target.text()))
                            target.setCursorPosition(pos)
                        except Exception:
                            pass
            return editor
        self.setCurrentWidget(self.blank_page)
        return None

    # Backward compatibility: some code/tests expect this legacy helper name
    def _build_editor_for_instance(self, tool_type, incoming_props: dict):
        """Compatibility wrapper for building an editor for a given tool type."""
        return self._build_editor(tool_type, incoming_props)

    def _update_editor_fields(self, tool_type, props: dict):
        """Update existing editor widgets in place based on new props.
        Signals are blocked during programmatic updates to avoid feedback loops.
        """
        editor = self.widget(2) if self.count() > 2 else None
        if editor is None:
            return
        adapter = get_editor(tool_type)
        if adapter is not None:
            adapter.update_fields(editor, props or {})
        # If adapter is None, do nothing (unknown tool)

    # --- Property merging helper ---
    def _merge_properties(self, defaults: dict, incoming: dict | None) -> dict:
        """Merge incoming properties over defaults with minimal copying.

        Assumptions:
        - Default getters in tools.* already return fresh copies, so we avoid
          extra deep copies here.
        - We perform a shallow overlay; nested dicts are replaced if provided
          by incoming, matching prior behavior.
        """
        merged = copy.deepcopy(defaults) if isinstance(defaults, dict) else dict(defaults or {})
        if not incoming:
            return merged

        def _recurse(base: dict, inc: dict):
            for k, v in inc.items():
                if isinstance(v, dict) and isinstance(base.get(k), dict):
                    _recurse(base[k], v)
                else:
                    base[k] = copy.deepcopy(v)

        _recurse(merged, incoming)
        return merged
