"""Tree-based property editor with inline editing capabilities."""

from __future__ import annotations

import copy
from typing import Dict, Any, Optional, List, Union, Callable, cast

from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal, QSize
from PyQt6.QtWidgets import (
    QVBoxLayout, QWidget, QTreeWidget, QTreeWidgetItem, QStyledItemDelegate,
    QSpinBox, QDoubleSpinBox, QLineEdit, QColorDialog, QComboBox,
    QCheckBox, QPushButton, QHBoxLayout, QLabel, QStyle, QApplication
)
from PyQt6.QtGui import QColor, QBrush, QFont, QPainter, QIcon

from dialogs.widgets import TagSelector

from services.command_history_service import command_history_service
from services.commands import UpdateChildPropertiesCommand, MoveChildCommand
from services.data_context import data_context
from services.screen_data_service import screen_service
from utils.editing_guard import EditingGuard
from utils import constants


class InlinePropertyEditor:
    """Helper class to manage inline editing for property tree items."""
    
    def __init__(self, tree_widget: QTreeWidget):
        self.tree_widget = tree_widget
        self.setup_editing_connections()
    
    def setup_editing_connections(self):
        """Set up connections for inline editing."""
        self.tree_widget.itemDoubleClicked.connect(self._on_item_double_clicked)
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Handle double click on tree items to show appropriate editor."""
        if column != 1 or not item:
            return
            
        property_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not property_path:
            return
            
        current_value = item.data(1, Qt.ItemDataRole.UserRole)
        if current_value is None:
            current_value = item.text(1)
        
        # Determine property type
        if property_path in ["x", "y", "width", "height", "w", "h", "border_width", "font_size", "icon_size"]:
            self._edit_int_property(item, property_path, current_value)
        elif property_path in ["component_type"]:
            options = ["Standard Button", "Toggle Switch", "Selector", "Toggle Button", "Tab Button", "Arrow Button"]
            self._edit_enum_property(item, property_path, current_value, options)
        elif property_path in ["shape_style"]:
            options = ["Flat", "3D", "Glass", "Outline"]
            self._edit_enum_property(item, property_path, current_value, options)
        elif property_path in ["background_type"]:
            options = ["Solid", "Gradient"]
            self._edit_enum_property(item, property_path, current_value, options)
        elif property_path in ["border_style"]:
            options = ["none", "solid", "dashed", "dotted", "double", "groove", "ridge"]
            self._edit_enum_property(item, property_path, current_value, options)
        elif property_path in ["font_family"]:
            options = ["Arial", "Helvetica", "Times New Roman", "Courier New", "Verdana", "Tahoma", "Calibri"]
            self._edit_enum_property(item, property_path, current_value, options)
        elif property_path in ["icon_align"]:
            options = ["left", "center", "right"]
            self._edit_enum_property(item, property_path, current_value, options)
        elif property_path in ["font_bold", "font_italic", "font_underline"]:
            self._edit_bool_property(item, property_path, current_value)
        elif property_path in ["background_color", "text_color", "border_color", "icon_color"]:
            self._edit_color_property(item, property_path, current_value)
        elif property_path.split('.')[-1] in ["tag", "tag_path", "target_tag"]:
            self._edit_tag_property(item, property_path, current_value)
        else:
            # Default to text editor
            self._edit_text_property(item, property_path, current_value)
    
    def _edit_int_property(self, item: QTreeWidgetItem, property_path: str, current_value: str):
        """Show integer editor for number properties."""
        try:
            value = int(current_value) if current_value else 0
        except ValueError:
            value = 0
        
        # Create temp widget to hold the spinbox
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        spinbox = QSpinBox(container)
        spinbox.setRange(-100000, 100000)
        spinbox.setValue(value)
        
        # Special cases for specific properties
        if property_path in ["border_width", "font_size", "icon_size"]:
            spinbox.setRange(0, 100)
            spinbox.setSuffix("%")
        elif property_path in ["width", "height"]:
            spinbox.setRange(0, 100000)
        
        layout.addWidget(spinbox)
        
        # Add buttons
        ok_button = QPushButton("OK", container)
        ok_button.setFixedWidth(40)
        layout.addWidget(ok_button)
        
        cancel_button = QPushButton("Cancel", container)
        cancel_button.setFixedWidth(60)
        layout.addWidget(cancel_button)
        
        # Set up container
        self.tree_widget.setItemWidget(item, 1, container)
        
        # Connect signals
        def apply_value():
            new_value = str(spinbox.value())
            self.tree_widget.setItemWidget(item, 1, None)
            item.setText(1, new_value)
            self.tree_widget.itemChanged.emit(item, 1)
        
        def cancel_edit():
            self.tree_widget.setItemWidget(item, 1, None)
        
        ok_button.clicked.connect(apply_value)
        cancel_button.clicked.connect(cancel_edit)
        spinbox.editingFinished.connect(apply_value)
    
    def _edit_text_property(self, item: QTreeWidgetItem, property_path: str, current_value: str):
        """Show text editor for string properties."""
        # Create temp widget to hold the edit field
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        line_edit = QLineEdit(container)
        line_edit.setText(current_value)
        layout.addWidget(line_edit)
        
        # Add buttons
        ok_button = QPushButton("OK", container)
        ok_button.setFixedWidth(40)
        layout.addWidget(ok_button)
        
        cancel_button = QPushButton("Cancel", container)
        cancel_button.setFixedWidth(60)
        layout.addWidget(cancel_button)
        
        # Set up container
        self.tree_widget.setItemWidget(item, 1, container)
        
        # Connect signals
        def apply_value():
            new_value = line_edit.text()
            self.tree_widget.setItemWidget(item, 1, None)
            item.setText(1, new_value)
            self.tree_widget.itemChanged.emit(item, 1)
        
        def cancel_edit():
            self.tree_widget.setItemWidget(item, 1, None)
        
        ok_button.clicked.connect(apply_value)
        cancel_button.clicked.connect(cancel_edit)
        line_edit.editingFinished.connect(apply_value)
    
    def _edit_enum_property(self, item: QTreeWidgetItem, property_path: str, current_value: str, options: list):
        """Show combo box editor for enum properties."""
        # Create temp widget to hold the combo box
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        combo = QComboBox(container)
        combo.addItems(options)
        if current_value in options:
            combo.setCurrentText(current_value)
        layout.addWidget(combo)
        
        # Add buttons
        ok_button = QPushButton("OK", container)
        ok_button.setFixedWidth(40)
        layout.addWidget(ok_button)
        
        cancel_button = QPushButton("Cancel", container)
        cancel_button.setFixedWidth(60)
        layout.addWidget(cancel_button)
        
        # Set up container
        self.tree_widget.setItemWidget(item, 1, container)
        
        # Connect signals
        def apply_value():
            new_value = combo.currentText()
            self.tree_widget.setItemWidget(item, 1, None)
            item.setText(1, new_value)
            self.tree_widget.itemChanged.emit(item, 1)
        
        def cancel_edit():
            self.tree_widget.setItemWidget(item, 1, None)
        
        ok_button.clicked.connect(apply_value)
        cancel_button.clicked.connect(cancel_edit)
        combo.activated.connect(apply_value)  # Apply when user selects an item

    def _format_tag_display(self, data: Optional[Dict[str, Any]]) -> str:
        """Create a string representation for tag selector data."""
        if not data:
            return ""
        main_tag = data.get("main_tag", {})
        main_val = main_tag.get("value") if isinstance(main_tag, dict) else None
        display = ""
        if isinstance(main_val, dict):
            db = main_val.get("db_name", "")
            tag = main_val.get("tag_name", "")
            display = f"[{db}]::{tag}"
        else:
            display = str(main_val) if main_val is not None else ""
        for idx in data.get("indices", []):
            val = idx.get("value") if isinstance(idx, dict) else None
            if isinstance(val, dict):
                db = val.get("db_name", "")
                tag = val.get("tag_name", "")
                display += f"[{db}]::{tag}"
            else:
                display += f"[{val}]" if val is not None else "[]"
        return display

    def _edit_tag_property(self, item: QTreeWidgetItem, property_path: str, current_value: Any):
        """Show TagSelector editor for tag properties."""
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)

        selector = TagSelector(container)
        layout.addWidget(selector)

        if isinstance(current_value, dict):
            try:
                selector.set_data(current_value)
            except Exception:
                pass

        ok_button = QPushButton("OK", container)
        ok_button.setFixedWidth(40)
        layout.addWidget(ok_button)

        cancel_button = QPushButton("Cancel", container)
        cancel_button.setFixedWidth(60)
        layout.addWidget(cancel_button)

        self.tree_widget.setItemWidget(item, 1, container)

        def apply_value():
            data = selector.get_data()
            self.tree_widget.setItemWidget(item, 1, None)
            item.setText(1, self._format_tag_display(data))
            item.setData(1, Qt.ItemDataRole.UserRole, data)
            self.tree_widget.itemChanged.emit(item, 1)

        def cancel_edit():
            self.tree_widget.setItemWidget(item, 1, None)

        ok_button.clicked.connect(apply_value)
        cancel_button.clicked.connect(cancel_edit)
    
    def _edit_bool_property(self, item: QTreeWidgetItem, property_path: str, current_value: str):
        """Show checkbox editor for boolean properties."""
        # Create temp widget to hold the checkbox
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        checkbox = QCheckBox(container)
        if isinstance(current_value, str):
            checkbox.setChecked(current_value.lower() == "true")
        else:
            checkbox.setChecked(bool(current_value))
        layout.addWidget(checkbox)
        
        # Add buttons
        ok_button = QPushButton("OK", container)
        ok_button.setFixedWidth(40)
        layout.addWidget(ok_button)
        
        cancel_button = QPushButton("Cancel", container)
        cancel_button.setFixedWidth(60)
        layout.addWidget(cancel_button)
        
        # Set up container
        self.tree_widget.setItemWidget(item, 1, container)
        
        # Connect signals
        def apply_value():
            new_value = str(checkbox.isChecked()).lower()
            self.tree_widget.setItemWidget(item, 1, None)
            item.setText(1, new_value)
            self.tree_widget.itemChanged.emit(item, 1)
        
        def cancel_edit():
            self.tree_widget.setItemWidget(item, 1, None)
        
        ok_button.clicked.connect(apply_value)
        cancel_button.clicked.connect(cancel_edit)
        checkbox.stateChanged.connect(lambda: None)  # Prevent auto-closing
    
    def _edit_color_property(self, item: QTreeWidgetItem, property_path: str, current_value: str):
        """Show color editor for color properties."""
        # Create temp widget to hold the color editor
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        
        line_edit = QLineEdit(container)
        line_edit.setText(current_value)
        layout.addWidget(line_edit)
        
        # Add color button
        color_button = QPushButton("...", container)
        color_button.setFixedWidth(30)
        layout.addWidget(color_button)
        
        # Add buttons
        ok_button = QPushButton("OK", container)
        ok_button.setFixedWidth(40)
        layout.addWidget(ok_button)
        
        cancel_button = QPushButton("Cancel", container)
        cancel_button.setFixedWidth(60)
        layout.addWidget(cancel_button)
        
        # Set up container
        self.tree_widget.setItemWidget(item, 1, container)
        
        # Connect signals
        def show_color_dialog():
            try:
                current_color = QColor(line_edit.text()) if line_edit.text() else QColor("#000000")
                color = QColorDialog.getColor(current_color, self.tree_widget)
                if color.isValid():
                    line_edit.setText(color.name())
            except Exception as e:
                print(f"Error showing color dialog: {e}")
        
        def apply_value():
            new_value = line_edit.text()
            self.tree_widget.setItemWidget(item, 1, None)
            item.setText(1, new_value)
            self.tree_widget.itemChanged.emit(item, 1)
        
        def cancel_edit():
            self.tree_widget.setItemWidget(item, 1, None)
        
        color_button.clicked.connect(show_color_dialog)
        ok_button.clicked.connect(apply_value)
        cancel_button.clicked.connect(cancel_edit)
        line_edit.editingFinished.connect(apply_value)


class ButtonTreePropertyEditor(QWidget):
    """Enhanced tree-based property editor with inline editing."""
    
    property_changed = pyqtSignal(str, object)
    
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.current_object_id: str | None = None
        self.current_parent_id: str | None = None
        self.current_properties: dict = {}
        self.current_position = {"x": 0, "y": 0}
        self.current_size = {"width": 0, "height": 0}
        self._is_editing = False
        self._blocked = False
        self._setup_ui()
        
        data_context.screens_changed.connect(self._handle_screen_event)
    
    def _setup_ui(self) -> None:
        """Set up the UI components."""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Create unified property tree with inline editing
        self.property_tree = QTreeWidget()
        self.property_tree.setHeaderLabels(["Property", "Value"])
        self.property_tree.setColumnWidth(0, 180)
        # Remove alternating row colors to eliminate blue lines
        self.property_tree.setAlternatingRowColors(False)
        # Set stylesheet to ensure consistent appearance
        self.property_tree.setStyleSheet("""
            QTreeWidget {
                background-color: transparent;
                border: none;
            }
            QTreeWidget::item {
                border-bottom: 1px solid #2a2a2a;
                padding: 2px 0;
            }
        """)
        self.property_tree.itemChanged.connect(self._on_item_changed)
        
        # Set up inline property editor
        self.inline_editor = InlinePropertyEditor(self.property_tree)
        
        main_layout.addWidget(self.property_tree)
        
        # Initialize tree with property categories
        self._populate_property_tree()
    
    def _populate_property_tree(self) -> None:
        """Populate the property tree with categories and properties."""
        self.property_tree.clear()
        
        # Position category (with X, Y, W, H)
        position_category = self._add_category("Position")
        self._add_property(position_category, "X", "x")
        self._add_property(position_category, "Y", "y")
        self._add_property(position_category, "W", "width")
        self._add_property(position_category, "H", "height")
        
        # Action category with dynamically numbered items
        action_category = self._add_category("action")
        self._populate_actions(action_category)
        
        # Style category with dynamically numbered items
        style_category = self._add_category("style")
        self._populate_conditional_styles(style_category)
        
        # Add default style if no conditional styles exist
        if not self.current_properties.get("conditional_styles"):
            # Style 1
            style1 = self._add_expandable_property(style_category, "1", "style1")
            self._add_property(style1, "tooltip", "tooltip")
            
            # Component style & background
            comp_style = self._add_expandable_property(style1, "component style & background...", "component_style")
            self._add_property(comp_style, "component type", "component_type")
            self._add_property(comp_style, "shape type", "shape_style")
            self._add_property(comp_style, "background type", "background_type")
            self._add_property(comp_style, "etc...", "comp_style_etc")
            
            # Style option
            style_option = self._add_expandable_property(style1, "style option", "style_option")
        
        # Expand position by default
        position_category.setExpanded(True)
    
    def _populate_conditional_styles(self, parent: QTreeWidgetItem) -> None:
        """Populate the conditional styles section of the tree."""
        styles = self.current_properties.get("conditional_styles", [])
        
        # Add "Add Style" button item
        add_style_item = QTreeWidgetItem(parent, ["Add Conditional Style", ""])
        add_style_item.setData(0, Qt.ItemDataRole.UserRole, "add_conditional_style")
        
        # If there are no styles, just show the add button
        if not styles:
            return
            
        # Add each conditional style as an expandable item with simple numbered display
        for i, style in enumerate(styles):
            # Just use the index number as the display label
            style_item = self._add_expandable_property(parent, f"{i+1}", f"conditional_styles.{i}")
            
            # Add style properties
            tag_path = style.get("tag_path", "")
            condition = style.get("condition", "==")
            value = style.get("value", "")
            
            self._add_property(style_item, "Tag Path", f"conditional_styles.{i}.tag_path")
            self._add_property(style_item, "Condition", f"conditional_styles.{i}.condition")
            self._add_property(style_item, "Value", f"conditional_styles.{i}.value")
            
            # Component style & background
            comp_style = self._add_expandable_property(style_item, "component style & background...", f"conditional_styles.{i}.component_style")
            self._add_property(comp_style, "component type", f"conditional_styles.{i}.style.component_type")
            self._add_property(comp_style, "shape type", f"conditional_styles.{i}.style.shape_style")
            self._add_property(comp_style, "background type", f"conditional_styles.{i}.style.background_type")
            
            # Style option
            style_option = self._add_expandable_property(style_item, "style option", f"conditional_styles.{i}.style_option")
            
            # Add all style properties that are available
            style_data = style.get("style", {})
            for prop_name, prop_value in style_data.items():
                if prop_name not in ["component_type", "shape_style", "background_type"]:
                    display_name = prop_name.replace("_", " ").title()
                    self._add_property(style_option, display_name, f"conditional_styles.{i}.style.{prop_name}")
    
    def _populate_actions(self, parent: QTreeWidgetItem) -> None:
        """Populate the actions section of the tree."""
        actions = self.current_properties.get("actions", [])
        
        # Add "Add Action" items
        bit_action_item = QTreeWidgetItem(parent, ["Add Bit Action", ""])
        bit_action_item.setData(0, Qt.ItemDataRole.UserRole, "add_bit_action")
        
        word_action_item = QTreeWidgetItem(parent, ["Add Word Action", ""])
        word_action_item.setData(0, Qt.ItemDataRole.UserRole, "add_word_action")
        
        # If there are no actions, just show the add buttons
        if not actions:
            return
            
        # Add each action as an expandable item with simple numbered display
        for i, action in enumerate(actions):
            action_type = action.get("type", "bit")
            
            # Just use the index number as the display label
            action_item = self._add_expandable_property(
                parent,
                f"{i+1}",
                f"actions.{i}"
            )
            
            # Add action type as an expandable property
            action_type_item = self._add_expandable_property(
                action_item,
                f"{action_type.title()} main action",
                f"actions.{i}.main_action"
            )
            
            # Add common action properties
            self._add_property(action_item, "Type", f"actions.{i}.type")
            
            # Add type-specific properties
            if action_type == "bit":
                target_tag = self._add_expandable_property(action_type_item, "target tag", f"actions.{i}.target_tag")
                self._add_property(target_tag, "index 1", f"actions.{i}.tag_index1")
                self._add_property(target_tag, "index 2", f"actions.{i}.tag_index2")
                
                self._add_property(action_item, "0 momentary 0 Alternet 0...", f"actions.{i}.momentary_action")
                
                trigger = self._add_expandable_property(action_item, "Trigger", f"actions.{i}.trigger")
                self._add_property(trigger, "Ordinary", f"actions.{i}.trigger_type")
                
            elif action_type == "word":
                target_tag = self._add_expandable_property(action_type_item, "target tag", f"actions.{i}.target_tag")
                self._add_property(target_tag, "index 1", f"actions.{i}.tag_index1")
                self._add_property(target_tag, "index 2", f"actions.{i}.tag_index2")
                
                self._add_property(action_item, "Action Mode", f"actions.{i}.action_mode")
                self._add_property(action_item, "Value to add", f"actions.{i}.value_to_add")
                
                trigger = self._add_expandable_property(action_item, "Trigger", f"actions.{i}.trigger")
                self._add_property(trigger, "Ordinary", f"actions.{i}.trigger_type")
                self._add_property(trigger, "Conditional reset", f"actions.{i}.conditional_reset")
                self._add_property(trigger, "etc", f"actions.{i}.trigger_etc")
                
            elif action_type == "navigate":
                self._add_property(action_item, "Screen", f"actions.{i}.screen")
            
            # Add any other properties that might be in the action
            for prop_name, prop_value in action.items():
                if prop_name not in ["type", "tag", "when_pressed", "when_released", "operation", "value", "screen"]:
                    display_name = prop_name.replace("_", " ").title()
                    self._add_property(action_item, display_name, f"actions.{i}.{prop_name}")
    
    def _add_category(self, name: str) -> QTreeWidgetItem:
        """Add a category to the property tree."""
        category = QTreeWidgetItem(self.property_tree, [name, ""])
        font = category.font(0)
        font.setBold(True)
        category.setFont(0, font)
        category.setFlags(category.flags() & ~Qt.ItemFlag.ItemIsSelectable)
        category.setExpanded(False)  # Categories start collapsed
        return category
    
    def _add_property(self, parent: QTreeWidgetItem, display_name: str, property_name: str) -> QTreeWidgetItem:
        """Add a property to the property tree under the specified category."""
        item = QTreeWidgetItem(parent, [display_name, ""])
        item.setData(0, Qt.ItemDataRole.UserRole, property_name)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        return item
    
    def _add_expandable_property(self, parent: QTreeWidgetItem, display_name: str, property_name: str) -> QTreeWidgetItem:
        """Add an expandable property group to the tree."""
        item = QTreeWidgetItem(parent, [display_name, ""])
        item.setData(0, Qt.ItemDataRole.UserRole, property_name)
        
        # Make it look like a category but still selectable
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)
        
        # Make it expanded by default
        item.setExpanded(True)
        
        return item
    
    def _on_item_changed(self, item: QTreeWidgetItem, column: int) -> None:
        """Handle changes to property items in the tree."""
        if self._blocked or column != 1:
            return
            
        property_path = item.data(0, Qt.ItemDataRole.UserRole)
        if not property_path:
            return
            
        value = item.data(1, Qt.ItemDataRole.UserRole)
        if value is None:
            value = item.text(1)
        
        # Handle special property paths
        if property_path == "add_conditional_style":
            self._add_new_conditional_style()
            return
        elif property_path == "add_bit_action":
            self._add_new_action("bit")
            return
        elif property_path == "add_word_action":
            self._add_new_action("word")
            return
        
        # Handle property path to update the correct property
        parts = property_path.split('.')
        
        # Handle basic properties first
        if len(parts) == 1:
            property_name = parts[0]
            
            # Handle position properties (x, y)
            if property_name in ["x", "y"]:
                try:
                    value = int(value)
                    self._on_position_changed(property_name, value)
                except ValueError:
                    pass  # Ignore invalid values
                    
            # Handle size properties (width, height, w, h)
            elif property_name in ["width", "height", "w", "h"]:
                try:
                    # Map w to width and h to height
                    key = property_name
                    if property_name == "w":
                        key = "width"
                    elif property_name == "h":
                        key = "height"
                    
                    value = int(value)
                    self._on_size_changed(key, value)
                except ValueError:
                    pass  # Ignore invalid values
                    
            # Handle regular properties
            else:
                self._on_property_changed(property_name, value)
                
        # Handle nested properties for conditional styles and actions
        else:
            self._update_nested_property(parts, value)
    
    def _update_nested_property(self, path_parts: List[str], value: Any) -> None:
        """Update a nested property based on its path."""
        if not self.current_object_id or isinstance(self.current_object_id, list):
            return
            
        old_props = copy.deepcopy(self.current_properties)
        new_props = copy.deepcopy(self.current_properties)
        
        # Navigate to the correct nested property
        current = new_props
        for i, part in enumerate(path_parts[:-1]):
            if part.isdigit():
                # Handle array indices
                idx = int(part)
                if isinstance(current, list) and 0 <= idx < len(current):
                    current = current[idx]
                else:
                    # Invalid path
                    return
            else:
                # Handle object properties
                if part not in current:
                    if i < len(path_parts) - 2 and path_parts[i+1].isdigit():
                        # Initialize as list if next part is an index
                        current[part] = []
                    else:
                        # Initialize as dict otherwise
                        current[part] = {}
                current = current[part]
        
        # Set the final property value
        last_part = path_parts[-1]
        
        # Convert value based on property type (hardcoding some known types)
        if last_part in ["font_bold", "font_italic", "font_underline"]:
            value = value.lower() == "true"
        elif last_part in ["border_width", "font_size", "icon_size"]:
            try:
                value = int(value)
            except ValueError:
                pass
        
        # Set the property
        if last_part.isdigit():
            idx = int(last_part)
            if isinstance(current, list) and 0 <= idx < len(current):
                current[idx] = value
        else:
            current[last_part] = value
        
        # Update the properties
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
            self._update_property_values()
        finally:
            guard.end()
    
    def _add_new_conditional_style(self) -> None:
        """Add a new conditional style to the button."""
        if not self.current_object_id or isinstance(self.current_object_id, list):
            return
            
        old_props = copy.deepcopy(self.current_properties)
        new_props = copy.deepcopy(self.current_properties)
        
        # Initialize conditional_styles if it doesn't exist
        if "conditional_styles" not in new_props:
            new_props["conditional_styles"] = []
            
        # Add new empty style
        new_style = {
            "tag_path": "",
            "condition": "==",
            "value": "",
            "style": {
                "background_color": "#cccccc",
                "text_color": "#000000"
            }
        }
        
        new_props["conditional_styles"].append(new_style)
        
        # Update the properties
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
            self._repopulate_property_tree()
        finally:
            guard.end()
    
    def _add_new_action(self, action_type: str) -> None:
        """Add a new action to the button."""
        if not self.current_object_id or isinstance(self.current_object_id, list):
            return
            
        old_props = copy.deepcopy(self.current_properties)
        new_props = copy.deepcopy(self.current_properties)
        
        # Initialize actions if it doesn't exist
        if "actions" not in new_props:
            new_props["actions"] = []
            
        # Add new action based on type
        if action_type == "bit":
            new_action = {
                "type": "bit",
                "tag": "",
                "when_pressed": "toggle",
                "when_released": "none"
            }
        elif action_type == "word":
            new_action = {
                "type": "word",
                "tag": "",
                "operation": "set",
                "value": "0"
            }
        else:
            return
            
        new_props["actions"].append(new_action)
        
        # Update the properties
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
            self._repopulate_property_tree()
        finally:
            guard.end()
    
    def _repopulate_property_tree(self) -> None:
        """Repopulate the entire property tree while preserving expansion state."""
        # Remember which categories were expanded
        expanded_items = []
        root = self.property_tree.invisibleRootItem()
        
        if root:
            child_count = root.childCount()
            for i in range(child_count):
                category = root.child(i)
                if category and category.isExpanded():
                    expanded_items.append(category.text(0))
                    
                    # Also check for expanded children
                    category_child_count = category.childCount()
                    for j in range(category_child_count):
                        child = category.child(j)
                        if child and child.isExpanded():
                            expanded_items.append(f"{category.text(0)}.{child.text(0)}")
        
        # Repopulate the tree
        self._populate_property_tree()
        
        # Restore expansion state
        root = self.property_tree.invisibleRootItem()
        
        if root:
            child_count = root.childCount()
            for i in range(child_count):
                category = root.child(i)
                if category and category.text(0) in expanded_items:
                    category.setExpanded(True)
                    
                    # Also check for expanded children
                    category_child_count = category.childCount()
                    for j in range(category_child_count):
                        child = category.child(j)
                        if child and f"{category.text(0)}.{child.text(0)}" in expanded_items:
                            child.setExpanded(True)
    
    def _update_property_values(self) -> None:
        """Update all property values in the tree."""
        if self._blocked:
            return
            
        self._blocked = True
        try:
            root = self.property_tree.invisibleRootItem()
            if root:
                self._update_tree_values(root)
        finally:
            self._blocked = False
    
    def _update_tree_values(self, parent_item: Optional[QTreeWidgetItem]) -> None:
        """Recursively update values for all tree items."""
        if not parent_item:
            return
            
        try:
            child_count = parent_item.childCount()
            for i in range(child_count):
                item = parent_item.child(i)
                if not item:
                    continue
                    
                property_path = item.data(0, Qt.ItemDataRole.UserRole)
                if not property_path:
                    continue
                    
                # Skip special items
                if property_path in ["add_conditional_style", "add_bit_action", "add_word_action"]:
                    continue
                
                # Add visual styling for all group headers
                if item.childCount() > 0:
                    # This is a group header
                    font = item.font(0)
                    font.setBold(True)
                    item.setFont(0, font)
                    
                # Handle regular properties
                if "." not in property_path:
                    if property_path in ["x", "y"]:
                        value = str(self.current_position.get(property_path, 0))
                    elif property_path in ["width", "height", "w", "h"]:
                        # Map w to width and h to height
                        prop = property_path
                        if property_path == "w":
                            prop = "width"
                        elif property_path == "h":
                            prop = "height"
                        value = str(self.current_size.get(prop, 0))
                    else:
                        value = self.current_properties.get(property_path, "")
                    if isinstance(value, dict) and "main_tag" in value:
                        display = self.inline_editor._format_tag_display(value) if hasattr(self, 'inline_editor') else str(value)
                        item.setText(1, display)
                        item.setData(1, Qt.ItemDataRole.UserRole, value)
                    else:
                        item.setText(1, str(value))
                        item.setData(1, Qt.ItemDataRole.UserRole, None)
                    
                    # Apply color handling for all color properties
                    self._apply_color_styling(item, property_path, value)
                    
                    # Boolean property special handling for display
                    if property_path in ["font_bold", "font_italic", "font_underline"]:
                        if value.lower() == "true":
                            item.setText(1, "True")
                            font = item.font(1)
                            if property_path == "font_bold":
                                font.setBold(True)
                            elif property_path == "font_italic":
                                font.setItalic(True)
                            elif property_path == "font_underline":
                                font.setUnderline(True)
                            item.setFont(1, font)
                        else:
                            item.setText(1, "False")
                else:
                    # Handle nested properties
                    self._update_nested_value(item, property_path)
                
                # Recursively update child items
                self._update_tree_values(item)
        except Exception as e:
            print(f"Error updating tree values: {e}")
    
    def _apply_color_styling(self, item: QTreeWidgetItem, property_path: str, value: str) -> None:
        """Apply color styling to properties that represent colors."""
        # Handle all color properties with consistent styling
        if "_color" in property_path:
            try:
                color = QColor(value)
                if color.isValid():
                    item.setBackground(1, QBrush(color))
                    # Use contrasting text color
                    brightness = (0.299 * color.red() + 0.587 * color.green() + 0.114 * color.blue()) / 255
                    if brightness > 0.5:
                        item.setForeground(1, QBrush(Qt.GlobalColor.black))
                    else:
                        item.setForeground(1, QBrush(Qt.GlobalColor.white))
            except Exception:
                # Reset background if not a valid color
                item.setBackground(1, QBrush())
                item.setForeground(1, QBrush())

    def _update_nested_value(self, item: QTreeWidgetItem, property_path: str) -> None:
        """Update value for a nested property based on its path."""
        parts = property_path.split('.')
        
        # Special handling for style number and graphics
        if property_path == "style_number":
            # Display style number (this could be retrieved from current properties)
            item.setText(1, str(self.current_properties.get("style_number", "1")))
            return
            
        # Navigate to the correct nested property
        current = self.current_properties
        for i, part in enumerate(parts):
            if part.isdigit():
                # Handle array indices
                idx = int(part)
                if isinstance(current, list) and 0 <= idx < len(current):
                    current = current[idx]
                else:
                    # Invalid path
                    item.setText(1, "")
                    return
            else:
                # Handle object properties
                if part not in current:
                    item.setText(1, "")
                    return
                current = current[part]
        
        # Set the item text
        value = current
        if isinstance(value, dict) and "main_tag" in value:
            display = self.inline_editor._format_tag_display(value) if hasattr(self, 'inline_editor') else str(value)
            item.setText(1, display)
            item.setData(1, Qt.ItemDataRole.UserRole, value)
        else:
            item.setText(1, str(value) if value is not None else "")
            item.setData(1, Qt.ItemDataRole.UserRole, None)
        
        # Apply color styling to all nested color properties too
        self._apply_color_styling(item, property_path, value)
    
    def _on_position_changed(self, key: str, value: int) -> None:
        """Handle position property changes."""
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
            self._update_property_values()
        finally:
            guard.end()
    
    def _on_size_changed(self, key: str, value: int) -> None:
        """Handle size property changes."""
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
            self._update_property_values()
        finally:
            guard.end()
    
    def _on_property_changed(self, key: str, value: Any) -> None:
        """Handle property changes."""
        if not self.current_object_id or isinstance(self.current_object_id, list):
            return
        old_props = copy.deepcopy(self.current_properties)
        new_props = copy.deepcopy(self.current_properties)
        
        # Check if value is the same
        if new_props.get(key) == value:
            return
            
        new_props[key] = value
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
            self._update_property_values()
            self.property_changed.emit(key, value)
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
        # Clear selection if editing is happening or screen ID doesn't match
        if self._is_editing or screen_id != self.current_parent_id:
            return
            
        # Check if we have a current object ID
        if not self.current_object_id:
            self._clear_selection()
            return
            
        # Try to get the instance from the screen service
        instance = screen_service.get_child_instance(
            self.current_parent_id, self.current_object_id
        )
        
        # If instance exists, update properties
        if instance is not None:
            selection = {
                "instance_id": instance.get("instance_id"),
                "properties": copy.deepcopy(instance.get("properties") or {}),
                # Store a top-level position for convenience, regardless of schema
                "position": (instance.get("position")
                               or instance.get("properties", {}).get("position", {})
                               or {}),
            }
            self.current_properties = selection.get("properties", {})
            # Read position from either top-level or nested under properties
            pos = (instance.get("position")
                   or instance.get("properties", {}).get("position", {})
                   or {})
            size = self.current_properties.get("size", {})
            self.current_position = {"x": int(pos.get("x", 0) or 0), "y": int(pos.get("y", 0) or 0)}
            self.current_size = {"width": int(size.get("width", 0) or 0), "height": int(size.get("height", 0) or 0)}
            self._update_property_values()
        else:
            # Clear selection if instance doesn't exist anymore
            self._clear_selection()
    
    def _clear_selection(self) -> None:
        """Completely clear the selection and reset the property editor."""
        self.current_object_id = None
        self.current_parent_id = None
        self.current_properties = {}
        self.current_position = {"x": 0, "y": 0}
        self.current_size = {"width": 0, "height": 0}
        
        # Completely clear the tree widget
        self.property_tree.clear()
        
        # Force immediate visual update
        self.property_tree.update()
        
        # Important: Do not repopulate property tree categories
        # This ensures properties will be completely gone when nothing is selected
    
    @pyqtSlot(str, object)
    def set_current_object(self, parent_id: str, selection_data: object) -> None:
        """Set the current object being edited."""
        if self._is_editing:
            return
        
        # First, ensure we clear any existing selection to prevent properties from persisting
        self._clear_selection()
        
        # If no selection data, we're already cleared
        if not selection_data:
            return
        
        self._blocked = True
        try:
            # Convert selection_data to dict if it's a list with a single item
            if isinstance(selection_data, list):
                if len(selection_data) == 1:
                    selection_data = selection_data[0]
                else:
                    return  # Multiple selections not supported
            
            # Handle selection_data safely
            if isinstance(selection_data, dict):
                selection_dict = selection_data
            else:
                # If it's not a dict, try to access attributes directly
                selection_dict = {}
                try:
                    if hasattr(selection_data, "tool_id"):
                        selection_dict["tool_id"] = getattr(selection_data, "tool_id")
                    if hasattr(selection_data, "tool_type"):
                        selection_dict["tool_type"] = getattr(selection_data, "tool_type")
                    if hasattr(selection_data, "instance_id"):
                        selection_dict["instance_id"] = getattr(selection_data, "instance_id")
                    if hasattr(selection_data, "properties"):
                        selection_dict["properties"] = getattr(selection_data, "properties")
                    if hasattr(selection_data, "position"):
                        selection_dict["position"] = getattr(selection_data, "position")
                except Exception:
                    return
                    
            # Check if selection is a button (support both legacy 'tool_id' and enum 'tool_type')
            tool_id = selection_dict.get("tool_id", "")
            tool_type_val = selection_dict.get("tool_type")
            tool_type = constants.tool_type_from_str(tool_type_val) if tool_type_val is not None else None
            is_button = (
                (isinstance(tool_id, str) and tool_id.startswith("button"))
                or (tool_type == constants.ToolType.BUTTON)
            )
            if not is_button:
                return  # Not a button, we should remain cleared
                
            self.current_object_id = selection_dict.get("instance_id")
            self.current_parent_id = parent_id
            
            # Handle properties
            properties_data = selection_dict.get("properties", {})
            if properties_data and isinstance(properties_data, dict):
                self.current_properties = copy.deepcopy(properties_data)
            else:
                self.current_properties = {}
                
            # Handle position (top-level or nested)
            position_data = selection_dict.get("position") or selection_dict.get("properties", {}).get("position", {})
            if position_data and isinstance(position_data, dict):
                pos = position_data
            else:
                pos = {}
                
            # Handle size
            size_data = self.current_properties.get("size", {})
            if size_data and isinstance(size_data, dict):
                size = size_data
            else:
                size = {}
            
            # Convert position values to integers, handling None values
            x = pos.get("x", 0)
            y = pos.get("y", 0)
            width = size.get("width", 0)
            height = size.get("height", 0)
            
            self.current_position = {
                "x": int(x) if x is not None else 0,
                "y": int(y) if y is not None else 0
            }
            self.current_size = {
                "width": int(width) if width is not None else 0,
                "height": int(height) if height is not None else 0
            }
            
            # Repopulate the tree with the current properties
            self._populate_property_tree()
        finally:
            self._blocked = False
            self._update_property_values()
    
    def set_active_tool(self, tool_id) -> None:  # compatibility stub
        """Compatibility stub to match the PropertyEditor interface."""
        pass