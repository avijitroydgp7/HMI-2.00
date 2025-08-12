# components/button/button_properties_dialog.py
from PyQt6.QtWidgets import (
    QTabWidget, QWidget, QDialogButtonBox, QLabel, QFormLayout, 
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView, 
    QPushButton, QHBoxLayout, QAbstractItemView, QVBoxLayout,
    QScrollArea, QSplitter, QGroupBox, QStackedWidget
)
from PyQt6.QtCore import Qt
from typing import Dict, Any, Optional
import copy

from tools import button_styles
from dialogs.actions.select_action_type_dialog import SelectActionTypeDialog
from dialogs.actions.bit_action_dialog import BitActionDialog
from dialogs.actions.word_action_dialog import WordActionDialog
from services.tag_data_service import tag_data_service
from dialogs.base_dialog import CustomDialog

class ButtonPropertiesDialog(CustomDialog):
    def __init__(self, properties: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.properties = copy.deepcopy(properties)
        if 'actions' not in self.properties:
            self.properties['actions'] = []
        
        # Store reference to button item and canvas
        self.button_item = None
        self.canvas = None
        
        # Try to get button item and canvas from parent
        if parent:
            if hasattr(parent, 'button_item'):
                self.button_item = parent.button_item
            if hasattr(parent, 'canvas'):
                self.canvas = parent.canvas
        
        self.setWindowTitle("Button Properties")
        self.setMinimumWidth(1000)  # Increased width for better layout
        self.setMaximumHeight(700)  # Increased height
        self.resize(1000, 700)  # Set initial size

        content_layout = self.get_content_layout()
        
        self.tab_widget = QTabWidget()
        content_layout.addWidget(self.tab_widget)

        self.action_tab = QWidget()
        self.style_tab = QWidget()

        self.tab_widget.addTab(self.action_tab, "Action")
        self.tab_widget.addTab(self.style_tab, "Style")
        
        self._populate_action_tab()
        self._populate_style_tab()
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        content_layout.addWidget(self.button_box)

    def _populate_action_tab(self):
        # Overall layout for the tab
        layout = QVBoxLayout(self.action_tab)
        
        # Splitter for top area
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Action table
        self.action_table = QTableWidget()
        self.action_table.setColumnCount(6)
        self.action_table.setHorizontalHeaderLabels([
            "#", "Action Type", "Target Tag", "Trigger", "Conditional Reset", "Details"
        ])
        self.action_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.action_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.action_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.action_table.verticalHeader().setVisible(False)
        header = self.action_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        splitter.addWidget(self.action_table)

        # Right panel: Action properties
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        self.action_properties_group = QGroupBox("Action Properties")
        properties_layout = QVBoxLayout(self.action_properties_group)
        
        self.action_properties_stack = QStackedWidget()
        properties_layout.addWidget(self.action_properties_stack)
        
        # Create different property widgets
        self._create_action_property_widgets()

        right_layout.addWidget(self.action_properties_group)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        # Add splitter to the main layout
        layout.addWidget(splitter)
        
        # Buttons at the bottom, outside the splitter
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add"); add_btn.clicked.connect(self._add_action)
        edit_btn = QPushButton("Edit"); edit_btn.clicked.connect(self._edit_action)
        remove_btn = QPushButton("Remove"); remove_btn.clicked.connect(self._remove_action)
        duplicate_btn = QPushButton("Duplicate"); duplicate_btn.clicked.connect(self._duplicate_action)
        move_up_btn = QPushButton("Move Up"); move_up_btn.clicked.connect(self._move_action_up)
        move_down_btn = QPushButton("Move Down"); move_down_btn.clicked.connect(self._move_action_down)
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(remove_btn)
        button_layout.addWidget(duplicate_btn)
        button_layout.addStretch()
        button_layout.addWidget(move_up_btn)
        button_layout.addWidget(move_down_btn)
        layout.addLayout(button_layout)
        
        self.action_table.cellDoubleClicked.connect(self._on_action_double_click)
        self.action_table.itemSelectionChanged.connect(self._on_action_selection_changed)
        
        self._refresh_action_table()
        self._on_action_selection_changed() # Set initial state

    def _create_action_property_widgets(self):
        # 0: Default widget
        default_widget = QWidget()
        default_layout = QVBoxLayout(default_widget)
        default_layout.addWidget(QLabel("Select an action to view its properties."))
        default_layout.addStretch()
        self.action_properties_stack.addWidget(default_widget)

        # 1: Bit action widget
        bit_widget = QWidget()
        bit_layout = QFormLayout(bit_widget)
        bit_layout.setContentsMargins(5, 5, 5, 5)
        self.bit_target_tag_edit = QLineEdit()
        self.bit_target_tag_edit.setReadOnly(True)
        self.bit_mode_edit = QLineEdit()
        self.bit_mode_edit.setReadOnly(True)
        bit_layout.addRow("Target Tag:", self.bit_target_tag_edit)
        bit_layout.addRow("Mode:", self.bit_mode_edit)
        self.action_properties_stack.addWidget(bit_widget)

        # 2: Word action widget
        word_widget = QWidget()
        word_layout = QFormLayout(word_widget)
        word_layout.setContentsMargins(5, 5, 5, 5)
        self.word_target_tag_edit = QLineEdit()
        self.word_target_tag_edit.setReadOnly(True)
        self.word_action_mode_edit = QLineEdit()
        self.word_action_mode_edit.setReadOnly(True)
        self.word_value_edit = QLineEdit()
        self.word_value_edit.setReadOnly(True)
        word_layout.addRow("Target Tag:", self.word_target_tag_edit)
        word_layout.addRow("Action Mode:", self.word_action_mode_edit)
        word_layout.addRow("Value:", self.word_value_edit)
        self.action_properties_stack.addWidget(word_widget)

    def _on_action_selection_changed(self):
        selected_rows = self.action_table.selectionModel().selectedRows()
        if not selected_rows:
            self.action_properties_stack.setCurrentIndex(0)
            self.action_properties_group.setTitle("Action Properties")
            return

        row = selected_rows[0].row()
        if row >= len(self.properties['actions']):
            self.action_properties_stack.setCurrentIndex(0)
            self.action_properties_group.setTitle("Action Properties")
            return
            
        action_data = self.properties['actions'][row]
        action_type = action_data.get('action_type')

        if action_type == "bit":
            self.action_properties_stack.setCurrentIndex(1)
            self.action_properties_group.setTitle("Bit Action Properties")
            self._populate_bit_action_properties(action_data)
        elif action_type == "word":
            self.action_properties_stack.setCurrentIndex(2)
            self.action_properties_group.setTitle("Word Action Properties")
            self._populate_word_action_properties(action_data)
        else:
            self.action_properties_stack.setCurrentIndex(0)
            self.action_properties_group.setTitle("Action Properties")

    def _populate_bit_action_properties(self, action_data):
        target_tag_str = self._format_operand_for_display(action_data.get("target_tag"))
        self.bit_target_tag_edit.setText(target_tag_str)
        self.bit_mode_edit.setText(action_data.get("mode", "N/A"))

    def _populate_word_action_properties(self, action_data):
        target_tag_str = self._format_operand_for_display(action_data.get("target_tag"))
        value_str = self._format_operand_for_display(action_data.get("value"))
        self.word_target_tag_edit.setText(target_tag_str)
        self.word_action_mode_edit.setText(action_data.get("action_mode", "N/A"))
        self.word_value_edit.setText(value_str)

    def _on_action_double_click(self, row, column):
        # Open edit dialog for the selected action
        if row < 0 or row >= len(self.properties.get('actions', [])):
            return
        action_data = self.properties['actions'][row]
        action_type = action_data.get('action_type')
        action_dialog = None
        if action_type == "bit":
            action_dialog = BitActionDialog(self, action_data=action_data)
        elif action_type == "word":
            action_dialog = WordActionDialog(self, action_data=action_data)
        if action_dialog and action_dialog.exec():
            new_action_data = action_dialog.get_data()
            if new_action_data:
                self.properties['actions'][row] = new_action_data
                self._refresh_action_table()

    def _format_operand_for_display(self, data: Optional[Dict]) -> str:
        if not data: return "N/A"
        
        # Handle direct tag structure (as used in action dialogs)
        if isinstance(data, dict) and 'db_name' in data and 'tag_name' in data:
            db_name = data.get('db_name', '??')
            tag_name = data.get('tag_name', '??')
            indices = data.get("indices", [])
            index_str = "".join(f"[{self._format_operand_for_display({'main_tag': idx})}]" for idx in indices)
            return f"[{db_name}]::{tag_name}{index_str}"
        
        # Handle nested structure
        main_tag = data.get("main_tag")
        if not main_tag: return "N/A"
        
        source = main_tag.get("source")
        value = main_tag.get("value")

        if source == "constant":
            return str(value)
        elif source == "tag" and isinstance(value, dict):
            db_name = value.get('db_name', '??')
            tag_name = value.get('tag_name', '??')
            indices = data.get("indices", [])
            index_str = "".join(f"[{self._format_operand_for_display({'main_tag': idx})}]" for idx in indices)
            return f"[{db_name}]::{tag_name}{index_str}"
        return "N/A"

    def _format_trigger_for_display(self, trigger_data: Optional[Dict]) -> str:
        """Format trigger information for display."""
        if not trigger_data:
            return "Click"
        
        mode = trigger_data.get('mode', 'Ordinary')
        if mode == "Ordinary":
            return "Click"
        elif mode == "On":
            tag_data = trigger_data.get('tag')
            if tag_data:
                tag_display = self._format_operand_for_display(tag_data)
                return f"ON = {tag_display}"
            return "ON"
        elif mode == "Off":
            tag_data = trigger_data.get('tag')
            if tag_data:
                tag_display = self._format_operand_for_display(tag_data)
                return f"OFF = {tag_display}"
            return "OFF"
        elif mode == "Range":
            operator = trigger_data.get('operator', '==')
            operand1 = trigger_data.get('operand1')
            if operand1:
                operand1_display = self._format_operand_for_display(operand1)
                
                if operator in ["between", "outside"]:
                    lower = trigger_data.get('lower_bound')
                    upper = trigger_data.get('upper_bound')
                    if lower and upper:
                        lower_display = self._format_operand_for_display(lower)
                        upper_display = self._format_operand_for_display(upper)
                        return f"RANGE {operand1_display} {operator} [{lower_display}, {upper_display}]"
                else:
                    operand2 = trigger_data.get('operand2')
                    if operand2:
                        operand2_display = self._format_operand_for_display(operand2)
                        return f"RANGE {operand1_display} {operator} {operand2_display}"
            return f"RANGE {operator}"
        
        return mode

    def _format_conditional_reset_for_display(self, conditional_data: Optional[Dict]) -> str:
        """Format conditional reset information for display."""
        if not conditional_data:
            return "None"
        
        operator = conditional_data.get('operator', '==')
        operand1 = conditional_data.get('operand1')
        
        if operand1:
            operand1_display = self._format_operand_for_display(operand1)
            
            if operator in ["between", "outside"]:
                lower = conditional_data.get('lower_bound')
                upper = conditional_data.get('upper_bound')
                if lower and upper:
                    lower_display = self._format_operand_for_display(lower)
                    upper_display = self._format_operand_for_display(upper)
                    return f"COND {operand1_display} {operator} [{lower_display}, {upper_display}]"
            else:
                operand2 = conditional_data.get('operand2')
                if operand2:
                    operand2_display = self._format_operand_for_display(operand2)
                    return f"COND {operand1_display} {operator} {operand2_display}"
                else:
                    return f"COND {operand1_display} {operator}"
        
        return "COND"

    def _refresh_action_table(self):
        self.action_table.setRowCount(0)
        actions = self.properties.get('actions', [])
        for i, action in enumerate(actions):
            self.action_table.insertRow(i)
            
            action_type = action.get('action_type', '')
            target_data = action.get('target_tag')
            display_tag = self._format_operand_for_display(target_data)
            
            # Get trigger and conditional reset data
            trigger_data = action.get('trigger')
            conditional_reset_data = action.get('conditional_reset')
            
            trigger_display = self._format_trigger_for_display(trigger_data)
            conditional_reset_display = self._format_conditional_reset_for_display(conditional_reset_data)

            self.action_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.action_table.setItem(i, 1, QTableWidgetItem(action_type.capitalize()))
            self.action_table.setItem(i, 2, QTableWidgetItem(display_tag))
            self.action_table.setItem(i, 3, QTableWidgetItem(trigger_display))
            self.action_table.setItem(i, 4, QTableWidgetItem(conditional_reset_display))
            self.action_table.setItem(i, 5, QTableWidgetItem(action.get('details', '')))

    def _add_action(self):
        type_dialog = SelectActionTypeDialog(self)
        if not type_dialog.exec(): return

        action_type = type_dialog.selected_action_type
        action_dialog = None
        if action_type == "bit":
            action_dialog = BitActionDialog(self)
        elif action_type == "word":
            action_dialog = WordActionDialog(self)
        
        if action_dialog and action_dialog.exec():
            action_data = action_dialog.get_data()
            if action_data:
                # Ensure new actions have trigger and conditional reset fields
                if 'trigger' not in action_data:
                    action_data['trigger'] = {'type': 'click'}
                if 'conditional_reset' not in action_data:
                    action_data['conditional_reset'] = {'type': 'none'}
                
                self.properties['actions'].append(action_data)
                self._refresh_action_table()

    def _edit_action(self):
        selected_rows = self.action_table.selectionModel().selectedRows()
        if not selected_rows: return
        row = selected_rows[0].row()
        
        action_data = self.properties['actions'][row]
        action_type = action_data.get('action_type')

        action_dialog = None
        if action_type == "bit":
            action_dialog = BitActionDialog(self, action_data=action_data)
        elif action_type == "word":
            action_dialog = WordActionDialog(self, action_data=action_data)

        if action_dialog and action_dialog.exec():
            new_action_data = action_dialog.get_data()
            if new_action_data:
                # Ensure trigger and conditional reset fields exist
                if 'trigger' not in new_action_data:
                    new_action_data['trigger'] = {'type': 'click'}
                if 'conditional_reset' not in new_action_data:
                    new_action_data['conditional_reset'] = {'type': 'none'}
                
                self.properties['actions'][row] = new_action_data
                self._refresh_action_table()

    def _remove_action(self):
        selected_rows = self.action_table.selectionModel().selectedRows()
        if not selected_rows: return
        row = selected_rows[0].row()
        del self.properties['actions'][row]
        self._refresh_action_table()

    def _move_action_up(self):
        selected_rows = self.action_table.selectionModel().selectedRows()
        if not selected_rows: return
        row = selected_rows[0].row()
        if row > 0:
            self.properties['actions'].insert(row - 1, self.properties['actions'].pop(row))
            self._refresh_action_table()
            self.action_table.selectRow(row - 1)

    def _move_action_down(self):
        selected_rows = self.action_table.selectionModel().selectedRows()
        if not selected_rows: return
        row = selected_rows[0].row()
        if row < len(self.properties['actions']) - 1:
            self.properties['actions'].insert(row + 1, self.properties['actions'].pop(row))
            self._refresh_action_table()
            self.action_table.selectRow(row + 1)

    def _duplicate_action(self):
        """Duplicate the selected action"""
        selected_rows = self.action_table.selectionModel().selectedRows()
        if not selected_rows: return
        row = selected_rows[0].row()
        
        if row < len(self.properties['actions']):
            # Create a deep copy of the action
            original_action = self.properties['actions'][row]
            duplicated_action = copy.deepcopy(original_action)
            
            # Insert the duplicated action after the original
            self.properties['actions'].insert(row + 1, duplicated_action)
            self._refresh_action_table()
            
            # Select the newly duplicated action
            self.action_table.selectRow(row + 1)

    def _populate_style_tab(self):
        # Overall layout for the tab
        layout = QVBoxLayout(self.style_tab)
        
        # Splitter for top area
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Style table
        self.style_table = QTableWidget()
        self.style_table.setColumnCount(5)
        self.style_table.setHorizontalHeaderLabels(["#", "Name", "Style ID", "Priority", "Conditions"])
        self.style_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.style_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.style_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.style_table.verticalHeader().setVisible(False)
        header = self.style_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Stretch)
        splitter.addWidget(self.style_table)

        # Right panel: Style properties (placeholder)
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        properties_group = QGroupBox("Style Properties")
        properties_layout = QVBoxLayout(properties_group)
        properties_layout.addWidget(QLabel("Select a style to see its properties."))
        properties_layout.addStretch()
        right_layout.addWidget(properties_group)
        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        # Add splitter to the main layout
        layout.addWidget(splitter)
        
        # Buttons at the bottom, outside the splitter
        button_layout = QHBoxLayout()
        add_btn = QPushButton("Add")
        edit_btn = QPushButton("Edit")
        remove_btn = QPushButton("Remove")
        duplicate_btn = QPushButton("Duplicate")
        move_up_btn = QPushButton("Move Up")
        move_down_btn = QPushButton("Move Down")
        
        button_layout.addWidget(add_btn)
        button_layout.addWidget(edit_btn)
        button_layout.addWidget(remove_btn)
        button_layout.addWidget(duplicate_btn)
        button_layout.addStretch()
        button_layout.addWidget(move_up_btn)
        button_layout.addWidget(move_down_btn)
        layout.addLayout(button_layout)
        
    def _populate_extended_style_tab(self):
        pass

    def _on_extended_style_selected(self, style):
        pass

    def _populate_svg_style_tab(self):
        pass

    def _on_svg_style_selected(self, style: dict):
        pass

    def _populate_text_tab(self):
        pass


    def _on_style_selected(self, style_id):
        pass

    def get_data(self) -> Dict[str, Any]:
        updated_props = self.properties.copy()
        updated_props["actions"] = self.properties.get('actions', [])
        # Save label and text color fallback
        updated_props["label"] = self.properties.get("label", "Button")
        updated_props["text_color"] = self.properties.get("text_color", "#ffffff")
        return updated_props
