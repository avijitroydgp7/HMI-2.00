"""
Property Editor package

This package hosts the main `PropertyEditor` widget and a set of
tool-specific editor helpers under this directory. Each tool editor
exposes two functions:

- build(host): returns a QWidget for editing that tool's properties.
- update_fields(widget, props): updates the widget's inputs from props
  with signals blocked to avoid feedback loops.

Factory mapping in `factory.py` selects the correct helper based on
`utils.constants.ToolType`. To add a new tool editor, create a
`<tool>_editor.py` here with `build` and `update_fields`, and register it
in `factory.get_editor`.
"""

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QStackedWidget,
    QLabel,
    QLineEdit,
)
from PyQt6.QtCore import pyqtSlot
from dataclasses import dataclass
from typing import Callable, Dict
from contextlib import contextmanager
import copy
from services.screen_data_service import screen_service
from services.data_context import data_context
from utils import constants
from utils.editing_guard import EditingGuard
from .factory import get_editor

# Module-level tool imports (dispatch via mapping below)
from tools import button as button_tool
from tools import line as line_tool
from tools import text as text_tool
from tools import polygon as polygon_tool
from tools import image as image_tool
from tools import scale as scale_tool


@dataclass(frozen=True)
class ToolSchema:
    """Schema describing how to handle a specific tool type in the editor."""
    type_id: str
    defaults_fn: Callable[[dict], dict]  # incoming props -> merged props with defaults
    editor_builder: Callable[[], QWidget]  # bound method that builds the editor widget


class PropertyEditor(QStackedWidget):
    """Property panel that displays and edits object properties by tool type."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_object_id = None
        self.current_parent_id = None
        self.current_properties = {}
        self.current_tool_type = None
        self.active_tool = constants.ToolType.SELECT
        # Guard to avoid refresh loops while applying edits
        self._is_editing = False
        # Tool schema registry
        self._schemas: Dict[object, ToolSchema] = {}

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

        # Refresh properties when the underlying screen data changes
        data_context.screens_changed.connect(self._handle_screen_event)

        # Initialize tool schema registry
        self._init_schemas()

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
            constants.ToolType.LINE: ToolSchema(
                constants.ToolType.LINE.value,
                lambda incoming: self._merge_properties(
                    line_tool.get_default_properties(), incoming
                ),
                lambda: get_editor(constants.ToolType.LINE).build(self),
            ),
            constants.ToolType.TEXT: ToolSchema(
                constants.ToolType.TEXT.value,
                lambda incoming: self._merge_properties(
                    text_tool.get_default_properties(), incoming
                ),
                lambda: get_editor(constants.ToolType.TEXT).build(self),
            ),
            constants.ToolType.POLYGON: ToolSchema(
                constants.ToolType.POLYGON.value,
                lambda incoming: self._merge_properties(
                    polygon_tool.get_default_properties(), incoming
                ),
                lambda: get_editor(constants.ToolType.POLYGON).build(self),
            ),
            constants.ToolType.IMAGE: ToolSchema(
                constants.ToolType.IMAGE.value,
                lambda incoming: self._merge_properties(
                    image_tool.get_default_properties(incoming.get("path", "")),
                    incoming,
                ),
                lambda: get_editor(constants.ToolType.IMAGE).build(self),
            ),
            constants.ToolType.SCALE: ToolSchema(
                constants.ToolType.SCALE.value,
                lambda incoming: self._merge_properties(
                    scale_tool.get_default_properties(), incoming
                ),
                lambda: get_editor(constants.ToolType.SCALE).build(self),
            ),
        }

    @contextmanager
    def _editing_context(self):
        """Backward-compatible contextmanager using the explicit EditingGuard."""
        guard = self._begin_edit()
        try:
            yield guard.mark_changed
        finally:
            guard.end()

    @pyqtSlot(str)
    def _on_screen_modified(self, screen_id: str):
        """Refresh the editor when the parent screen's data changes."""
        # Skip refreshes while we are applying a local edit
        if getattr(self, "_is_editing", False):
            return
        if screen_id != self.current_parent_id:
            return
        if self.current_object_id:
            instance = screen_service.get_child_instance(
                self.current_parent_id, self.current_object_id
            )
            if instance is not None:
                # Pass only minimal fields and deep copy properties to avoid shared mutations
                minimal = {
                    "instance_id": instance.get("instance_id"),
                    "tool_type": instance.get("tool_type"),
                    "properties": copy.deepcopy(instance.get("properties") or {}),
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
            if self._handle_multi_select(selection_data):
                return
            elif len(selection_data) == 1:
                selection_data = selection_data[0]
            else:  # Empty list
                self.set_current_object(None, None)
                return

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
            return

        # Build editor using schema
        self._build_editor(
            new_tool_type, incoming_props, restore_name, restore_cursor
        )

    # --- Helpers extracted from set_current_object ---
    def _clear_selection(self) -> None:
        self.current_object_id = None
        self.current_parent_id = None
        self.current_properties = {}
        self.current_tool_type = None
        # Clear editor widget if it exists
        if self.count() > 2:
            old_widget = self.widget(2)
            self.removeWidget(old_widget)
            old_widget.deleteLater()
        self.setCurrentWidget(self.blank_page)

    def _handle_multi_select(self, selection_list) -> bool:
        if len(selection_list) > 1:
            # Multi-select; show dedicated page and clear tracking
            self.setCurrentWidget(self.multi_select_page)
            self.current_object_id = None
            self.current_parent_id = None
            self.current_properties = {}
            self.current_tool_type = None
            # Clear editor widget if it exists
            if self.count() > 2:
                old_widget = self.widget(2)
                self.removeWidget(old_widget)
                old_widget.deleteLater()
            return True
        return False

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
            adapter.update_fields(editor, props)
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
        merged = defaults.copy() if isinstance(defaults, dict) else dict(defaults or {})
        if incoming:
            merged.update(incoming)
        return merged
