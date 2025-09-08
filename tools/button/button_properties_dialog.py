# components/button/button_properties_dialog.py
from PyQt6.QtWidgets import (
    QTabWidget,
    QWidget,
    QDialogButtonBox,
    QLabel,
    QFormLayout,
    QLineEdit,
    QTableView,
    QHeaderView,
    QPushButton,
    QHBoxLayout,
    QAbstractItemView,
    QVBoxLayout,
    QSplitter,
    QGroupBox,
    QStackedWidget,
    QDialog,
    QListWidget,
    QListWidgetItem,
    QToolButton,
    QStyle,
)
from PyQt6.QtCore import Qt, QSize, pyqtSignal
from utils.dpi import dpi_scale
from typing import Dict, Any, Optional
import logging
import copy
import re

from tools.button.actions.select_action_type_dialog import SelectActionTypeDialog
from tools.button.actions.bit_action_dialog import BitActionDialog
from tools.button.actions.word_action_dialog import WordActionDialog
from tools.button.actions.constants import ActionType, TriggerMode
from .button_actions_model import ButtonActionsModel

from .conditional_style import (
    ConditionalStyleManager,
    ConditionalStyle,
    ConditionalStyleEditorDialog,
    PreviewButton,
    SwitchButton,
)
from utils.percentage import percent_to_value, value_to_percent


def scale_stylesheet(qss: str, scale: float) -> str:
    """Scale numeric px/pt values in ``qss`` by ``scale``."""
    def repl(match: re.Match) -> str:
        value = float(match.group(1))
        unit = match.group(2)
        return f"{value * scale:.0f}{unit}"

    return re.sub(r"(\d+(?:\.\d+)?)(px|pt)", repl, qss)


class ButtonPropertiesWidget(QWidget):
    """Widget exposing the Action and Style tabs used by the dialog and
    the property editor."""

    properties_changed = pyqtSignal(dict)

    def __init__(self, properties: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.properties = copy.deepcopy(properties)

        # Initialize conditional style manager
        self._load_styles(self.properties)

        main_layout = QVBoxLayout(self)

        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)

        self.action_tab = QWidget()
        self.style_tab = QWidget()

        self.tab_widget.addTab(self.action_tab, "Action")
        self.tab_widget.addTab(self.style_tab, "Style")

        self._populate_action_tab()
        self._populate_style_tab()
        self._refresh_style_list()
        self._on_style_selection_changed()

    # ------------------------------------------------------------------
    # Public API -------------------------------------------------------
    def set_properties(self, properties: Dict[str, Any]) -> None:
        """Replace the current property payload and refresh the UI."""
        self.properties = copy.deepcopy(properties)

        # Update action model backing list
        self.action_model._actions = self.properties["actions"]
        self.action_model.refresh()

        # Recreate style manager from dict
        self._load_styles(self.properties)

        self._refresh_style_list()
        self._on_style_selection_changed()

    def get_data(self) -> Dict[str, Any]:
        updated_props = self.properties.copy()
        updated_props["actions"] = self.properties.get("actions", [])
        # Save label and text color fallback
        updated_props["label"] = self.properties.get("label", "Button")
        updated_props["text_color"] = self.properties.get("text_color", "#ffffff")

        # Serialize conditional styles and construct default style block
        style_data = self.style_manager.to_dict()
        updated_props["conditional_styles"] = style_data.get(
            "conditional_styles", []
        )
        first_style = (
            updated_props["conditional_styles"][0]
            if updated_props["conditional_styles"]
            else {}
        )
        default_style = {
            "style_id": first_style.get(
                "style_id", self.properties.get("default_style", {}).get("style_id", "")
            ),
            "tooltip": first_style.get(
                "tooltip", self.properties.get("default_style", {}).get("tooltip", "")
            ),
            "style_sheet": first_style.get(
                "style_sheet",
                self.properties.get("default_style", {}).get("style_sheet", ""),
            ),
            "tags": first_style.get(
                "tags", self.properties.get("default_style", {}).get("tags", [])
            ),
            "text": first_style.get(
                "text", self.properties.get("default_style", {}).get("text", "")
            ),
            "properties": style_data.get("default_style", {}),
            "hover_properties": first_style.get(
                "hover_properties",
                self.properties.get("default_style", {}).get("hover_properties", {}),
            ),
            "pressed_properties": first_style.get(
                "pressed_properties",
                self.properties.get("default_style", {}).get("pressed_properties", {}),
            ),
            "disabled_properties": first_style.get(
                "disabled_properties",
                self.properties.get("default_style", {}).get("disabled_properties", {}),
            ),
        }
        # Expose key properties alongside the nested dict for compatibility
        default_style.update(default_style.get("properties", {}))
        updated_props["default_style"] = default_style

        # Flatten default style for canvas/runtime consumption
        updated_props.update(default_style.get("properties", {}))
        if default_style.get("hover_properties"):
            updated_props["hover_properties"] = default_style["hover_properties"]
        else:
            updated_props.pop("hover_properties", None)
        if default_style.get("pressed_properties"):
            updated_props["pressed_properties"] = default_style["pressed_properties"]
        else:
            updated_props.pop("pressed_properties", None)
        if default_style.get("disabled_properties"):
            updated_props["disabled_properties"] = default_style["disabled_properties"]
        else:
            updated_props.pop("disabled_properties", None)
        if default_style.get("tags"):
            updated_props["tags"] = default_style["tags"]
        else:
            updated_props.pop("tags", None)
        if default_style.get("text"):
            updated_props["text"] = default_style["text"]
        else:
            updated_props.pop("text", None)
        if default_style.get("tooltip"):
            updated_props["tooltip"] = default_style["tooltip"]
        else:
            updated_props.pop("tooltip", None)
        if default_style.get("style_sheet"):
            updated_props["style_sheet"] = default_style["style_sheet"]
        else:
            updated_props.pop("style_sheet", None)

        return updated_props

    # Internal helpers -------------------------------------------------
    def _load_styles(self, properties: Dict[str, Any]) -> None:
        """Create and populate ``ConditionalStyleManager`` from ``properties``."""
        self.style_manager = ConditionalStyleManager()
        default_style = properties.get("default_style", {})
        self.style_manager.default_style = default_style.get(
            "properties", default_style
        )
        for style_data in properties.get("conditional_styles", []):
            try:
                style = ConditionalStyle.from_dict(style_data)
                self.style_manager.add_style(style)
            except Exception as e:
                logging.getLogger(__name__).warning(
                    "Failed to load conditional style (style_id=%r). Typical causes: "
                    "missing keys, wrong types, invalid color/icon values, or malformed condition data. "
                    "Error: %s. Data: %r",
                    style_data.get("style_id", "<unknown>"),
                    e,
                    style_data,
                )

        # Backwards compatibility: seed a basic style from legacy keys
        if not self.style_manager.conditional_styles:
            base_props = {
                k: v
                for k, v in properties.items()
                if k
                not in {
                    "actions",
                    "size",
                    "hover_properties",
                    "pressed_properties",
                    "disabled_properties",
                    "label",
                    "default_style",
                    "conditional_styles",
                }
            }
            if properties.get("label"):
                base_props["text_value"] = properties.get("label", "")
                base_props.setdefault("text_type", "Text")
            hover_props = copy.deepcopy(properties.get("hover_properties", {}))
            pressed_props = copy.deepcopy(properties.get("pressed_properties", {}))
            disabled_props = copy.deepcopy(properties.get("disabled_properties", {}))
            if properties.get("icon"):
                base_props.setdefault("icon", properties.get("icon"))
            if properties.get("hover_icon"):
                hover_props.setdefault("icon", properties.get("hover_icon"))
            legacy_style = ConditionalStyle.from_dict(
                {
                    "style_id": str(properties.get("style_id", "1")),
                    "properties": base_props,
                    "hover_properties": hover_props,
                    "pressed_properties": pressed_props,
                    "disabled_properties": disabled_props,
                }
            )
            self.style_manager.add_style(legacy_style)

    def _emit_changes(self) -> None:
        data = self.get_data()
        self.properties = copy.deepcopy(data)
        self.properties_changed.emit(data)

    def _populate_action_tab(self):
        # Overall layout for the tab
        layout = QVBoxLayout(self.action_tab)
        
        # Splitter for top area
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Action view bound to model
        self.action_table = QTableView()
        self.action_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.action_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.action_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.action_table.verticalHeader().setVisible(False)

        # Bind model
        self.action_model = ButtonActionsModel(self.properties['actions'], self)
        self.action_table.setModel(self.action_model)

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
        self.action_add_btn = QPushButton("Add")
        self.action_add_btn.clicked.connect(self._add_action)
        self.action_edit_btn = QPushButton("Edit")
        self.action_edit_btn.clicked.connect(self._edit_action)
        self.action_remove_btn = QPushButton("Remove")
        self.action_remove_btn.clicked.connect(self._remove_action)
        self.action_duplicate_btn = QPushButton("Duplicate")
        self.action_duplicate_btn.clicked.connect(self._duplicate_action)
        self.action_move_up_btn = QPushButton("Move Up")
        self.action_move_up_btn.clicked.connect(self._move_action_up)
        self.action_move_down_btn = QPushButton("Move Down")
        self.action_move_down_btn.clicked.connect(self._move_action_down)

        button_layout.addWidget(self.action_add_btn)
        button_layout.addWidget(self.action_edit_btn)
        button_layout.addWidget(self.action_remove_btn)
        button_layout.addWidget(self.action_duplicate_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.action_move_up_btn)
        button_layout.addWidget(self.action_move_down_btn)
        layout.addLayout(button_layout)

        # Initialize in disabled state; will be enabled when a row is selected
        self.action_edit_btn.setEnabled(False)
        self.action_remove_btn.setEnabled(False)
        self.action_duplicate_btn.setEnabled(False)
        self.action_move_up_btn.setEnabled(False)
        self.action_move_down_btn.setEnabled(False)
        
        self.action_table.doubleClicked.connect(self._on_action_double_click)
        self.action_table.selectionModel().selectionChanged.connect(lambda *_: self._on_action_selection_changed())

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
            self.action_edit_btn.setEnabled(False)
            self.action_remove_btn.setEnabled(False)
            self.action_duplicate_btn.setEnabled(False)
            self.action_move_up_btn.setEnabled(False)
            self.action_move_down_btn.setEnabled(False)
            self.action_properties_stack.setCurrentIndex(0)
            self.action_properties_group.setTitle("Action Properties")
            return

        row = selected_rows[0].row()
        self.action_edit_btn.setEnabled(True)
        self.action_remove_btn.setEnabled(True)
        self.action_duplicate_btn.setEnabled(True)
        self.action_move_up_btn.setEnabled(row > 0)
        self.action_move_down_btn.setEnabled(row < self.action_model.rowCount() - 1)

        if row >= len(self.properties['actions']):
            self.action_properties_stack.setCurrentIndex(0)
            self.action_properties_group.setTitle("Action Properties")
            return

        action_data = self.properties['actions'][row]
        action_type = action_data.get('action_type')

        if action_type == ActionType.BIT.value:
            self.action_properties_stack.setCurrentIndex(1)
            self.action_properties_group.setTitle("Bit Action Properties")
            self._populate_bit_action_properties(action_data)
        elif action_type == ActionType.WORD.value:
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

    def _on_action_double_click(self, index):
        # Open edit dialog for the selected action
        if not index or not index.isValid():
            return
        row = index.row()
        if row < 0 or row >= len(self.properties.get('actions', [])):
            return
        action_data = self.properties['actions'][row]
        action_type = action_data.get('action_type')
        action_dialog = None
        if action_type == ActionType.BIT.value:
            action_dialog = BitActionDialog(self, action_data=action_data)
        elif action_type == ActionType.WORD.value:
            action_dialog = WordActionDialog(self, action_data=action_data)
        if action_dialog and action_dialog.exec():
            new_action_data = action_dialog.get_data()
            if new_action_data:
                self.action_model.update_action(row, new_action_data)

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
        
        mode = trigger_data.get('mode', TriggerMode.ORDINARY.value)
        if mode == TriggerMode.ORDINARY.value:
            return ""
        elif mode == TriggerMode.ON.value:
            tag_data = trigger_data.get('tag')
            if tag_data:
                tag_display = self._format_operand_for_display(tag_data)
                return f"ON = {tag_display}"
            return "ON"
        elif mode == TriggerMode.OFF.value:
            tag_data = trigger_data.get('tag')
            if tag_data:
                tag_display = self._format_operand_for_display(tag_data)
                return f"OFF = {tag_display}"
            return "OFF"
        elif mode == TriggerMode.RANGE.value:
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
        # Underlying list may have changed externally; notify the model
        if hasattr(self, 'action_model'):
            self.action_model.refresh()

    def _add_action(self):
        type_dialog = SelectActionTypeDialog(self)
        if not type_dialog.exec(): return

        action_type = type_dialog.selected_action_type
        action_dialog = None
        if action_type == ActionType.BIT.value:
            action_dialog = BitActionDialog(self)
        elif action_type == ActionType.WORD.value:
            action_dialog = WordActionDialog(self)
        
        if action_dialog and action_dialog.exec():
            action_data = action_dialog.get_data()
            if action_data:
                new_row = self.action_model.rowCount()
                self.action_model.insert_action(new_row, action_data)
                self.action_table.selectRow(new_row)
                self._on_action_selection_changed()
                self._emit_changes()

    def _edit_action(self):
        selected_rows = self.action_table.selectionModel().selectedRows()
        if not selected_rows: return
        row = selected_rows[0].row()
        
        action_data = self.properties['actions'][row]
        action_type = action_data.get('action_type')

        action_dialog = None
        if action_type == ActionType.BIT.value:
            action_dialog = BitActionDialog(self, action_data=action_data)
        elif action_type == ActionType.WORD.value:
            action_dialog = WordActionDialog(self, action_data=action_data)

        if action_dialog and action_dialog.exec():
            new_action_data = action_dialog.get_data()
            if new_action_data:
                self.action_model.update_action(row, new_action_data)
                self.action_table.selectRow(row)
                self._on_action_selection_changed()
                self._emit_changes()

    def _remove_action(self):
        selected_rows = self.action_table.selectionModel().selectedRows()
        if not selected_rows: return
        row = selected_rows[0].row()
        self.action_model.remove_action(row)
        self._on_action_selection_changed()
        self._emit_changes()

    def _move_action_up(self):
        selected_rows = self.action_table.selectionModel().selectedRows()
        if not selected_rows: return
        row = selected_rows[0].row()
        if row > 0:
            self.action_model.move_action(row, row - 1)
            self.action_table.selectRow(row - 1)
            self._on_action_selection_changed()
            self._emit_changes()

    def _move_action_down(self):
        selected_rows = self.action_table.selectionModel().selectedRows()
        if not selected_rows: return
        row = selected_rows[0].row()
        if row < self.action_model.rowCount() - 1:
            self.action_model.move_action(row, row + 1)
            self.action_table.selectRow(row + 1)
            self._on_action_selection_changed()
            self._emit_changes()

    def _duplicate_action(self):
        """Duplicate the selected action"""
        selected_rows = self.action_table.selectionModel().selectedRows()
        if not selected_rows: return
        row = selected_rows[0].row()
        
        if row < self.action_model.rowCount():
            # Create a deep copy of the action
            original_action = self.properties['actions'][row]
            duplicated_action = copy.deepcopy(original_action)

            # Insert the duplicated action after the original
            new_row = row + 1
            self.action_model.duplicate_action(row, duplicated_action)
            self.action_table.selectRow(new_row)
            self._on_action_selection_changed()
            self._emit_changes()

    def _populate_style_tab(self):
        # Overall layout for the tab
        layout = QVBoxLayout(self.style_tab)

        # Splitter for top area
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Left panel: Style list with preview swatches
        self.style_list = QListWidget()
        self.style_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.style_list.setUniformItemSizes(True)
        splitter.addWidget(self.style_list)

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
        info_layout.addRow("Style ID:", self.style_id_label)
        info_layout.addRow("Tooltip:", self.tooltip_label)
        info_layout.addRow("Base BG:", self.bg_color_label)
        info_layout.addRow("Base Text:", self.text_color_label)
        info_layout.addRow("Hover BG:", self.hover_bg_color_label)
        info_layout.addRow("Hover Text:", self.hover_text_color_label)
        self.style_properties_stack.addWidget(info_widget)

        right_layout.addWidget(self.style_properties_group)

        # Preview widgets
        self.preview_button = PreviewButton("")
        self.preview_button.setMinimumSize(dpi_scale(200), dpi_scale(100))
        self.preview_switch = SwitchButton()
        self.preview_stack = QStackedWidget()
        self.preview_stack.addWidget(self.preview_button)
        self.preview_stack.addWidget(self.preview_switch)
        right_layout.addWidget(self.preview_stack, alignment=Qt.AlignmentFlag.AlignCenter)
        right_layout.addStretch()

        splitter.addWidget(right_panel)

        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        # Add splitter to the main layout
        layout.addWidget(splitter)
        
        # Toolbar buttons at the bottom, outside the splitter
        button_layout = QHBoxLayout()
        self.style_add_btn = QToolButton()
        self.style_add_btn.setText("Add")
        self.style_add_btn.setIcon(self.style_add_btn.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        self.style_edit_btn = QToolButton()
        self.style_edit_btn.setText("Edit")
        self.style_edit_btn.setIcon(self.style_edit_btn.style().standardIcon(QStyle.StandardPixmap.SP_DialogApplyButton))
        self.style_remove_btn = QToolButton()
        self.style_remove_btn.setText("Delete")
        self.style_remove_btn.setIcon(self.style_remove_btn.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
        self.style_duplicate_btn = QToolButton()
        self.style_duplicate_btn.setText("Duplicate")
        self.style_duplicate_btn.setIcon(self.style_duplicate_btn.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogNewFolder))
        self.style_move_up_btn = QToolButton()
        self.style_move_up_btn.setText("Up")
        self.style_move_up_btn.setIcon(self.style_move_up_btn.style().standardIcon(QStyle.StandardPixmap.SP_ArrowUp))
        self.style_move_down_btn = QToolButton()
        self.style_move_down_btn.setText("Down")
        self.style_move_down_btn.setIcon(self.style_move_down_btn.style().standardIcon(QStyle.StandardPixmap.SP_ArrowDown))

        for btn in (self.style_add_btn, self.style_edit_btn, self.style_remove_btn, self.style_duplicate_btn, self.style_move_up_btn, self.style_move_down_btn):
            btn.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)

        button_layout.addWidget(self.style_add_btn)
        button_layout.addWidget(self.style_edit_btn)
        button_layout.addWidget(self.style_remove_btn)
        button_layout.addWidget(self.style_duplicate_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.style_move_up_btn)
        button_layout.addWidget(self.style_move_down_btn)
        layout.addLayout(button_layout)

        self.style_add_btn.clicked.connect(self._add_style)
        self.style_edit_btn.clicked.connect(self._edit_style)
        self.style_remove_btn.clicked.connect(self._remove_style)
        self.style_duplicate_btn.clicked.connect(self._duplicate_style)
        self.style_move_up_btn.clicked.connect(self._move_style_up)
        self.style_move_down_btn.clicked.connect(self._move_style_down)

        # Initialize in disabled state; will be enabled when a row is selected
        self.style_edit_btn.setEnabled(False)
        self.style_remove_btn.setEnabled(False)
        self.style_duplicate_btn.setEnabled(False)
        self.style_move_up_btn.setEnabled(False)
        self.style_move_down_btn.setEnabled(False)

        self.style_list.itemDoubleClicked.connect(self._on_style_double_click)
        self.style_list.itemSelectionChanged.connect(self._on_style_selection_changed)
        self._refresh_style_list()
        self._on_style_selection_changed()

    def _build_swatch_widget(self, index: int, style: ConditionalStyle) -> QWidget:
        """Create a small swatch widget to preview the style in the list."""
        container = QWidget()
        hl = QHBoxLayout(container)
        hl.setContentsMargins(
            dpi_scale(6), dpi_scale(4), dpi_scale(6), dpi_scale(4)
        )
        hl.setSpacing(dpi_scale(8))

        component_type = style.properties.get("component_type", "Standard Button")

        # Small preview widget reflecting style type
        if component_type == "Toggle Switch":
            preview = SwitchButton()
            swatch_w = dpi_scale(90)
            swatch_h = dpi_scale(36)
        else:
            preview_text = (
                style.properties.get("text_value", "")
                if style.properties.get("text_type", "Text") == "Text"
                else ""
            )
            preview = PreviewButton(preview_text or "")
            if component_type == "Circle Button":
                swatch_w = swatch_h = dpi_scale(36)
            else:
                swatch_w = dpi_scale(90)
                swatch_h = dpi_scale(36)
        preview.setFixedSize(swatch_w, swatch_h)
        base_w = 200
        base_h = 200 if component_type == "Circle Button" else 100
        min_dim = min(base_w, base_h)
        scale = min(swatch_w / dpi_scale(base_w), swatch_h / dpi_scale(base_h))

        # Determine base/hover properties for icons and colours using the
        # manager, bypassing condition evaluation.
        base_props = self.style_manager.get_style_by_index(index)
        hover_props = self.style_manager.get_style_by_index(index, state="hover")

        # Apply either stored style sheet or basic colours
        if style.style_sheet:
            preview.setStyleSheet(scale_stylesheet(style.style_sheet, scale))
        else:
            radius_px = percent_to_value(base_props.get('border_radius', 0), min_dim)
            qss = (
                "QPushButton {\n"
                f"    background-color: {base_props.get('background_color', 'transparent')};\n"
                f"    color: {base_props.get('text_color', '#000')};\n"
                f"    border-radius: {int(radius_px * scale)}px;\n"
                "}\n"
                "QPushButton:hover {\n"
                f"    background-color: {hover_props.get('background_color', base_props.get('background_color', 'transparent'))};\n"
                f"    color: {hover_props.get('text_color', base_props.get('text_color', '#000'))};\n"
                "}\n"
            )
            preview.setStyleSheet(qss)

        if component_type != "Toggle Switch":
            # Icon handling
            preview.set_icon(
                base_props.get("icon", ""), base_props.get("icon_color")
            )
            preview.set_hover_icon(
                hover_props.get("icon", ""),
                hover_props.get("icon_color", base_props.get("icon_color")),
            )
            icon_sz = dpi_scale(percent_to_value(base_props.get("icon_size", 20), min_dim) * scale)
            preview.set_icon_size(icon_sz)
            preview.set_icon_alignment(base_props.get("icon_align", "center"))

            # Text formatting
            font_sz = percent_to_value(base_props.get("font_size", 0), base_h)
            preview.set_text_font(
                base_props.get("font_family", ""),
                max(1, int(font_sz * scale)),
                base_props.get("bold", False),
                base_props.get("italic", False),
                base_props.get("underline", False),
            )
            preview.set_text_colors(
                base_props.get("text_color", "#000"),
                hover_props.get("text_color", base_props.get("text_color", "#000")),
            )
            preview.set_text_offset(
                int(
                    base_props.get("offset_to_frame", base_props.get("offset", 0))
                    * scale
                )
            )

            # Alignment
            h_align = base_props.get(
                "h_align", base_props.get("horizontal_align", "center")
            )
            v_align = base_props.get(
                "v_align", base_props.get("vertical_align", "middle")
            )
            alignment = Qt.AlignmentFlag.AlignAbsolute
            if h_align == "left":
                alignment |= Qt.AlignmentFlag.AlignLeft
            elif h_align == "center":
                alignment |= Qt.AlignmentFlag.AlignHCenter
            elif h_align == "right":
                alignment |= Qt.AlignmentFlag.AlignRight
            if v_align == "top":
                alignment |= Qt.AlignmentFlag.AlignTop
            elif v_align == "middle":
                alignment |= Qt.AlignmentFlag.AlignVCenter
            elif v_align == "bottom":
                alignment |= Qt.AlignmentFlag.AlignBottom
            preview.setAlignment(alignment)

        # Label for style id
        label = QLabel(style.style_id)
        label.setMinimumWidth(dpi_scale(120))
        label.setToolTip(style.tooltip)

        hl.addWidget(preview)
        hl.addWidget(label)
        hl.addStretch()
        return container

    def _refresh_style_list(self):
        self.style_list.clear()
        for idx, style in enumerate(self.style_manager.conditional_styles):
            item = QListWidgetItem()
            item.setSizeHint(QSize(dpi_scale(240), dpi_scale(48)))
            self.style_list.addItem(item)
            widget = self._build_swatch_widget(idx, style)
            self.style_list.setItemWidget(item, widget)

    def _add_style(self):
        dialog = ConditionalStyleEditorDialog(self)
        if dialog.exec():
            new_style = dialog.get_style()
            if new_style:
                self.style_manager.add_style(new_style)
                self._refresh_style_list()
                row = len(self.style_manager.conditional_styles) - 1
                self.style_list.setCurrentRow(row)
                self._on_style_selection_changed()
                self._emit_changes()

    def _edit_style(self):
        row = self.style_list.currentRow()
        if row < 0:
            return
        if row >= len(self.style_manager.conditional_styles):
            return
        style = self.style_manager.conditional_styles[row]
        dialog = ConditionalStyleEditorDialog(self, style)
        if dialog.exec():
            updated_style = dialog.get_style()
            if updated_style:
                # Use manager helper to ensure internal structures stay consistent
                self.style_manager.update_style(row, updated_style)
                self._refresh_style_list()
                self.style_list.setCurrentRow(row)
                self._on_style_selection_changed()
                self._emit_changes()

    def _remove_style(self):
        row = self.style_list.currentRow()
        if row < 0:
            return
        styles = self.style_manager.conditional_styles
        if len(styles) <= 1:
            if styles:
                styles[0] = ConditionalStyle()
                self.style_manager.renumber_styles()
            self._refresh_style_list()
            self.style_list.setCurrentRow(0)
            self._on_style_selection_changed()
            self._emit_changes()
            return
        if 0 <= row < len(styles):
            self.style_manager.remove_style(row)
            self._refresh_style_list()
            self.style_list.setCurrentRow(
                min(row, len(self.style_manager.conditional_styles) - 1)
            )
            self._on_style_selection_changed()
            self._emit_changes()

    def _duplicate_style(self):
        row = self.style_list.currentRow()
        if row < 0:
            return
        if 0 <= row < len(self.style_manager.conditional_styles):
            original = self.style_manager.conditional_styles[row]
            duplicated = copy.deepcopy(original)
            self.style_manager.conditional_styles.insert(row + 1, duplicated)
            self.style_manager.renumber_styles()
            self._refresh_style_list()
            self.style_list.setCurrentRow(row + 1)
            self._on_style_selection_changed()
            self._emit_changes()

    def _move_style_up(self):
        row = self.style_list.currentRow()
        if row < 0:
            return
        styles = self.style_manager.conditional_styles
        if row > 0:
            styles.insert(row - 1, styles.pop(row))
            self.style_manager.renumber_styles()
            self._refresh_style_list()
            self.style_list.setCurrentRow(row - 1)
            self._on_style_selection_changed()
            self._emit_changes()

    def _move_style_down(self):
        row = self.style_list.currentRow()
        if row < 0:
            return
        styles = self.style_manager.conditional_styles
        if row < len(styles) - 1:
            styles.insert(row + 1, styles.pop(row))
            self.style_manager.renumber_styles()
            self._refresh_style_list()
            self.style_list.setCurrentRow(row + 1)
            self._on_style_selection_changed()
            self._emit_changes()

    def _on_style_double_click(self, *_):
        self._edit_style()

    def _on_style_selection_changed(self):
        row = self.style_list.currentRow()
        styles = self.style_manager.conditional_styles
        if row < 0 or not styles:
            self.style_edit_btn.setEnabled(False)
            self.style_remove_btn.setEnabled(False)
            self.style_duplicate_btn.setEnabled(False)
            self.style_move_up_btn.setEnabled(False)
            self.style_move_down_btn.setEnabled(False)
            self.style_properties_stack.setCurrentIndex(0)
            self.style_properties_group.setTitle("Style Properties")
            self.preview_button.setStyleSheet("")
            self.preview_button.setText("")
            self.preview_button.set_icon("")
            self.preview_button.set_hover_icon("")
            self.preview_button.setFixedSize(dpi_scale(200), dpi_scale(100))
            self.preview_switch.setStyleSheet("")
            self.preview_stack.setCurrentWidget(self.preview_button)
            self.style_list.blockSignals(True)
            self._refresh_style_list()
            self.style_list.blockSignals(False)
            return

        self.style_edit_btn.setEnabled(True)
        self.style_remove_btn.setEnabled(len(styles) > 1)
        self.style_duplicate_btn.setEnabled(True)
        self.style_move_up_btn.setEnabled(row > 0)
        self.style_move_down_btn.setEnabled(row < len(styles) - 1)
        if row >= len(styles):
            self.style_properties_stack.setCurrentIndex(0)
            self._refresh_style_list()
            return

        style = styles[row]

        # Populate labels
        self.style_id_label.setText(style.style_id)
        self.tooltip_label.setText(style.tooltip)
        self.bg_color_label.setText(style.properties.get("background_color", ""))
        self.text_color_label.setText(style.properties.get("text_color", ""))
        self.hover_bg_color_label.setText(style.hover_properties.get("background_color", ""))
        self.hover_text_color_label.setText(style.hover_properties.get("text_color", ""))

        self.style_properties_stack.setCurrentIndex(1)
        self.style_properties_group.setTitle(f"Style Properties - {style.style_id}")

        # Apply style to preview button using manager helper
        base_props = self.style_manager.get_style_by_index(row)
        hover_props = self.style_manager.get_style_by_index(row, state="hover")

        component_type = style.properties.get("component_type", "Standard Button")

        if component_type == "Toggle Switch":
            self.preview_stack.setCurrentWidget(self.preview_switch)
            if style.style_sheet:
                self.preview_switch.setStyleSheet(style.style_sheet)
            else:
                self.preview_switch.setStyleSheet("")
            self.preview_switch.setToolTip(style.tooltip)
        else:
            self.preview_stack.setCurrentWidget(self.preview_button)
            if component_type == "Circle Button":
                self.preview_button.setFixedSize(dpi_scale(200), dpi_scale(200))
                base_w = base_h = 200
            else:
                self.preview_button.setFixedSize(dpi_scale(200), dpi_scale(100))
                base_w = 200
                base_h = 100
            min_dim = min(base_w, base_h)

            if style.style_sheet:
                self.preview_button.setStyleSheet(style.style_sheet)
            else:
                radius_px = percent_to_value(base_props.get('border_radius', 0), min_dim)
                qss = (
                    "QPushButton {\n"
                    f"    background-color: {base_props.get('background_color', 'transparent')};\n"
                    f"    color: {base_props.get('text_color', '#000000')};\n"
                    f"    border-radius: {radius_px}px;\n"
                    "}\n"
                    "QPushButton:hover {\n"
                    f"    background-color: {hover_props.get('background_color', base_props.get('background_color', 'transparent'))};\n"
                    f"    color: {hover_props.get('text_color', base_props.get('text_color', '#000000'))};\n"
                    "}\n"
                )
                self.preview_button.setStyleSheet(qss)

            self.preview_button.set_icon(
                base_props.get('icon', ''), base_props.get('icon_color')
            )
            self.preview_button.set_hover_icon(
                hover_props.get('icon', ''),
                hover_props.get('icon_color', base_props.get('icon_color'))
            )
            icon_sz = percent_to_value(base_props.get('icon_size', 48), min_dim)
            self.preview_button.set_icon_size(icon_sz)
            self.preview_button.set_icon_alignment(base_props.get('icon_align', 'center'))
            text = (
                style.properties.get('text_value', '')
                if style.properties.get('text_type', 'Text') == 'Text'
                else ''
            )
            self.preview_button.setText(text or "")
            self.preview_button.setToolTip(style.tooltip)

            # Apply text formatting to mirror saved style
            font_sz = percent_to_value(base_props.get("font_size", 0), base_h)
            self.preview_button.set_text_font(
                base_props.get("font_family", ""),
                font_sz,
                base_props.get("bold", False),
                base_props.get("italic", False),
                base_props.get("underline", False),
            )
            self.preview_button.set_text_colors(
                base_props.get("text_color", "#000"),
                hover_props.get("text_color", base_props.get("text_color", "#000")),
            )
            self.preview_button.set_text_offset(
                base_props.get("offset_to_frame", base_props.get("offset", 0))
            )

            h_align = base_props.get(
                "h_align", base_props.get("horizontal_align", "center")
            )
            v_align = base_props.get(
                "v_align", base_props.get("vertical_align", "middle")
            )
            alignment = Qt.AlignmentFlag.AlignAbsolute
            if h_align == "left":
                alignment |= Qt.AlignmentFlag.AlignLeft
            elif h_align == "center":
                alignment |= Qt.AlignmentFlag.AlignHCenter
            elif h_align == "right":
                alignment |= Qt.AlignmentFlag.AlignRight
            if v_align == "top":
                alignment |= Qt.AlignmentFlag.AlignTop
            elif v_align == "middle":
                alignment |= Qt.AlignmentFlag.AlignVCenter
            elif v_align == "bottom":
                alignment |= Qt.AlignmentFlag.AlignBottom
            self.preview_button.setAlignment(alignment)

        self.style_list.blockSignals(True)
        self._refresh_style_list()
        self.style_list.setCurrentRow(row)
        self.style_list.blockSignals(False)

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


class ButtonPropertiesDialog(QDialog):
    """Wrapper dialog that hosts :class:`ButtonPropertiesWidget`. Existing
    code that previously instantiated ``ButtonPropertiesDialog`` continues to
    work without changes."""

    def __init__(self, properties: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Button Properties")
        self.setMinimumWidth(1000)
        self.setMaximumHeight(700)
        self.resize(1000, 700)

        layout = QVBoxLayout(self)
        self.widget = ButtonPropertiesWidget(properties, self)
        layout.addWidget(self.widget)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def get_data(self) -> Dict[str, Any]:
        return self.widget.get_data()
