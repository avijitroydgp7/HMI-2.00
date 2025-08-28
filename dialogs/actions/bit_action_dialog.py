# dialogs/actions/bit_action_dialog.py
# Configuration dialog for Bit Actions.

from PyQt6.QtWidgets import (
    QDialogButtonBox, QButtonGroup, QRadioButton, QWidget,
    QVBoxLayout, QGroupBox, QGridLayout, QLabel, QComboBox, QStackedWidget,
    QScrollArea, QHBoxLayout, QDialog
)
from PyQt6.QtCore import Qt
from typing import Dict, Optional

from ..widgets import TagSelector, CollapsibleBox
from .range_helpers import DataTypeMapper, validate_range_section
from .constants import ActionType, TriggerMode
from .trigger_utils import TriggerUI

class BitActionDialog(QDialog):
    """
    A dialog to configure a Bit Action for a button, with a custom title bar
    and an advanced trigger section.
    """
    def __init__(self, parent=None, action_data: Optional[Dict] = None):
        super().__init__(parent)
        self.setWindowTitle("Bit Action Configuration")
        self.setMinimumWidth(600)
        # Provide a sensible initial size without fixing the height
        self.resize(600, 650)
        # Use default styling so dropdowns match the Conditional Style window

        content_layout = QVBoxLayout(self)
        content_layout.setContentsMargins(0,0,0,0)

        # Scroll Area for all content
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("ContentScrollArea")
        
        scroll_content_widget = QWidget()
        scroll_content_widget.setObjectName("ScrollContainer")
        scroll_area.setWidget(scroll_content_widget)

        scrollable_layout = QVBoxLayout(scroll_content_widget)
        scrollable_layout.setSpacing(10)
        scrollable_layout.setContentsMargins(15, 15, 15, 15)

        # --- Main Action Section ---
        self._build_main_action_ui(scrollable_layout)

        # --- Trigger Section ---
        self._build_trigger_ui(scrollable_layout)
        
        scrollable_layout.addStretch(1)
        content_layout.addWidget(scroll_area)

        # --- Error display and Dialog Buttons ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)

        self.error_label = QLabel()
        self.error_label.setStyleSheet("color: #E57373;")

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.error_label)
        bottom_layout.addStretch(1)
        bottom_layout.addWidget(self.button_box)
        content_layout.addLayout(bottom_layout)

        # --- Connect signals & initialize ---
        self._connect_signals()
        
        if action_data:
            self._load_data(action_data)
        else:
            self._on_trigger_mode_changed(self.trigger_mode_combo.currentText())

        self._validate_form()

    def _build_main_action_ui(self, parent_layout):
        main_group = QGroupBox("Main Action")
        main_group.setObjectName("CardGroup")
        layout = QVBoxLayout(main_group)
        
        # MODIFIED: Use TagSelector and set it to fixed "Tag" mode
        self.target_tag_selector = TagSelector()
        self.target_tag_selector.set_allowed_tag_types(["BOOL"])
        self.target_tag_selector.main_tag_selector.set_mode_fixed("Tag")
        layout.addWidget(QLabel("<b>Target Tag</b>"))
        layout.addWidget(self.target_tag_selector)
        
        # Container for the simple action modes
        self.action_mode_container = QWidget()
        action_mode_layout = QHBoxLayout(self.action_mode_container)
        action_mode_layout.setContentsMargins(0, 10, 0, 0)
        
        self.mode_group = QButtonGroup(self)
        modes = ["Momentary", "Alternate", "Set", "Reset"]
        for mode in modes:
            rb = QRadioButton(mode)
            self.mode_group.addButton(rb)
            action_mode_layout.addWidget(rb)
        
        self.mode_group.buttons()[0].setChecked(True)
        layout.addWidget(self.action_mode_container)
        
        parent_layout.addWidget(main_group)

    def _build_trigger_ui(self, parent_layout):
        # Build trigger UI via shared helper and expose fields on self to keep
        # compatibility with existing code paths and signal hookups.
        self._trigger_helper = TriggerUI(parent=self, on_change=self._validate_form)

        # Expose helper widgets/attributes to instance to preserve names
        self.trigger_box = self._trigger_helper.box
        self.trigger_mode_combo = self._trigger_helper.mode_combo
        self.trigger_stack = self._trigger_helper.stack
        self.trigger_empty_page = self._trigger_helper.trigger_empty_page
        self.trigger_onoff_page = self._trigger_helper.trigger_onoff_page
        self.trigger_range_page = self._trigger_helper.trigger_range_page

        # On/Off
        self.on_off_tag_selector = self._trigger_helper.on_off_tag_selector

        # Range
        self.range_operand1_selector = self._trigger_helper.range_operand1_selector
        self.range_operator_combo = self._trigger_helper.range_operator_combo
        self.range_rhs_stack = self._trigger_helper.range_rhs_stack
        self.range_operand2_selector = self._trigger_helper.range_operand2_selector
        self.range_lower_bound_selector = self._trigger_helper.range_lower_bound_selector
        self.range_upper_bound_selector = self._trigger_helper.range_upper_bound_selector

        # Keep operator change behavior consistent with prior implementation
        if self.range_operator_combo is not None:
            self.range_operator_combo.currentTextChanged.connect(self._on_range_operator_changed)

        parent_layout.addWidget(self.trigger_box)

    def _connect_signals(self):
        self.trigger_mode_combo.currentTextChanged.connect(self._on_trigger_mode_changed)
        self.target_tag_selector.inputChanged.connect(self._validate_form)

    def _on_trigger_mode_changed(self, mode: str):
        # Delegate to helper and revalidate the form
        if hasattr(self, "_trigger_helper") and self._trigger_helper:
            self._trigger_helper.on_mode_changed(mode)
        self._validate_form()

    def _on_range_operator_changed(self, operator: str):
        # Delegate to helper so behavior stays consistent
        if hasattr(self, "_trigger_helper") and self._trigger_helper:
            self._trigger_helper.on_range_operator_changed(operator)
        self._validate_form()

    def _load_data(self, data):
        self._set_tag_selector_data(self.target_tag_selector, data.get("target_tag"))
        
        trigger_data = data.get("trigger", {})
        # Load trigger via shared helper
        self._trigger_helper.load_data(trigger_data)
        
        mode = data.get("mode", "Momentary")
        for button in self.mode_group.buttons():
            if button.text() == mode:
                button.setChecked(True)
                break
        
        self.trigger_box.setExpanded(bool(trigger_data))

    def _set_tag_selector_data(self, selector: TagSelector, data: Optional[Dict]):
        if selector and data:
            selector.set_data(data)

    def _validate_form(self, *args):
        error_msg = None
        is_valid = True

        if not self.target_tag_selector.get_data():
            error_msg = "Target Tag must be selected."
            is_valid = False

        trigger_mode = self.trigger_mode_combo.currentText()
        trigger_is_valid, trigger_error = self._trigger_helper.validate()
        if not trigger_is_valid and error_msg is None:
            error_msg = trigger_error

        is_valid &= trigger_is_valid
        if trigger_mode == TriggerMode.ORDINARY.value:
            self.trigger_box.setStatus(CollapsibleBox.Status.NEUTRAL)
        else:
            self.trigger_box.setStatus(CollapsibleBox.Status.OK if trigger_is_valid else CollapsibleBox.Status.ERROR)

        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button:
            ok_button.setEnabled(is_valid)

        self.error_label.setText(error_msg or "")

    def get_data(self) -> Optional[Dict]:
        target_tag_data = self.target_tag_selector.get_data()
        if not target_tag_data:
            return None
            
        action_data = {
            "action_type": ActionType.BIT.value,
            "target_tag": target_tag_data,
            "mode": self.mode_group.checkedButton().text()
        }

        trigger_dict = self._trigger_helper.get_data()
        if trigger_dict is not None:
            action_data["trigger"] = trigger_dict
        
        target_str = self._format_operand_for_display(target_tag_data)
        mode_str = action_data.get("mode", "N/A")
        trigger_mode = self.trigger_mode_combo.currentText()
        if trigger_mode != TriggerMode.ORDINARY.value:
            mode_str = f"Triggered ({trigger_mode})"
            
        action_data["details"] = f"{mode_str} -> {target_str}"
        
        return action_data

    def _format_operand_for_display(self, data: Optional[Dict]) -> str:
        if not data:
            return "?"
        main_tag = data.get("main_tag")
        if not main_tag:
            return "?"
        
        source = main_tag.get("source")
        value = main_tag.get("value")

        if source == "constant":
            return str(value)
        elif source == "tag":
            db_name = value.get('db_name', '??')
            tag_name = value.get('tag_name', '??')
            indices = data.get("indices", [])
            index_str = "".join(f"[{self._format_operand_for_display({'main_tag': idx})}]" for idx in indices)
            return f"[{db_name}]::{tag_name}{index_str}"
        return "?"
