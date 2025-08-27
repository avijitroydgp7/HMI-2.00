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

class BitActionDialog(QDialog):
    """
    A dialog to configure a Bit Action for a button, with a custom title bar
    and an advanced trigger section.
    """
    def __init__(self, parent=None, action_data: Optional[Dict] = None):
        super().__init__(parent)
        self.setWindowTitle("Bit Action Configuration")
        self.setMinimumWidth(600)
        self.setFixedHeight(650)
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
        self.trigger_box = CollapsibleBox("Trigger")
        
        trigger_content_widget = QWidget()
        trigger_main_layout = QVBoxLayout(trigger_content_widget)
        trigger_main_layout.setContentsMargins(5, 10, 5, 5)
        
        self.trigger_mode_combo = QComboBox()
        self.trigger_mode_combo.addItems(["Ordinary", "On", "Off", "Range"])
        trigger_main_layout.addWidget(self.trigger_mode_combo)
        
        self.trigger_options_container = QWidget()
        trigger_main_layout.addWidget(self.trigger_options_container)
        
        self.trigger_box.setContent(trigger_content_widget)
        parent_layout.addWidget(self.trigger_box)

    def _connect_signals(self):
        self.trigger_mode_combo.currentTextChanged.connect(self._on_trigger_mode_changed)
        self.target_tag_selector.inputChanged.connect(self._validate_form)

    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

    def _on_trigger_mode_changed(self, mode: str):
        # MODIFIED: Removed logic to hide action_mode_container
        layout = self.trigger_options_container.layout()
        if layout is not None:
            self._clear_layout(layout)
        else:
            layout = QVBoxLayout(self.trigger_options_container)
            self.trigger_options_container.setLayout(layout)
        layout.setContentsMargins(0, 10, 0, 0)

        # Reset any existing selector attributes
        for attr in [
            "on_off_tag_selector",
            "range_operand1_selector",
            "range_operand2_selector",
            "range_lower_bound_selector",
            "range_upper_bound_selector",
            "range_operator_combo",
            "range_rhs_stack",
        ]:
            if hasattr(self, attr):
                setattr(self, attr, None)

        if mode in ["On", "Off"]:
            self.on_off_tag_selector = TagSelector()
            self.on_off_tag_selector.set_allowed_tag_types(["BOOL"])
            self.on_off_tag_selector.main_tag_selector.set_mode_fixed("Tag")
            self.on_off_tag_selector.inputChanged.connect(self._validate_form)
            layout.addWidget(self.on_off_tag_selector)
        elif mode == "Range":
            self._build_range_trigger_options(layout)
        
        self._validate_form()

    def _build_range_trigger_options(self, parent_layout):

        range_group = QGroupBox("Range Configuration")
        range_group.setObjectName("CardGroup")
        layout = QGridLayout(range_group)
        layout.setSpacing(10)
        
        allowed_types = [
            DataTypeMapper.normalize_type(t) for t in ["INT", "DINT", "REAL"]
        ]
        
        op1_layout = QVBoxLayout()
        self.range_operand1_selector = TagSelector(allowed_tag_types=allowed_types)
        self.range_operand1_selector.main_tag_selector.set_mode_fixed("Tag")
        op1_layout.addWidget(QLabel("Operand 1"))
        op1_layout.addWidget(self.range_operand1_selector)
        op1_layout.addStretch(1)

        op_layout = QVBoxLayout()
        self.range_operator_combo = QComboBox()
        self.range_operator_combo.addItems(["==", "!=", ">", ">=", "<", "<=", "between", "outside"])
        op_layout.addWidget(QLabel("Operator"))
        op_layout.addWidget(self.range_operator_combo)
        op_layout.addStretch(1)
        
        self.range_rhs_stack = QStackedWidget()
        
        layout.addLayout(op1_layout, 0, 0)
        layout.addLayout(op_layout, 0, 1)
        layout.addWidget(self.range_rhs_stack, 0, 2, alignment=Qt.AlignmentFlag.AlignTop)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(2, 1)
        
        op2_page = QWidget()
        op2_page_layout = QVBoxLayout(op2_page)
        op2_page_layout.setContentsMargins(0,0,0,0)
        self.range_operand2_selector = TagSelector(allowed_tag_types=allowed_types)
        op2_page_layout.addWidget(QLabel("Operand 2"))
        op2_page_layout.addWidget(self.range_operand2_selector)
        op2_page_layout.addStretch(1)
        self.range_rhs_stack.addWidget(op2_page)
        
        between_page = QWidget()
        between_layout = QGridLayout(between_page)
        between_layout.setContentsMargins(0,0,0,0)
        self.range_lower_bound_selector = TagSelector(allowed_tag_types=allowed_types)
        self.range_upper_bound_selector = TagSelector(allowed_tag_types=allowed_types)
        between_layout.addWidget(QLabel("Lower Bound"), 0, 0)
        between_layout.addWidget(self.range_lower_bound_selector, 1, 0)
        between_layout.addWidget(QLabel("Upper Bound"), 0, 1)
        between_layout.addWidget(self.range_upper_bound_selector, 1, 1)
        between_layout.setRowStretch(2, 1)
        self.range_rhs_stack.addWidget(between_page)
        
        self.range_operand1_selector.inputChanged.connect(self._validate_form)
        self.range_operator_combo.currentTextChanged.connect(self._on_range_operator_changed)
        self.range_operand2_selector.inputChanged.connect(self._validate_form)
        self.range_lower_bound_selector.inputChanged.connect(self._validate_form)
        self.range_upper_bound_selector.inputChanged.connect(self._validate_form)
        
        self._on_range_operator_changed(self.range_operator_combo.currentText())
        parent_layout.addWidget(range_group)

    def _on_range_operator_changed(self, operator: str):
        if self.range_rhs_stack:
            self.range_rhs_stack.setCurrentIndex(1 if operator in ["between", "outside"] else 0)
        self._validate_form()

    def _load_data(self, data):
        self._set_tag_selector_data(self.target_tag_selector, data.get("target_tag"))
        
        trigger_data = data.get("trigger", {})
        trigger_mode = trigger_data.get("mode", "Ordinary")
        
        self.trigger_mode_combo.blockSignals(True)
        self.trigger_mode_combo.setCurrentText(trigger_mode)
        self.trigger_mode_combo.blockSignals(False)
        self._on_trigger_mode_changed(trigger_mode)

        if trigger_mode in ["On", "Off"] and self.on_off_tag_selector:
            self._set_tag_selector_data(self.on_off_tag_selector, trigger_data.get("tag"))
        elif trigger_mode == "Range" and self.range_operator_combo:
            self.range_operator_combo.setCurrentText(trigger_data.get("operator"))
            if self.range_operand1_selector:
                self._set_tag_selector_data(self.range_operand1_selector, trigger_data.get("operand1"))
            if trigger_data.get("operator") in ["between", "outside"]:
                if self.range_lower_bound_selector:
                    self._set_tag_selector_data(self.range_lower_bound_selector, trigger_data.get("lower_bound"))
                if self.range_upper_bound_selector:
                    self._set_tag_selector_data(self.range_upper_bound_selector, trigger_data.get("upper_bound"))
            else:
                if self.range_operand2_selector:
                    self._set_tag_selector_data(self.range_operand2_selector, trigger_data.get("operand2"))
        
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
        trigger_is_valid = True
        if trigger_mode in ["On", "Off"]:
            if not (self.on_off_tag_selector and self.on_off_tag_selector.get_data()):
                if error_msg is None:
                    error_msg = f"A tag must be selected for '{trigger_mode}' trigger."
                trigger_is_valid = False
        elif trigger_mode == "Range":
            if self.range_operand1_selector and self.range_operator_combo:
                trigger_is_valid, range_error = validate_range_section(
                    self.range_operand1_selector,
                    self.range_operator_combo.currentText(),
                    self.range_operand2_selector,
                    self.range_lower_bound_selector,
                    self.range_upper_bound_selector,
                )
                if not trigger_is_valid and error_msg is None:
                    error_msg = range_error

        is_valid &= trigger_is_valid
        if trigger_mode == "Ordinary":
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
            "action_type": "bit",
            "target_tag": target_tag_data,
            "mode": self.mode_group.checkedButton().text()
        }

        trigger_mode = self.trigger_mode_combo.currentText()
        if trigger_mode != "Ordinary":
            trigger_dict = {"mode": trigger_mode}
            if trigger_mode in ["On", "Off"]:
                trigger_dict["tag"] = self.on_off_tag_selector.get_data()
            elif trigger_mode == "Range":
                trigger_dict["operator"] = self.range_operator_combo.currentText()
                trigger_dict["operand1"] = self.range_operand1_selector.get_data()
                if trigger_dict["operator"] in ["between", "outside"]:
                    trigger_dict["lower_bound"] = self.range_lower_bound_selector.get_data()
                    trigger_dict["upper_bound"] = self.range_upper_bound_selector.get_data()
                else:
                    trigger_dict["operand2"] = self.range_operand2_selector.get_data()
            action_data["trigger"] = trigger_dict
        
        target_str = self._format_operand_for_display(target_tag_data)
        mode_str = action_data.get("mode", "N/A")
        if trigger_mode != "Ordinary":
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
