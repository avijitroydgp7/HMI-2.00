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
from PyQt6.QtCore import pyqtSlot
import copy
from services.command_history_service import command_history_service
# FIX: Removed unused MoveChildCommand import
from services.commands import UpdateChildPropertiesCommand
from utils import constants

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
        self.active_tool = constants.TOOL_SELECT

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

    def set_active_tool(self, tool_id: str):
        """Update the active tool and show its default properties when appropriate."""
        self.active_tool = tool_id
        if self.current_object_id is None:
            self._show_active_tool_defaults()

    def _show_active_tool_defaults(self):
        """Display the editor for the active tool's default properties."""
        # Remove any existing editor page beyond the default ones
        if self.count() > 2:
            old_widget = self.widget(2)
            self.removeWidget(old_widget)
            old_widget.deleteLater()

        if self.active_tool == constants.TOOL_SELECT:
            self.setCurrentWidget(self.blank_page)
            return

        editor = None
        if self.active_tool == constants.TOOL_BUTTON:
            from tools import button

            self.current_properties = button.get_default_properties()
            editor = self._create_button_editor()
        elif self.active_tool == constants.TOOL_LINE:
            from tools import line as line_tool

            self.current_properties = line_tool.get_default_properties()
            editor = self._create_line_editor()
        elif self.active_tool == constants.TOOL_TEXT:
            from tools import text as text_tool

            self.current_properties = text_tool.get_default_properties()
            editor = self._create_text_editor()
        elif self.active_tool == constants.TOOL_POLYGON:
            from tools import polygon as polygon_tool

            self.current_properties = polygon_tool.get_default_properties()
            editor = self._create_polygon_editor()
        elif self.active_tool == constants.TOOL_IMAGE:
            from tools import image as image_tool

            self.current_properties = image_tool.get_default_properties("")
            editor = self._create_image_editor()
        elif self.active_tool == constants.TOOL_SCALE:
            from tools import scale as scale_tool

            self.current_properties = scale_tool.get_default_properties()
            editor = self._create_scale_editor()

        if editor:
            self.addWidget(editor)
            self.setCurrentWidget(editor)
        else:
            self.setCurrentWidget(self.blank_page)
    @pyqtSlot(str, object)
    def set_current_object(self, parent_id: str, selection_data: object):
        """
        Sets the currently selected object(s) to be edited.
        """
        # Clear previous editor if it exists
        if self.count() > 2:
            old_widget = self.widget(2)
            self.removeWidget(old_widget)
            old_widget.deleteLater()

        if not selection_data:
            self.current_object_id = None
            self.current_parent_id = None
            self.current_properties = {}
            self._show_active_tool_defaults()
            return

        if isinstance(selection_data, list):
            if len(selection_data) > 1:
                self.setCurrentWidget(self.multi_select_page)
                self.current_object_id = None
                self.current_parent_id = None
                return
            elif len(selection_data) == 1:
                selection_data = selection_data[0]
            else: # Empty list
                self.set_current_object(None, None)
                return
        
        self.current_object_id = selection_data.get('instance_id')
        self.current_parent_id = parent_id
        
        if 'screen_id' in selection_data:
            # This is an embedded screen, which has different properties
            # For now, show a placeholder
            self.setCurrentWidget(self.blank_page)
        elif 'tool_type' in selection_data:
            tool_type = selection_data.get('tool_type')
            self.current_properties = selection_data.get('properties', {})

            editor = None
            if tool_type == 'button':
                from tools import button

                default_props = button.get_default_properties()
                props = copy.deepcopy(default_props)
                props.update(self.current_properties)
                self.current_properties = props
                editor = self._create_button_editor()
            elif tool_type == 'line':
                from tools import line as line_tool

                default_props = line_tool.get_default_properties()
                props = copy.deepcopy(default_props)
                props.update(self.current_properties)
                self.current_properties = props
                editor = self._create_line_editor()
            elif tool_type == 'text':
                from tools import text as text_tool

                default_props = text_tool.get_default_properties()
                props = copy.deepcopy(default_props)
                props.update(self.current_properties)
                self.current_properties = props
                editor = self._create_text_editor()
            elif tool_type == 'polygon':
                from tools import polygon as polygon_tool

                default_props = polygon_tool.get_default_properties()
                props = copy.deepcopy(default_props)
                props.update(self.current_properties)
                self.current_properties = props
                editor = self._create_polygon_editor()
            elif tool_type == 'image':
                from tools import image as image_tool

                default_props = image_tool.get_default_properties(
                    self.current_properties.get('path', '')
                )
                props = copy.deepcopy(default_props)
                props.update(self.current_properties)
                self.current_properties = props
                editor = self._create_image_editor()
            elif tool_type == 'scale':
                from tools import scale as scale_tool

                default_props = scale_tool.get_default_properties()
                props = copy.deepcopy(default_props)
                props.update(self.current_properties)
                self.current_properties = props
                editor = self._create_scale_editor()

            if editor:
                self.addWidget(editor)
                self.setCurrentWidget(editor)
            else:
                self.setCurrentWidget(self.blank_page)
        else:
            self.setCurrentWidget(self.blank_page)


    def _create_button_editor(self):
        """Creates a property editor widget specifically for buttons."""
        from tools import button, button_styles

        editor_widget = QWidget()
        layout = QFormLayout(editor_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        label_edit = QLineEdit(self.current_properties.get("label", ""))
        style_combo = QComboBox()
        styles = button_styles.get_styles()
        for style in styles:
            style_combo.addItem(style['name'], style['id'])
        
        current_style_id = self.current_properties.get("style_id", "default_rounded")
        index = style_combo.findData(current_style_id)
        if index != -1:
            style_combo.setCurrentIndex(index)
        
        bg_color_edit = QLineEdit(self.current_properties.get("background_color", ""))
        text_color_edit = QLineEdit(self.current_properties.get("text_color", ""))

        layout.addRow("Label:", label_edit)
        layout.addRow("Style:", style_combo)
        layout.addRow("Background Color:", bg_color_edit)
        layout.addRow("Text Color:", text_color_edit)

        def on_property_changed():
            new_props = copy.deepcopy(self.current_properties)
            new_props["label"] = label_edit.text()
            new_props["background_color"] = bg_color_edit.text()
            new_props["text_color"] = text_color_edit.text()
            
            selected_style_id = style_combo.currentData()
            if selected_style_id != new_props.get('style_id'):
                new_props['style_id'] = selected_style_id
                style_def = button_styles.get_style_by_id(selected_style_id)
                new_props.update(style_def['properties'])
                # Update UI to reflect style change
                bg_color_edit.setText(new_props['background_color'])
                text_color_edit.setText(new_props['text_color'])

            if new_props != self.current_properties:
                if self.current_object_id:
                    command = UpdateChildPropertiesCommand(
                        self.current_parent_id,
                        self.current_object_id,
                        new_props,
                        self.current_properties,
                    )
                    command_history_service.add_command(command)
                else:
                    button.set_default_properties(new_props)
                self.current_properties = new_props
        
        label_edit.editingFinished.connect(on_property_changed)
        style_combo.currentIndexChanged.connect(on_property_changed)
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
        start_y = QLineEdit(str(self.current_properties.get('start', {}).get('y', 0)))
        end_x = QLineEdit(str(self.current_properties.get('end', {}).get('x', 0)))
        end_y = QLineEdit(str(self.current_properties.get('end', {}).get('y', 0)))
        color_edit = QLineEdit(self.current_properties.get('color', ''))
        width_edit = QLineEdit(str(self.current_properties.get('width', 0)))
        style_edit = QLineEdit(self.current_properties.get('style', ''))

        layout.addRow('Start X:', start_x)
        layout.addRow('Start Y:', start_y)
        layout.addRow('End X:', end_x)
        layout.addRow('End Y:', end_y)
        layout.addRow('Color:', color_edit)
        layout.addRow('Width:', width_edit)
        layout.addRow('Style:', style_edit)

        def on_property_changed():
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
                else:
                    line_tool.set_default_properties(new_props)
                self.current_properties = new_props

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
        font_family = QLineEdit(self.current_properties.get('font', {}).get('family', ''))
        font_size = QLineEdit(str(self.current_properties.get('font', {}).get('size', 0)))
        bold_combo = QComboBox()
        bold_combo.addItems(['False', 'True'])
        bold_combo.setCurrentText('True' if self.current_properties.get('font', {}).get('bold') else 'False')
        italic_combo = QComboBox()
        italic_combo.addItems(['False', 'True'])
        italic_combo.setCurrentText('True' if self.current_properties.get('font', {}).get('italic') else 'False')
        color_edit = QLineEdit(self.current_properties.get('color', ''))

        layout.addRow('Content:', content_edit)
        layout.addRow('Font Family:', font_family)
        layout.addRow('Font Size:', font_size)
        layout.addRow('Bold:', bold_combo)
        layout.addRow('Italic:', italic_combo)
        layout.addRow('Color:', color_edit)

        def on_property_changed():
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
                else:
                    text_tool.set_default_properties(new_props)
                self.current_properties = new_props

        content_edit.editingFinished.connect(on_property_changed)
        font_family.editingFinished.connect(on_property_changed)
        font_size.editingFinished.connect(on_property_changed)
        bold_combo.currentIndexChanged.connect(on_property_changed)
        italic_combo.currentIndexChanged.connect(on_property_changed)
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
        stroke_color = QLineEdit(self.current_properties.get('stroke_color', ''))
        stroke_width = QLineEdit(str(self.current_properties.get('stroke_width', 0)))
        stroke_style = QLineEdit(self.current_properties.get('stroke_style', ''))

        layout.addRow('Fill Color:', fill_color)
        layout.addRow('Stroke Color:', stroke_color)
        layout.addRow('Stroke Width:', stroke_width)
        layout.addRow('Stroke Style:', stroke_style)

        def on_property_changed():
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
                else:
                    polygon_tool.set_default_properties(new_props)
                self.current_properties = new_props

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
        width_edit = QLineEdit(str(self.current_properties.get('size', {}).get('width', 0)))
        height_edit = QLineEdit(str(self.current_properties.get('size', {}).get('height', 0)))

        layout.addRow('Path:', path_edit)
        layout.addRow('Width:', width_edit)
        layout.addRow('Height:', height_edit)

        def on_property_changed():
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
                else:
                    image_tool.set_default_properties(new_props)
                self.current_properties = new_props

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
        orientation_combo.addItems(['horizontal', 'vertical'])
        orientation_combo.setCurrentText(self.current_properties.get('orientation', 'horizontal'))
        length_edit = QLineEdit(str(self.current_properties.get('length', 0)))
        thickness_edit = QLineEdit(str(self.current_properties.get('thickness', 0)))
        major_ticks = QLineEdit(str(self.current_properties.get('major_ticks', 0)))
        minor_ticks = QLineEdit(str(self.current_properties.get('minor_ticks', 0)))
        tick_spacing = QLineEdit(str(self.current_properties.get('tick_spacing', 0)))
        units_edit = QLineEdit(self.current_properties.get('units', ''))
        color_edit = QLineEdit(self.current_properties.get('color', ''))

        layout.addRow('Orientation:', orientation_combo)
        layout.addRow('Length:', length_edit)
        layout.addRow('Thickness:', thickness_edit)
        layout.addRow('Major Ticks:', major_ticks)
        layout.addRow('Minor Ticks:', minor_ticks)
        layout.addRow('Tick Spacing:', tick_spacing)
        layout.addRow('Units:', units_edit)
        layout.addRow('Color:', color_edit)

        def on_property_changed():
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
                else:
                    scale_tool.set_default_properties(new_props)
                self.current_properties = new_props

        orientation_combo.currentIndexChanged.connect(on_property_changed)
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