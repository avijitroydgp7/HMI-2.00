# components/property_editor.py
# A property editor panel that displays and allows editing of object properties.

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QStackedWidget, QLabel, QFormLayout, 
    QLineEdit, QComboBox
)
from PyQt6.QtCore import pyqtSlot
import copy
from services.command_history_service import command_history_service
# FIX: Removed unused MoveChildCommand import
from services.commands import UpdateChildPropertiesCommand

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
            self.setCurrentWidget(self.blank_page)
            self.current_object_id = None
            self.current_parent_id = None
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
            self.current_properties = selection_data.get('properties', {})
            tool_type = selection_data.get('tool_type')
            if tool_type == 'button':
                editor = self._create_button_editor()
                self.addWidget(editor)
                self.setCurrentWidget(editor)
            else:
                self.setCurrentWidget(self.blank_page)
        else:
            self.setCurrentWidget(self.blank_page)


    def _create_button_editor(self):
        """Creates a property editor widget specifically for buttons."""
        from tools import button_styles
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
                command = UpdateChildPropertiesCommand(
                    self.current_parent_id, 
                    self.current_object_id, 
                    new_props, 
                    self.current_properties
                )
                command_history_service.add_command(command)
        
        label_edit.editingFinished.connect(on_property_changed)
        style_combo.currentIndexChanged.connect(on_property_changed)
        bg_color_edit.editingFinished.connect(on_property_changed)
        text_color_edit.editingFinished.connect(on_property_changed)

        return editor_widget
