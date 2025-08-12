# dialogs/actions/bit_action_dialog.py
# Configuration dialog for Bit Actions.

from PyQt6.QtWidgets import (
    QFormLayout, QDialogButtonBox, QButtonGroup, QRadioButton, QWidget, 
    QVBoxLayout, QGroupBox, QGridLayout, QLabel, QComboBox, QStackedWidget,
    QScrollArea, QHBoxLayout
)
from typing import Dict, Optional

from ..tag_browser_dialog import TagBrowserDialog
from services.tag_data_service import tag_data_service
from ..base_dialog import CustomDialog
from ..custom_widgets import TagLineEdit, TagSelector, CollapsibleBox

class BitActionDialog(CustomDialog):
    """
    A dialog to configure a Bit Action for a button, with a custom title bar
    and an advanced trigger section.
    """
    def __init__(self, parent=None, action_data: Optional[Dict] = None):
        super().__init__(parent)
        self.setWindowTitle("Bit Action Configuration")
        self.setMinimumWidth(600)
        self.setFixedHeight(650)

        content_layout = self.get_content_layout()
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

        # --- Dialog Buttons ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        content_layout.addWidget(self.button_box)

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
        
        allowed_types = ["INT16", "INT32", "REAL"]
        
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
        layout.addWidget(self.range_rhs_stack, 0, 2)
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
        self.range_rhs_stack.addWidget(between_page)
        
        self.range_operand1_selector.inputChanged.connect(self._validate_form)
        self.range_operator_combo.currentTextChanged.connect(self._on_range_operator_changed)
        self.range_operand2_selector.inputChanged.connect(self._validate_form)
        self.range_lower_bound_selector.inputChanged.connect(self._validate_form)
        self.range_upper_bound_selector.inputChanged.connect(self._validate_form)
        
        self._on_range_operator_changed(self.range_operator_combo.currentText())
        parent_layout.addWidget(range_group)

    def _on_range_operator_changed(self, operator: str):
        if hasattr(self, 'range_rhs_stack'):
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

        if trigger_mode in ["On", "Off"]:
            self._set_tag_selector_data(self.on_off_tag_selector, trigger_data.get("tag"))
        elif trigger_mode == "Range":
            if hasattr(self, 'range_operator_combo'):
                self.range_operator_combo.setCurrentText(trigger_data.get("operator"))
                self._set_tag_selector_data(self.range_operand1_selector, trigger_data.get("operand1"))
                if trigger_data.get("operator") in ["between", "outside"]:
                    self._set_tag_selector_data(self.range_lower_bound_selector, trigger_data.get("lower_bound"))
                    self._set_tag_selector_data(self.range_upper_bound_selector, trigger_data.get("upper_bound"))
                else:
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
        is_valid = True
        
        self.target_tag_selector.clear_errors_recursive()
        if hasattr(self, 'on_off_tag_selector'):
            self.on_off_tag_selector.clear_errors_recursive()
        if hasattr(self, 'range_operand1_selector'):
            self.range_operand1_selector.clear_errors_recursive()
            self.range_operand2_selector.clear_errors_recursive()
            self.range_lower_bound_selector.clear_errors_recursive()
            self.range_upper_bound_selector.clear_errors_recursive()

        if not self.target_tag_selector.get_data():
            self.target_tag_selector.setError("Target Tag must be selected.")
            is_valid = False

        trigger_mode = self.trigger_mode_combo.currentText()
        trigger_is_valid = True
        if trigger_mode in ["On", "Off"]:
            if hasattr(self, 'on_off_tag_selector') and not self.on_off_tag_selector.get_data():
                self.on_off_tag_selector.setError(f"A tag must be selected for '{trigger_mode}' trigger.")
                trigger_is_valid = False
        elif trigger_mode == "Range":
            if hasattr(self, 'range_operand1_selector'):
                trigger_is_valid &= self._validate_range_section(self.range_operand1_selector, self.range_operator_combo.currentText(), self.range_operand2_selector, self.range_lower_bound_selector, self.range_upper_bound_selector)
        
        is_valid &= trigger_is_valid
        if trigger_mode == "Ordinary":
            self.trigger_box.setStatus(CollapsibleBox.Status.NEUTRAL)
        else:
            self.trigger_box.setStatus(CollapsibleBox.Status.OK if trigger_is_valid else CollapsibleBox.Status.ERROR)
        
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button:
            ok_button.setEnabled(is_valid)

    def _validate_range_section(self, op1_selector, operator, op2_selector, lower_selector, upper_selector, prefix="Range Trigger"):
        is_valid = True
        if not op1_selector.get_data():
            op1_selector.setError(f"{prefix}: Operand 1 must be specified.")
            is_valid = False
        
        if operator in ["between", "outside"]:
            if not lower_selector.get_data():
                lower_selector.setError(f"{prefix}: Lower Bound must be specified.")
                is_valid = False
            if not upper_selector.get_data():
                upper_selector.setError(f"{prefix}: Upper Bound must be specified.")
                is_valid = False
        else:
            if not op2_selector.get_data():
                op2_selector.setError(f"{prefix}: Operand 2 must be specified.")
                is_valid = False
        
        op1_type = op1_selector.current_tag_data.get('data_type') if op1_selector.current_tag_data else None
        if op1_type:
            op1_type = {"INT": "INT16", "DINT": "INT32"}.get(op1_type, op1_type)
            if operator in ["between", "outside"]:
                lower_type = lower_selector.current_tag_data.get('data_type') if lower_selector.current_tag_data else None
                if lower_type:
                    lower_type = {"INT": "INT16", "DINT": "INT32"}.get(lower_type, lower_type)
                    if lower_type != op1_type:
                        lower_selector.setError("Data type must match Operand 1.")
                        is_valid = False
                upper_type = upper_selector.current_tag_data.get('data_type') if upper_selector.current_tag_data else None
                if upper_type:
                    upper_type = {"INT": "INT16", "DINT": "INT32"}.get(upper_type, upper_type)
                    if upper_type != op1_type:
                        upper_selector.setError("Data type must match Operand 1.")
                        is_valid = False
            else:
                op2_type = op2_selector.current_tag_data.get('data_type') if op2_selector.current_tag_data else None
                if op2_type:
                    op2_type = {"INT": "INT16", "DINT": "INT32"}.get(op2_type, op1_type)
                    if op2_type != op1_type:
                        op2_selector.setError("Data type must match Operand 1.")
                        is_valid = False
        return is_valid

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
