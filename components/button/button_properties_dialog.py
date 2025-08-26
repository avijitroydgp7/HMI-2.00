# components/button/button_properties_dialog.py
from PyQt6.QtWidgets import (
    QTabWidget, QWidget, QDialogButtonBox, QLabel, QFormLayout,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QPushButton, QHBoxLayout, QAbstractItemView, QVBoxLayout,
    QSplitter, QGroupBox, QStackedWidget, QDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIcon, QColor
from typing import Dict, Any, Optional
import copy

from dialogs.actions.select_action_type_dialog import SelectActionTypeDialog
from dialogs.actions.bit_action_dialog import BitActionDialog
from dialogs.actions.word_action_dialog import WordActionDialog

from .conditional_style import (
    ConditionalStyleManager,
    ConditionalStyle,
    ConditionalStyleEditorDialog,
    PreviewButton,
)


class ButtonPropertiesDialog(QDialog):
    def __init__(self, properties: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.properties = copy.deepcopy(properties)
        if 'actions' not in self.properties:
            self.properties['actions'] = []

        # Initialize conditional style manager
        self.style_manager = ConditionalStyleManager()
        for style_data in self.properties.get('conditional_styles', []):
            try:
                # ConditionalStyle.from_dict already understands the separated
                # base/hover/click property dictionaries and tooltip field.
                self.style_manager.add_style(ConditionalStyle.from_dict(style_data))
            except Exception:
                pass
        
        self.setWindowTitle("Button Properties")
        self.setMinimumWidth(1000)  # Increased width for better layout
        self.setMaximumHeight(700)  # Increased height
        self.resize(1000, 700)  # Set initial size

        content_layout = QVBoxLayout(self)
        
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
        """Format trigger information for display.

        Returns an empty string when no trigger is defined or when the
        trigger is an ordinary click.
        """
        if not trigger_data:
            return ""
        
        mode = trigger_data.get('mode', 'Ordinary')
        if mode == "Ordinary":
            return ""
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
        """Format conditional reset information for display.

        Returns an empty string when no conditional reset is defined.
        """
        if not conditional_data:
            return ""
        
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
        self.style_table.setColumnCount(4)
        self.style_table.setHorizontalHeaderLabels(["#", "Condition", "Preview", "Style ID"])
        self.style_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.style_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.style_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.style_table.verticalHeader().setVisible(False)
        header = self.style_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.style_table.setColumnWidth(2, 120)
        splitter.addWidget(self.style_table)

        # Right panel: Style properties and preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        # Group box with stacked widget for property display
        self.style_properties_group = QGroupBox("Style Properties")
        properties_layout = QVBoxLayout(self.style_properties_group)
        self.style_properties_stack = QStackedWidget()
        properties_layout.addWidget(self.style_properties_stack)

        # 0: Default widget when no style selected
        default_widget = QWidget()
        default_layout = QVBoxLayout(default_widget)
        default_layout.addWidget(QLabel("Select a style to see its properties."))
        default_layout.addStretch()
        self.style_properties_stack.addWidget(default_widget)

        # 1: Style info widget
        info_widget = QWidget()
        info_layout = QFormLayout(info_widget)
        self.style_id_label = QLabel()
        self.tooltip_label = QLabel()
        self.bg_color_label = QLabel()
        self.text_color_label = QLabel()
        self.hover_bg_color_label = QLabel()
        self.hover_text_color_label = QLabel()
        self.click_bg_color_label = QLabel()
        self.click_text_color_label = QLabel()
        info_layout.addRow("Style ID:", self.style_id_label)
        info_layout.addRow("Tooltip:", self.tooltip_label)
        info_layout.addRow("Base BG:", self.bg_color_label)
        info_layout.addRow("Base Text:", self.text_color_label)
        info_layout.addRow("Hover BG:", self.hover_bg_color_label)
        info_layout.addRow("Hover Text:", self.hover_text_color_label)
        info_layout.addRow("Click BG:", self.click_bg_color_label)
        info_layout.addRow("Click Text:", self.click_text_color_label)
        self.style_properties_stack.addWidget(info_widget)

        right_layout.addWidget(self.style_properties_group)

        # Preview widget
        self.preview_button = PreviewButton("Preview")
        self.preview_button.setMinimumSize(200, 100)
        right_layout.addWidget(self.preview_button, alignment=Qt.AlignmentFlag.AlignCenter)
        right_layout.addStretch()

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

        add_btn.clicked.connect(self._add_style)
        edit_btn.clicked.connect(self._edit_style)
        remove_btn.clicked.connect(self._remove_style)
        duplicate_btn.clicked.connect(self._duplicate_style)
        move_up_btn.clicked.connect(self._move_style_up)
        move_down_btn.clicked.connect(self._move_style_down)

        self.style_table.cellDoubleClicked.connect(self._on_style_double_click)
        self.style_table.itemSelectionChanged.connect(self._on_style_selection_changed)
        self._refresh_style_table()
        self._on_style_selection_changed()

    def _refresh_style_table(self):
        self.style_table.setRowCount(0)
        for i, style in enumerate(self.style_manager.conditional_styles):
            self.style_table.insertRow(i)
            self.style_table.setItem(i, 0, QTableWidgetItem(str(i + 1)))
            self.style_table.setItem(i, 1, QTableWidgetItem(self._describe_condition(style)))

            preview_item = QTableWidgetItem()
            bg = style.properties.get("background_color")
            if bg:
                preview_item.setBackground(QColor(bg))
            fg = style.properties.get("text_color")
            if fg:
                preview_item.setForeground(QColor(fg))
            text = style.text_value if getattr(style, "text_type", "") == "Text" else ""
            preview_item.setText(text)
            icon_path = style.properties.get("icon")
            if icon_path:
                preview_item.setIcon(QIcon(icon_path))
            self.style_table.setItem(i, 2, preview_item)
            self.style_table.setItem(i, 3, QTableWidgetItem(style.style_id))

    def _describe_condition(self, style: ConditionalStyle) -> str:
        condition = getattr(style, 'condition', None)
        if condition:
            return str(condition)
        cfg = getattr(style, 'condition_data', {}) or {}
        mode = cfg.get('mode', 'Ordinary')
        if mode == 'Ordinary':
            return 'Always'
        tag = self._format_value(cfg.get('tag'))
        if mode in ('On', 'Off'):
            return f"{tag} is {mode}"
        if mode == 'Range':
            op = cfg.get('operator', '==')
            if op in ('between', 'outside'):
                lower = self._format_value(cfg.get('lower'))
                upper = self._format_value(cfg.get('upper'))
                word = 'between' if op == 'between' else 'outside'
                return f"{tag} {word} {lower} and {upper}"
            operand = self._format_value(cfg.get('operand'))
            return f"{tag} {op} {operand}"
        return ''

    def _format_value(self, data: Optional[Dict[str, Any]]) -> str:
        if not data:
            return '?' 
        value = data.get('value')
        if data.get('source') == 'tag' and isinstance(value, dict):
            return value.get('tag_name', '')
        return str(value)

    def _add_style(self):
        dialog = ConditionalStyleEditorDialog(self)
        if dialog.exec():
            new_style = dialog.get_style()
            if new_style:
                self.style_manager.add_style(new_style)
                self._refresh_style_table()
                row = len(self.style_manager.conditional_styles) - 1
                self.style_table.selectRow(row)
                self._on_style_selection_changed()

    def _edit_style(self):
        selected_rows = self.style_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if row >= len(self.style_manager.conditional_styles):
            return
        style = self.style_manager.conditional_styles[row]
        dialog = ConditionalStyleEditorDialog(self, style)
        if dialog.exec():
            updated_style = dialog.get_style()
            if updated_style:
                # Use manager helper to ensure internal structures stay consistent
                self.style_manager.update_style(row, updated_style)
                self._refresh_style_table()
                self.style_table.selectRow(row)
                self._on_style_selection_changed()


    def _remove_style(self):
        selected_rows = self.style_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if 0 <= row < len(self.style_manager.conditional_styles):
            self.style_manager.remove_style(row)
            self._refresh_style_table()

    def _duplicate_style(self):
        selected_rows = self.style_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        if 0 <= row < len(self.style_manager.conditional_styles):
            original = self.style_manager.conditional_styles[row]
            duplicated = copy.deepcopy(original)
            self.style_manager.conditional_styles.insert(row + 1, duplicated)
            self._refresh_style_table()
            self.style_table.selectRow(row + 1)
            self._on_style_selection_changed()

    def _move_style_up(self):
        selected_rows = self.style_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        styles = self.style_manager.conditional_styles
        if row > 0:
            styles.insert(row - 1, styles.pop(row))
            self._refresh_style_table()
            self.style_table.selectRow(row - 1)

    def _move_style_down(self):
        selected_rows = self.style_table.selectionModel().selectedRows()
        if not selected_rows:
            return
        row = selected_rows[0].row()
        styles = self.style_manager.conditional_styles
        if row < len(styles) - 1:
            styles.insert(row + 1, styles.pop(row))
            self._refresh_style_table()
            self.style_table.selectRow(row + 1)

    def _on_style_double_click(self, row, column):
        self._edit_style()

    def _on_style_selection_changed(self):
        selected_rows = self.style_table.selectionModel().selectedRows()
        if not selected_rows:
            self.style_properties_stack.setCurrentIndex(0)
            self.style_properties_group.setTitle("Style Properties")
            self.preview_button.setStyleSheet("")
            self.preview_button.setText("Preview")
            self.preview_button.set_icon("")
            self.preview_button.set_hover_icon("")
            self.preview_button.set_click_icon("")
            return

        row = selected_rows[0].row()
        if row >= len(self.style_manager.conditional_styles):
            self.style_properties_stack.setCurrentIndex(0)
            return

        style = self.style_manager.conditional_styles[row]

        # Populate labels
        self.style_id_label.setText(style.style_id)
        self.tooltip_label.setText(style.tooltip)
        self.bg_color_label.setText(style.properties.get("background_color", ""))
        self.text_color_label.setText(style.properties.get("text_color", ""))
        self.hover_bg_color_label.setText(style.hover_properties.get("background_color", ""))
        self.hover_text_color_label.setText(style.hover_properties.get("text_color", ""))
        self.click_bg_color_label.setText(style.click_properties.get("background_color", ""))
        self.click_text_color_label.setText(style.click_properties.get("text_color", ""))

        self.style_properties_stack.setCurrentIndex(1)
        self.style_properties_group.setTitle(f"Style Properties - {style.style_id}")

        # Apply style to preview button using the style's own properties
        # rather than running it through ``get_active_style`` which depends on
        # condition evaluation.  This ensures the user sees the newly added or
        # edited style immediately regardless of its condition configuration.

        # ``ConditionalStyle._normalize_state`` guarantees all expected keys
        # are present (font family, size, bold/italic, etc.).
        base_props = ConditionalStyle._normalize_state(style.properties)
        hover_props = ConditionalStyle._normalize_state(style.hover_properties)
        click_props = ConditionalStyle._normalize_state(style.click_properties)

        # Placeholder tag values that would satisfy the style's condition.  The
        # values are not currently used because the preview bypasses condition
        # checks, but they are provided for completeness should future preview
        # logic require condition evaluation.
        cond_cfg = getattr(style, "condition_data", {"mode": "Ordinary"})
        _tag_values = {}
        tag_def = cond_cfg.get("tag") or {}
        tag_name = (
            tag_def.get("tag_name")
            or (tag_def.get("value") or {}).get("tag_name")
        )
        if tag_name:
            mode = cond_cfg.get("mode")
            if mode == "On":
                _tag_values[tag_name] = 1
            elif mode == "Off":
                _tag_values[tag_name] = 0
            elif mode == "Range":
                op = cond_cfg.get("operator", "==")
                if op in ("between", "outside"):
                    lower = cond_cfg.get("lower", {}).get("value")
                    upper = cond_cfg.get("upper", {}).get("value")
                    try:
                        lower_val = float(lower)
                        upper_val = float(upper)
                        _tag_values[tag_name] = (lower_val + upper_val) / 2
                    except Exception:
                        _tag_values[tag_name] = 0
                else:
                    operand = cond_cfg.get("operand", {}).get("value")
                    try:
                        _tag_values[tag_name] = float(operand)
                    except Exception:
                        _tag_values[tag_name] = 0


        # Build QSS for preview including font properties
        base_font_family_name = base_props.get('font_family', '')
        base_font_family = f"'{base_font_family_name}'" if base_font_family_name else 'inherit'
        base_font_size = base_props.get('font_size', 10)
        base_font_weight = 'bold' if base_props.get('bold', False) else 'normal'
        base_font_style = 'italic' if base_props.get('italic', False) else 'normal'

        hover_font_family_name = hover_props.get('font_family', base_font_family_name)
        hover_font_family = (
            f"'{hover_font_family_name}'" if hover_font_family_name else base_font_family
        )
        hover_font_size = hover_props.get('font_size', base_font_size)
        hover_font_weight = 'bold' if hover_props.get('bold', base_props.get('bold', False)) else 'normal'
        hover_font_style = 'italic' if hover_props.get('italic', base_props.get('italic', False)) else 'normal'

        click_font_family_name = click_props.get('font_family', hover_font_family_name)
        click_font_family = (
            f"'{click_font_family_name}'" if click_font_family_name else hover_font_family
        )
        click_font_size = click_props.get('font_size', hover_font_size)
        click_font_weight = (
            'bold'
            if click_props.get(
                'bold', hover_props.get('bold', base_props.get('bold', False))
            )
            else 'normal'
        )
        click_font_style = (
            'italic'
            if click_props.get(
                'italic', hover_props.get('italic', base_props.get('italic', False))
            )
            else 'normal'
        )

        h_align = base_props.get('h_align')
        v_align = base_props.get('v_align')
        alignment_css = ""
        if h_align:
            alignment_css += f"    text-align: {h_align};\n"
        if h_align or v_align:
            h_flag = {
                'left': 'AlignLeft',
                'center': 'AlignHCenter',
                'right': 'AlignRight',
            }.get(h_align, 'AlignHCenter')
            v_flag = {
                'top': 'AlignTop',
                'middle': 'AlignVCenter',
                'bottom': 'AlignBottom',
            }.get(v_align, 'AlignVCenter')
            alignment_css += f"    qproperty-alignment: {v_flag}|{h_flag};\n"

        qss = (
            "QPushButton {\n"
            f"    background-color: {base_props.get('background_color', 'transparent')};\n"
            f"    color: {base_props.get('text_color', '#000000')};\n"

            f"    border-radius: {base_props.get('border_radius', 0)}px;\n"
            f"    font-family: {base_font_family};\n"
            f"    font-size: {base_font_size}pt;\n"
            f"    font-weight: {base_font_weight};\n"
            f"    font-style: {base_font_style};\n"
            f"{alignment_css}"
            "}\n"
            "QPushButton:hover {\n"
            f"    background-color: {hover_props.get('background_color', base_props.get('background_color', 'transparent'))};\n"
            f"    color: {hover_props.get('text_color', base_props.get('text_color', '#000000'))};\n"
            f"    font-family: {hover_font_family};\n"
            f"    font-size: {hover_font_size}pt;\n"
            f"    font-weight: {hover_font_weight};\n"
            f"    font-style: {hover_font_style};\n"
            "}\n"
            "QPushButton:pressed {\n"
            f"    background-color: {click_props.get('background_color', hover_props.get('background_color', base_props.get('background_color', 'transparent')))};\n"
            f"    color: {click_props.get('text_color', hover_props.get('text_color', base_props.get('text_color', '#000000')))};\n"
            f"    font-family: {click_font_family};\n"
            f"    font-size: {click_font_size}pt;\n"
            f"    font-weight: {click_font_weight};\n"
            f"    font-style: {click_font_style};\n"
            "}\n"
        )
        self.preview_button.setStyleSheet(qss)
        self.preview_button.set_icon(style.icon)
        self.preview_button.set_hover_icon(style.hover_icon)
        self.preview_button.set_click_icon(style.click_icon)
        icon_sz = style.properties.get('icon_size', 48)
        self.preview_button.set_icon_size(icon_sz)

        text = style.text_value if style.text_type == "Text" else ""
        self.preview_button.setText(text or "Preview")
        self.preview_button.setToolTip(style.tooltip)

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
        # Serialize conditional styles, preserving any future fields
        style_data = self.style_manager.to_dict()
        updated_props["conditional_styles"] = style_data.get("conditional_styles", [])
        if style_data.get("default_style"):
            updated_props["default_style"] = style_data["default_style"]
        return updated_props
