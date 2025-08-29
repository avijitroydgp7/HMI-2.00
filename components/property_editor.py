# components/property_editor.py
# A property editor panel that displays and allows editing of object properties.

from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QStackedWidget,
    QLabel,
    QFormLayout,
    QLineEdit,
    QComboBox,
)
from PyQt6.QtGui import QIcon
from PyQt6.QtCore import pyqtSlot, QSignalBlocker, QTimer
from dataclasses import dataclass
from typing import Callable, Dict
from contextlib import contextmanager
import copy
from services.command_history_service import command_history_service
# FIX: Removed unused MoveChildCommand import
from services.commands import UpdateChildPropertiesCommand
from services.screen_data_service import screen_service
from utils import constants
from utils.editing_guard import EditingGuard


@dataclass(frozen=True)
class ToolSchema:
    """Schema describing how to handle a specific tool type in the editor."""
    type_id: str
    defaults_fn: Callable[[dict], dict]  # incoming props -> merged props with defaults
    editor_builder: Callable[[], QWidget]  # bound method that builds the editor widget

class PropertyEditor(QStackedWidget):
    """
    A widget that displays a property editor for the currently selected object.
    It shows different editors based on the type of object selected.
    """
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
        screen_service.screen_modified.connect(self._on_screen_modified)

        # Initialize tool schema registry
        self._init_schemas()

    # --- Utility: explicit begin/end edit guard ---
    def _active_canvas_widget(self):
        try:
            win = self.window()
            if hasattr(win, 'tab_widget'):
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

        return EditingGuard(self, screen_service, active_widget=active_widget, emit_final=_emit_final).begin()

    def _init_schemas(self):
        """Build the tool schema registry to reduce branching."""
        def _merge(defaults: dict, incoming: dict) -> dict:
            merged = copy.deepcopy(defaults)
            merged.update(incoming or {})
            return merged

        # Lazily import inside closures to avoid import cycles at module import time
        def _button_defaults(incoming: dict) -> dict:
            from tools import button as _button
            return _merge(_button.get_default_properties(), incoming)

        def _line_defaults(incoming: dict) -> dict:
            from tools import line as _line
            return _merge(_line.get_default_properties(), incoming)

        def _text_defaults(incoming: dict) -> dict:
            from tools import text as _text
            return _merge(_text.get_default_properties(), incoming)

        def _polygon_defaults(incoming: dict) -> dict:
            from tools import polygon as _polygon
            return _merge(_polygon.get_default_properties(), incoming)

        def _image_defaults(incoming: dict) -> dict:
            from tools import image as _image
            return _merge(_image.get_default_properties(incoming.get('path', '')), incoming)

        def _scale_defaults(incoming: dict) -> dict:
            from tools import scale as _scale
            return _merge(_scale.get_default_properties(), incoming)

        self._schemas = {
            constants.ToolType.BUTTON: ToolSchema(constants.ToolType.BUTTON.value, _button_defaults, self._create_button_editor),
            constants.ToolType.LINE: ToolSchema(constants.ToolType.LINE.value, _line_defaults, self._create_line_editor),
            constants.ToolType.TEXT: ToolSchema(constants.ToolType.TEXT.value, _text_defaults, self._create_text_editor),
            constants.ToolType.POLYGON: ToolSchema(constants.ToolType.POLYGON.value, _polygon_defaults, self._create_polygon_editor),
            constants.ToolType.IMAGE: ToolSchema(constants.ToolType.IMAGE.value, _image_defaults, self._create_image_editor),
            constants.ToolType.SCALE: ToolSchema(constants.ToolType.SCALE.value, _scale_defaults, self._create_scale_editor),
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
                self.set_current_object(self.current_parent_id, copy.deepcopy(instance))
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
        """
        Sets the currently selected object(s) to be edited.
        """
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
        new_instance_id = selection_data.get('instance_id')
        new_parent_id = parent_id
        new_tool_type = None
        if 'screen_id' in selection_data:
            new_tool_type = 'screen'
        elif 'tool_type' in selection_data:
            new_tool_type = constants.tool_type_from_str(selection_data.get('tool_type'))

        # Decide if selection truly changed (different object or type)
        selection_changed = (
            new_instance_id != self.current_object_id
            or new_parent_id != self.current_parent_id
            or new_tool_type != self.current_tool_type
        )

        # Properties from selection (raw)
        incoming_props = selection_data.get('properties', {}) if new_tool_type and new_tool_type != 'screen' else {}

        # Capture currently focused line edit so we can restore caret after rebuild/update
        restore_name = None
        restore_cursor = None
        try:
            fw = self.window().focusWidget()
            if isinstance(fw, QLineEdit) and self.isAncestorOf(fw):
                restore_name = fw.objectName() or None
                try:
                    restore_cursor = fw.cursorPosition()
                except Exception:
                    restore_cursor = None
        except Exception:
            restore_name = None
            restore_cursor = None

        if not selection_changed and new_tool_type and new_tool_type != 'screen':
            # Same object/type: update properties and refresh existing widgets in place
            # Ensure we look up by ToolType when possible
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
                    target = editor.findChild(QLineEdit, restore_name)
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

        if new_tool_type == 'screen' or not new_tool_type:
            # Show placeholder for screens or unknown types
            self.current_properties = {}
            self.setCurrentWidget(self.blank_page)
            return

        # Build editor using schema
        self._build_editor_for_instance(new_tool_type, incoming_props, restore_name, restore_cursor)

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

    def _build_editor_for_instance(self, tool_type, incoming_props: dict, restore_name=None, restore_cursor=None):
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
                target = editor.findChild(QLineEdit, restore_name)
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

    def _update_editor_fields(self, tool_type, props: dict):
        """Update existing editor widgets in place based on new props.
        Signals are blocked during programmatic updates to avoid feedback loops.
        """
        editor = self.widget(2) if self.count() > 2 else None
        if editor is None:
            return

        def _set_line(name: str, value: str):
            w = editor.findChild(QLineEdit, name)
            if w is not None:
                blocker = QSignalBlocker(w)
                try:
                    w.setText(str(value))
                finally:
                    del blocker

        def _set_combo(name: str, text_value: str = None, data_value=None):
            from PyQt6.QtWidgets import QComboBox as _QComboBox
            w = editor.findChild(_QComboBox, name)
            if w is not None:
                blocker = QSignalBlocker(w)
                try:
                    if data_value is not None:
                        idx = w.findData(data_value)
                        if idx != -1:
                            w.setCurrentIndex(idx)
                    elif text_value is not None:
                        w.setCurrentText(text_value)
                finally:
                    del blocker

        if tool_type == constants.ToolType.BUTTON:
            _set_line('label', props.get('label', ''))
            _set_line('background_color', props.get('background_color', ''))
            _set_line('text_color', props.get('text_color', ''))
            _set_combo('style_id', data_value=props.get('style_id'))
        elif tool_type == constants.ToolType.LINE:
            start = props.get('start', {})
            end = props.get('end', {})
            _set_line('start.x', start.get('x', 0))
            _set_line('start.y', start.get('y', 0))
            _set_line('end.x', end.get('x', 0))
            _set_line('end.y', end.get('y', 0))
            _set_line('color', props.get('color', ''))
            _set_line('width', props.get('width', 0))
            _set_line('style', props.get('style', ''))
        elif tool_type == constants.ToolType.TEXT:
            font = props.get('font', {})
            _set_line('content', props.get('content', ''))
            _set_line('font.family', font.get('family', ''))
            _set_line('font.size', font.get('size', 0))
            _set_combo('font.bold', text_value='True' if font.get('bold') else 'False')
            _set_combo('font.italic', text_value='True' if font.get('italic') else 'False')
            _set_line('color', props.get('color', ''))
        elif tool_type == constants.ToolType.POLYGON:
            _set_line('fill_color', props.get('fill_color', ''))
            _set_line('stroke_color', props.get('stroke_color', ''))
            _set_line('stroke_width', props.get('stroke_width', 0))
            _set_line('stroke_style', props.get('stroke_style', ''))
        elif tool_type == constants.ToolType.IMAGE:
            size = props.get('size', {})
            _set_line('path', props.get('path', ''))
            _set_line('size.width', size.get('width', 0))
            _set_line('size.height', size.get('height', 0))
        elif tool_type == constants.ToolType.SCALE:
            _set_combo('orientation', text_value=props.get('orientation', 'horizontal'))
            _set_line('length', props.get('length', 0))
            _set_line('thickness', props.get('thickness', 0))
            _set_line('major_ticks', props.get('major_ticks', 0))
            _set_line('minor_ticks', props.get('minor_ticks', 0))
            _set_line('tick_spacing', props.get('tick_spacing', 0))
            _set_line('units', props.get('units', ''))
            _set_line('color', props.get('color', ''))


    def _create_button_editor(self):
        """Creates a property editor widget specifically for buttons."""
        from tools import button
        from tools.button import conditional_style as button_styles

        editor_widget = QWidget()
        layout = QFormLayout(editor_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        label_edit = QLineEdit(self.current_properties.get("label", ""))
        label_edit.setObjectName('label')
        style_combo = QComboBox()
        style_combo.setObjectName('style_id')
        styles = button_styles.get_styles()
        for style in styles:
            icon_path = style.get('icon') or style.get('svg_icon')
            if icon_path:
                style_combo.addItem(QIcon(icon_path), style['name'], style['id'])
            else:
                style_combo.addItem(style['name'], style['id'])
        
        current_style_id = self.current_properties.get("style_id", "default_rounded")
        index = style_combo.findData(current_style_id)
        if index != -1:
            style_combo.setCurrentIndex(index)
        
        bg_color_edit = QLineEdit(self.current_properties.get("background_color", ""))
        bg_color_edit.setObjectName('background_color')
        text_color_edit = QLineEdit(self.current_properties.get("text_color", ""))
        text_color_edit.setObjectName('text_color')

        layout.addRow("Label:", label_edit)
        layout.addRow("Style:", style_combo)
        layout.addRow("Background Color:", bg_color_edit)
        layout.addRow("Text Color:", text_color_edit)

        # Update UI fields that are derived from a style definition
        def _apply_style_field_updates(style_id: str):
            style_def = button_styles.get_style_by_id(style_id) or {}
            style_props = style_def.get('properties', {})
            # Block signals to avoid recursive emissions while programmatically updating
            blocker_bg = QSignalBlocker(bg_color_edit)
            blocker_text = QSignalBlocker(text_color_edit)
            try:
                bg_color_edit.setText(style_props.get('background_color', ''))
                text_color_edit.setText(style_props.get('text_color', ''))
            finally:
                # Explicitly delete blockers to restore signal state now
                del blocker_bg
                del blocker_text

        def on_property_changed():
            guard = self._begin_edit()
            try:
                new_props = copy.deepcopy(self.current_properties)
                new_props["label"] = label_edit.text()
                new_props["background_color"] = bg_color_edit.text()
                new_props["text_color"] = text_color_edit.text()

                selected_style_id = style_combo.currentData()
                if selected_style_id != new_props.get('style_id'):
                    new_props['style_id'] = selected_style_id
                    style_def = button_styles.get_style_by_id(selected_style_id)
                    new_props.update(style_def['properties'])
                    if 'hover_properties' in style_def:
                        new_props['hover_properties'] = copy.deepcopy(style_def['hover_properties'])
                    if 'click_properties' in style_def:
                        new_props['click_properties'] = copy.deepcopy(style_def['click_properties'])
                    if style_def.get('icon'):
                        new_props['icon'] = style_def['icon']
                    if style_def.get('hover_icon'):
                        new_props['hover_icon'] = style_def['hover_icon']
                    if style_def.get('click_icon'):
                        new_props['click_icon'] = style_def['click_icon']

                if new_props != self.current_properties:
                    if self.current_object_id:
                        command = UpdateChildPropertiesCommand(
                            self.current_parent_id,
                            self.current_object_id,
                            new_props,
                            self.current_properties,
                        )
                        command_history_service.add_command(command)
                        guard.mark_changed()
                    else:
                        button.set_default_properties(new_props)
                    self.current_properties = new_props
            finally:
                guard.end()
        
        label_edit.editingFinished.connect(on_property_changed)
        # When style changes, first update derived UI fields, then apply property change
        def _on_style_activated(_=None):
            selected_style_id = style_combo.currentData()
            _apply_style_field_updates(selected_style_id)
            on_property_changed()
        style_combo.activated.connect(_on_style_activated)
        bg_color_edit.editingFinished.connect(on_property_changed)
        text_color_edit.editingFinished.connect(on_property_changed)

        return editor_widget

    def _create_line_editor(self):
        """Creates a property editor widget for lines."""
        from tools import line as line_tool

        editor_widget = QWidget()
        layout = QFormLayout(editor_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        start_x = QLineEdit(str(self.current_properties.get('start', {}).get('x', 0)))
        start_x.setObjectName('start.x')
        start_y = QLineEdit(str(self.current_properties.get('start', {}).get('y', 0)))
        start_y.setObjectName('start.y')
        end_x = QLineEdit(str(self.current_properties.get('end', {}).get('x', 0)))
        end_x.setObjectName('end.x')
        end_y = QLineEdit(str(self.current_properties.get('end', {}).get('y', 0)))
        end_y.setObjectName('end.y')
        color_edit = QLineEdit(self.current_properties.get('color', ''))
        color_edit.setObjectName('color')
        width_edit = QLineEdit(str(self.current_properties.get('width', 0)))
        width_edit.setObjectName('width')
        style_edit = QLineEdit(self.current_properties.get('style', ''))
        style_edit.setObjectName('style')

        layout.addRow('Start X:', start_x)
        layout.addRow('Start Y:', start_y)
        layout.addRow('End X:', end_x)
        layout.addRow('End Y:', end_y)
        layout.addRow('Color:', color_edit)
        layout.addRow('Width:', width_edit)
        layout.addRow('Style:', style_edit)

        def on_property_changed():
            guard = self._begin_edit()
            try:
                new_props = copy.deepcopy(self.current_properties)
                new_props['start'] = {
                    'x': int(start_x.text() or 0),
                    'y': int(start_y.text() or 0),
                }
                new_props['end'] = {
                    'x': int(end_x.text() or 0),
                    'y': int(end_y.text() or 0),
                }
                new_props['color'] = color_edit.text()
                new_props['width'] = int(width_edit.text() or 0)
                new_props['style'] = style_edit.text()
                if new_props != self.current_properties:
                    if self.current_object_id:
                        command = UpdateChildPropertiesCommand(
                            self.current_parent_id,
                            self.current_object_id,
                            new_props,
                            self.current_properties,
                        )
                        command_history_service.add_command(command)
                        guard.mark_changed()
                    else:
                        line_tool.set_default_properties(new_props)
                    self.current_properties = new_props
            finally:
                guard.end()

        for widget in (start_x, start_y, end_x, end_y, color_edit, width_edit, style_edit):
            widget.editingFinished.connect(on_property_changed)

        return editor_widget

    def _create_text_editor(self):
        """Creates a property editor widget for text."""
        from tools import text as text_tool

        editor_widget = QWidget()
        layout = QFormLayout(editor_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        content_edit = QLineEdit(self.current_properties.get('content', ''))
        content_edit.setObjectName('content')
        font_family = QLineEdit(self.current_properties.get('font', {}).get('family', ''))
        font_family.setObjectName('font.family')
        font_size = QLineEdit(str(self.current_properties.get('font', {}).get('size', 0)))
        font_size.setObjectName('font.size')
        bold_combo = QComboBox()
        bold_combo.setObjectName('font.bold')
        bold_combo.addItems(['False', 'True'])
        bold_combo.setCurrentText('True' if self.current_properties.get('font', {}).get('bold') else 'False')
        italic_combo = QComboBox()
        italic_combo.setObjectName('font.italic')
        italic_combo.addItems(['False', 'True'])
        italic_combo.setCurrentText('True' if self.current_properties.get('font', {}).get('italic') else 'False')
        color_edit = QLineEdit(self.current_properties.get('color', ''))
        color_edit.setObjectName('color')

        layout.addRow('Content:', content_edit)
        layout.addRow('Font Family:', font_family)
        layout.addRow('Font Size:', font_size)
        layout.addRow('Bold:', bold_combo)
        layout.addRow('Italic:', italic_combo)
        layout.addRow('Color:', color_edit)

        def on_property_changed():
            guard = self._begin_edit()
            try:
                new_props = copy.deepcopy(self.current_properties)
                new_props['content'] = content_edit.text()
                new_props['font'] = {
                    'family': font_family.text(),
                    'size': int(font_size.text() or 0),
                    'bold': bold_combo.currentText() == 'True',
                    'italic': italic_combo.currentText() == 'True',
                }
                new_props['color'] = color_edit.text()
                if new_props != self.current_properties:
                    if self.current_object_id:
                        command = UpdateChildPropertiesCommand(
                            self.current_parent_id,
                            self.current_object_id,
                            new_props,
                            self.current_properties,
                        )
                        command_history_service.add_command(command)
                        guard.mark_changed()
                    else:
                        text_tool.set_default_properties(new_props)
                    self.current_properties = new_props
            finally:
                guard.end()

        content_edit.editingFinished.connect(on_property_changed)
        font_family.editingFinished.connect(on_property_changed)
        font_size.editingFinished.connect(on_property_changed)
        bold_combo.activated.connect(lambda _=None: on_property_changed())
        italic_combo.activated.connect(lambda _=None: on_property_changed())
        color_edit.editingFinished.connect(on_property_changed)

        return editor_widget

    def _create_polygon_editor(self):
        """Creates a property editor widget for polygons."""
        from tools import polygon as polygon_tool

        editor_widget = QWidget()
        layout = QFormLayout(editor_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        fill_color = QLineEdit(self.current_properties.get('fill_color', ''))
        fill_color.setObjectName('fill_color')
        stroke_color = QLineEdit(self.current_properties.get('stroke_color', ''))
        stroke_color.setObjectName('stroke_color')
        stroke_width = QLineEdit(str(self.current_properties.get('stroke_width', 0)))
        stroke_width.setObjectName('stroke_width')
        stroke_style = QLineEdit(self.current_properties.get('stroke_style', ''))
        stroke_style.setObjectName('stroke_style')

        layout.addRow('Fill Color:', fill_color)
        layout.addRow('Stroke Color:', stroke_color)
        layout.addRow('Stroke Width:', stroke_width)
        layout.addRow('Stroke Style:', stroke_style)

        def on_property_changed():
            guard = self._begin_edit()
            try:
                new_props = copy.deepcopy(self.current_properties)
                new_props['fill_color'] = fill_color.text()
                new_props['stroke_color'] = stroke_color.text()
                new_props['stroke_width'] = int(stroke_width.text() or 0)
                new_props['stroke_style'] = stroke_style.text()
                if new_props != self.current_properties:
                    if self.current_object_id:
                        command = UpdateChildPropertiesCommand(
                            self.current_parent_id,
                            self.current_object_id,
                            new_props,
                            self.current_properties,
                        )
                        command_history_service.add_command(command)
                        guard.mark_changed()
                    else:
                        polygon_tool.set_default_properties(new_props)
                    self.current_properties = new_props
            finally:
                guard.end()

        for widget in (fill_color, stroke_color, stroke_width, stroke_style):
            widget.editingFinished.connect(on_property_changed)

        return editor_widget

    def _create_image_editor(self):
        """Creates a property editor widget for images."""
        from tools import image as image_tool

        editor_widget = QWidget()
        layout = QFormLayout(editor_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        path_edit = QLineEdit(self.current_properties.get('path', ''))
        path_edit.setObjectName('path')
        width_edit = QLineEdit(str(self.current_properties.get('size', {}).get('width', 0)))
        width_edit.setObjectName('size.width')
        height_edit = QLineEdit(str(self.current_properties.get('size', {}).get('height', 0)))
        height_edit.setObjectName('size.height')

        layout.addRow('Path:', path_edit)
        layout.addRow('Width:', width_edit)
        layout.addRow('Height:', height_edit)

        def on_property_changed():
            guard = self._begin_edit()
            try:
                new_props = copy.deepcopy(self.current_properties)
                new_props['path'] = path_edit.text()
                new_props['size'] = {
                    'width': int(width_edit.text() or 0),
                    'height': int(height_edit.text() or 0),
                }
                if new_props != self.current_properties:
                    if self.current_object_id:
                        command = UpdateChildPropertiesCommand(
                            self.current_parent_id,
                            self.current_object_id,
                            new_props,
                            self.current_properties,
                        )
                        command_history_service.add_command(command)
                        guard.mark_changed()
                    else:
                        image_tool.set_default_properties(new_props)
                    self.current_properties = new_props
            finally:
                guard.end()

        for widget in (path_edit, width_edit, height_edit):
            widget.editingFinished.connect(on_property_changed)

        return editor_widget

    def _create_scale_editor(self):
        """Creates a property editor widget for scales."""
        from tools import scale as scale_tool

        editor_widget = QWidget()
        layout = QFormLayout(editor_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        orientation_combo = QComboBox()
        orientation_combo.setObjectName('orientation')
        orientation_combo.addItems(['horizontal', 'vertical'])
        orientation_combo.setCurrentText(self.current_properties.get('orientation', 'horizontal'))
        length_edit = QLineEdit(str(self.current_properties.get('length', 0)))
        length_edit.setObjectName('length')
        thickness_edit = QLineEdit(str(self.current_properties.get('thickness', 0)))
        thickness_edit.setObjectName('thickness')
        major_ticks = QLineEdit(str(self.current_properties.get('major_ticks', 0)))
        major_ticks.setObjectName('major_ticks')
        minor_ticks = QLineEdit(str(self.current_properties.get('minor_ticks', 0)))
        minor_ticks.setObjectName('minor_ticks')
        tick_spacing = QLineEdit(str(self.current_properties.get('tick_spacing', 0)))
        tick_spacing.setObjectName('tick_spacing')
        units_edit = QLineEdit(self.current_properties.get('units', ''))
        units_edit.setObjectName('units')
        color_edit = QLineEdit(self.current_properties.get('color', ''))
        color_edit.setObjectName('color')

        layout.addRow('Orientation:', orientation_combo)
        layout.addRow('Length:', length_edit)
        layout.addRow('Thickness:', thickness_edit)
        layout.addRow('Major Ticks:', major_ticks)
        layout.addRow('Minor Ticks:', minor_ticks)
        layout.addRow('Tick Spacing:', tick_spacing)
        layout.addRow('Units:', units_edit)
        layout.addRow('Color:', color_edit)

        def on_property_changed():
            guard = self._begin_edit()
            try:
                new_props = copy.deepcopy(self.current_properties)
                new_props['orientation'] = orientation_combo.currentText()
                new_props['length'] = int(length_edit.text() or 0)
                new_props['thickness'] = int(thickness_edit.text() or 0)
                new_props['major_ticks'] = int(major_ticks.text() or 0)
                new_props['minor_ticks'] = int(minor_ticks.text() or 0)
                new_props['tick_spacing'] = int(tick_spacing.text() or 0)
                new_props['units'] = units_edit.text()
                new_props['color'] = color_edit.text()
                if new_props != self.current_properties:
                    if self.current_object_id:
                        command = UpdateChildPropertiesCommand(
                            self.current_parent_id,
                            self.current_object_id,
                            new_props,
                            self.current_properties,
                        )
                        command_history_service.add_command(command)
                        guard.mark_changed()
                    else:
                        scale_tool.set_default_properties(new_props)
                    self.current_properties = new_props
            finally:
                guard.end()

        orientation_combo.activated.connect(lambda _=None: on_property_changed())
        for widget in (
            length_edit,
            thickness_edit,
            major_ticks,
            minor_ticks,
            tick_spacing,
            units_edit,
            color_edit,
        ):
            widget.editingFinished.connect(on_property_changed)

        return editor_widget
