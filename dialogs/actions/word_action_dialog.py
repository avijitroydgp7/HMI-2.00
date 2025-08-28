# dialogs/actions/word_action_dialog.py
# A dialog for configuring advanced Word Actions with improved UX.

from PyQt6.QtWidgets import (
    QGroupBox, QGridLayout, QHBoxLayout, QVBoxLayout,
    QLabel, QComboBox, QDialogButtonBox, QCheckBox, QWidget,
    QStackedWidget, QScrollArea, QDialog
)
from PyQt6.QtCore import Qt
from typing import Dict, Optional

from ..widgets import TagSelector, CollapsibleBox
from .range_helpers import DataTypeMapper, validate_range_section
from .constants import ActionType, TriggerMode

class WordActionDialog(QDialog):
    """
    A redesigned dialog for configuring a 'Word Action' with a focus on
    progressive disclosure, inline validation, and clearer visual hierarchy.
    Now uses a fixed-height, scrollable layout.
    """
    def __init__(self, parent=None, action_data: Optional[Dict] = None):
        super().__init__(parent)
        self.setWindowTitle("Word Action Configuration")
        self.setMinimumWidth(800)
        self.setFixedHeight(750)
        # Remove borderless styling so combo boxes use the standard dropdown
        # appearance consistent with the Conditional Style window

        # Main layout for the dialog
        content_layout = QVBoxLayout(self)
        content_layout.setContentsMargins(0, 0, 0, 0)

        # Create a scroll area for the main configuration
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setObjectName("ContentScrollArea")
        
        scroll_content_widget = QWidget()
        scroll_content_widget.setObjectName("ScrollContainer")
        scroll_area.setWidget(scroll_content_widget)

        # This layout will hold all the collapsible sections
        scrollable_layout = QVBoxLayout(scroll_content_widget)
        scrollable_layout.setSpacing(10)
        scrollable_layout.setContentsMargins(15, 15, 15, 15)

        # --- Build UI sections and add them to the scrollable layout ---
        self._build_main_action_ui(scrollable_layout)
        self._build_trigger_ui(scrollable_layout)
        self._build_conditional_reset_ui(scrollable_layout)
        
        scrollable_layout.addStretch(1)

        # Add the scroll area to the main dialog layout
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

        # --- Connect signals after all UI is built ---
        self._connect_signals()

        # --- Initialize dialog state ---
        self._initialize_dialog(action_data)
        
        # Ensure dynamic trigger widgets exist as attributes
        # so signal handlers can safely reference them before creation.
        if not hasattr(self, 'on_off_tag_selector'): self.on_off_tag_selector = None
        if not hasattr(self, 'range_operand1_selector'): self.range_operand1_selector = None
        if not hasattr(self, 'range_operand2_selector'): self.range_operand2_selector = None
        if not hasattr(self, 'range_lower_bound_selector'): self.range_lower_bound_selector = None
        if not hasattr(self, 'range_upper_bound_selector'): self.range_upper_bound_selector = None
        if not hasattr(self, 'range_operator_combo'): self.range_operator_combo = None
        if not hasattr(self, 'range_rhs_stack'): self.range_rhs_stack = None

    # -------------------------------------------------------------------------
    # UI Building Methods
    # -------------------------------------------------------------------------

    def _build_main_action_ui(self, parent_layout):
        main_action_group = QGroupBox("Main Action")
        main_action_group.setObjectName("CardGroup")
        main_action_layout = QGridLayout(main_action_group)
        main_action_layout.setSpacing(10)
        
        target_layout = QVBoxLayout()
        mode_layout = QVBoxLayout()
        value_layout = QVBoxLayout()

        self.target_tag_selector = TagSelector()
        self.target_tag_selector.main_tag_selector.set_mode_fixed("Tag")
        self.target_tag_selector.set_allowed_tag_types(
            [DataTypeMapper.normalize_type(t) for t in ["INT", "DINT", "REAL"]]
        )
        target_layout.addWidget(QLabel("<b>Target Tag</b>"))
        target_layout.addWidget(self.target_tag_selector)
        target_layout.addStretch(1)
        
        self.action_mode_combo = QComboBox()
        self.action_mode_combo.addItems(["Addition", "Subtraction", "Set Value", "Multiplication", "Division"])
        mode_layout.addWidget(QLabel("<b>Action Mode</b>"))
        mode_layout.addWidget(self.action_mode_combo)
        mode_layout.addStretch(1)
        
        self.value_label = QLabel("<b>Value</b>")
        self.value_selector = TagSelector()
        value_layout.addWidget(self.value_label)
        value_layout.addWidget(self.value_selector)
        value_layout.addStretch(1)
        
        main_action_layout.addLayout(target_layout, 0, 0)
        main_action_layout.addLayout(mode_layout, 0, 1)
        main_action_layout.addLayout(value_layout, 0, 2)
        
        main_action_layout.setColumnStretch(0, 1)
        main_action_layout.setColumnStretch(2, 1)
        parent_layout.addWidget(main_action_group)

    def _build_trigger_ui(self, parent_layout):
        self.trigger_box = CollapsibleBox("Trigger")

        trigger_content_widget = QWidget()
        trigger_main_layout = QVBoxLayout(trigger_content_widget)
        trigger_main_layout.setContentsMargins(5, 10, 5, 5)

        self.trigger_mode_combo = QComboBox()
        self.trigger_mode_combo.addItems(TriggerMode.values())
        trigger_main_layout.addWidget(self.trigger_mode_combo)

        # Use a stacked widget to avoid creating/destroying child widgets
        self.trigger_stack = QStackedWidget()

        # 1) ORDINARY: empty page
        self.trigger_empty_page = QWidget()
        self.trigger_stack.addWidget(self.trigger_empty_page)

        # 2) ON/OFF: single TagSelector page
        self.trigger_onoff_page = QWidget()
        onoff_layout = QVBoxLayout(self.trigger_onoff_page)
        onoff_layout.setContentsMargins(0, 10, 0, 0)
        self.on_off_tag_selector = TagSelector()
        self.on_off_tag_selector.set_allowed_tag_types(["BOOL"])
        self.on_off_tag_selector.main_tag_selector.set_mode_fixed("Tag")
        onoff_layout.addWidget(self.on_off_tag_selector)
        onoff_layout.addStretch(1)
        self.trigger_stack.addWidget(self.trigger_onoff_page)

        # 3) RANGE: full range config page
        self.trigger_range_page = self._create_range_trigger_page()
        self.trigger_stack.addWidget(self.trigger_range_page)

        trigger_main_layout.addWidget(self.trigger_stack)

        self.trigger_box.setContent(trigger_content_widget)
        parent_layout.addWidget(self.trigger_box)

    def _build_conditional_reset_ui(self, parent_layout):
        self.conditional_reset_group = CollapsibleBox("Conditional Reset")
        self.conditional_reset_group.setCheckable(True)
        
        conditional_reset_content = QWidget()
        layout = QVBoxLayout(conditional_reset_content)
        layout.setSpacing(10)
        layout.setContentsMargins(5, 10, 5, 5)
        
        if_group = QGroupBox("If")
        if_group.setObjectName("CardGroup")
        if_layout = QGridLayout(if_group)
        
        op1_layout = QVBoxLayout()
        self.operand1_selector = TagSelector()
        self.operand1_selector.main_tag_selector.set_mode_fixed("Tag")
        op1_layout.addWidget(QLabel("Operand 1"))
        op1_layout.addWidget(self.operand1_selector)
        op1_layout.addStretch(1)

        op_layout = QVBoxLayout()
        self.operator_combo = QComboBox()
        self.operator_combo.addItems(["==", "!=", ">", ">=", "<", "<=", "between", "outside"])
        op_layout.addWidget(QLabel("Operator"))
        op_layout.addWidget(self.operator_combo)
        op_layout.addStretch(1)

        self.cond_rhs_stack = QStackedWidget()
        
        if_layout.addLayout(op1_layout, 0, 0)
        if_layout.addLayout(op_layout, 0, 1)
        if_layout.addWidget(self.cond_rhs_stack, 0, 2)
        if_layout.setColumnStretch(0, 1)
        if_layout.setColumnStretch(2, 1)
        
        op2_page = QWidget(); op2_page_layout = QVBoxLayout(op2_page); op2_page_layout.setContentsMargins(0,0,0,0)
        self.cond_operand2_selector = TagSelector(); op2_page_layout.addWidget(QLabel("Operand 2")); op2_page_layout.addWidget(self.cond_operand2_selector); op2_page_layout.addStretch(1)
        self.cond_rhs_stack.addWidget(op2_page)
        
        between_page = QWidget(); between_layout = QGridLayout(between_page); between_layout.setContentsMargins(0,0,0,0)
        self.cond_lower_bound_selector = TagSelector(); between_layout.addWidget(QLabel("Lower Bound"), 0, 0); between_layout.addWidget(self.cond_lower_bound_selector, 1, 0)
        self.cond_upper_bound_selector = TagSelector(); between_layout.addWidget(QLabel("Upper Bound"), 0, 1); between_layout.addWidget(self.cond_upper_bound_selector, 1, 1)
        self.cond_rhs_stack.addWidget(between_page)
        layout.addWidget(if_group)
        
        then_group = QGroupBox("Then")
        then_group.setObjectName("CardGroup")
        then_layout = QVBoxLayout(then_group)
        self.reset_selector = TagSelector()
        then_layout.addWidget(QLabel("Reset Target to Value:"))
        then_layout.addWidget(self.reset_selector)
        then_layout.addStretch(1)
        layout.addWidget(then_group)
        
        self.else_checkbox = QCheckBox("Add Else Condition")
        layout.addWidget(self.else_checkbox)

        self.else_group = QGroupBox("Else")
        self.else_group.setObjectName("CardGroup")
        self.else_group.setVisible(False)
        else_layout = QVBoxLayout(self.else_group)
        self.else_selector = TagSelector()
        else_layout.addWidget(QLabel("Reset Target to Value:"))
        else_layout.addWidget(self.else_selector)
        else_layout.addStretch(1)
        layout.addWidget(self.else_group)
        
        self.conditional_reset_group.setContent(conditional_reset_content)
        parent_layout.addWidget(self.conditional_reset_group)

    # -------------------------------------------------------------------------
    # Signal Connections & Event Handlers
    # -------------------------------------------------------------------------

    def _connect_signals(self):
        all_selectors = self.findChildren(TagSelector)
        for selector in all_selectors:
            selector.inputChanged.connect(self._validate_form)
            selector.tag_selected.connect(self._on_tag_selected_in_child)

        self.action_mode_combo.currentTextChanged.connect(self._on_action_mode_changed)
        self.trigger_mode_combo.currentTextChanged.connect(self._on_trigger_mode_changed)
        self.operator_combo.currentTextChanged.connect(self._on_conditional_operator_changed)
        self.conditional_reset_group.toggled.connect(self._validate_form)
        self.else_checkbox.toggled.connect(self.else_group.setVisible)
        self.else_checkbox.toggled.connect(self._validate_form)

    # Note: Widget clearing helpers removed in favor of stacked pages.

    def _on_trigger_mode_changed(self, mode: str):
        # Switch pre-built pages without destroying widgets
        if mode == TriggerMode.ORDINARY.value:
            self.trigger_stack.setCurrentWidget(self.trigger_empty_page)
        elif mode in [TriggerMode.ON.value, TriggerMode.OFF.value]:
            self.trigger_stack.setCurrentWidget(self.trigger_onoff_page)
        elif mode == TriggerMode.RANGE.value:
            self.trigger_stack.setCurrentWidget(self.trigger_range_page)
        else:
            self.trigger_stack.setCurrentWidget(self.trigger_empty_page)
        self._validate_form()

    def _create_range_trigger_page(self) -> QWidget:
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

        op2_page = QWidget(); op2_page_layout = QVBoxLayout(op2_page); op2_page_layout.setContentsMargins(0,0,0,0)
        self.range_operand2_selector = TagSelector(allowed_tag_types=allowed_types)
        op2_page_layout.addWidget(QLabel("Operand 2")); op2_page_layout.addWidget(self.range_operand2_selector); op2_page_layout.addStretch(1)
        self.range_rhs_stack.addWidget(op2_page)

        between_page = QWidget(); between_layout = QGridLayout(between_page); between_layout.setContentsMargins(0,0,0,0)
        self.range_lower_bound_selector = TagSelector(allowed_tag_types=allowed_types)
        self.range_upper_bound_selector = TagSelector(allowed_tag_types=allowed_types)
        between_layout.addWidget(QLabel("Lower Bound"), 0, 0); between_layout.addWidget(self.range_lower_bound_selector, 1, 0)
        between_layout.addWidget(QLabel("Upper Bound"), 0, 1); between_layout.addWidget(self.range_upper_bound_selector, 1, 1)
        between_layout.setRowStretch(2, 1)
        self.range_rhs_stack.addWidget(between_page)

        # Connect validation and operator switching once
        self.range_operand1_selector.inputChanged.connect(self._validate_form)
        self.range_operator_combo.currentTextChanged.connect(self._on_range_operator_changed)
        self.range_operand2_selector.inputChanged.connect(self._validate_form)
        self.range_lower_bound_selector.inputChanged.connect(self._validate_form)
        self.range_upper_bound_selector.inputChanged.connect(self._validate_form)

        # Initialize RHS page without triggering validation during build
        op = self.range_operator_combo.currentText()
        self.range_rhs_stack.setCurrentIndex(1 if op in ["between", "outside"] else 0)
        return range_group

    def _on_action_mode_changed(self, mode_text: str):
        label_map = {
            "Addition": "<b>Value to Add</b>", "Subtraction": "<b>Value to Subtract</b>",
            "Set Value": "<b>New Value</b>", "Multiplication": "<b>Value to Multiply By</b>",
            "Division": "<b>Value to Divide By</b>"
        }
        self.value_label.setText(label_map.get(mode_text, "<b>Value</b>"))
        self._validate_form()

    def _on_range_operator_changed(self, operator: str):
        if self.range_rhs_stack:
            self.range_rhs_stack.setCurrentIndex(1 if operator in ["between", "outside"] else 0)
        self._validate_form()

    def _on_conditional_operator_changed(self, operator: str):
        self.cond_rhs_stack.setCurrentIndex(1 if operator in ["between", "outside"] else 0)
        self._validate_form()

    def _on_tag_selected_in_child(self, tag_data: Optional[Dict]):
        sender = self.sender()
        if sender == self.target_tag_selector:
            self._on_target_tag_selected(tag_data)
        elif getattr(self, 'range_operand1_selector', None) is not None and sender == self.range_operand1_selector:
            self._on_range_operand1_selected(tag_data)
        self._validate_form()

    def _on_target_tag_selected(self, tag_data: Optional[Dict]):
        allowed_types = self.target_tag_selector.allowed_tag_types
        if tag_data and tag_data.get('data_type'):
            normalized_type = DataTypeMapper.normalize_type(tag_data.get('data_type'))
            allowed_types = [normalized_type]
        
        self.value_selector.set_allowed_tag_types(allowed_types)
        self.operand1_selector.set_allowed_tag_types(allowed_types)
        self.cond_operand2_selector.set_allowed_tag_types(allowed_types)
        self.cond_lower_bound_selector.set_allowed_tag_types(allowed_types)
        self.cond_upper_bound_selector.set_allowed_tag_types(allowed_types)
        self.reset_selector.set_allowed_tag_types(allowed_types)
        self.else_selector.set_allowed_tag_types(allowed_types)

    def _on_range_operand1_selected(self, tag_data: Optional[Dict]):
        allowed_types = [
            DataTypeMapper.normalize_type(t) for t in ["INT", "DINT", "REAL"]
        ]
        if tag_data and tag_data.get('data_type'):
            normalized_type = DataTypeMapper.normalize_type(tag_data.get('data_type'))
            allowed_types = [normalized_type]
        
        self.range_operand2_selector.set_allowed_tag_types(allowed_types)
        self.range_lower_bound_selector.set_allowed_tag_types(allowed_types)
        self.range_upper_bound_selector.set_allowed_tag_types(allowed_types)

    # -------------------------------------------------------------------------
    # Validation Logic
    # -------------------------------------------------------------------------

    def _validate_form(self, *args):
        """Main validation method that coordinates all validation checks."""

        error_msg = None

        main_action_valid, main_error = self._validate_main_action()
        if error_msg is None and main_error:
            error_msg = main_error

        trigger_valid, trigger_error = self._validate_trigger_section()
        if error_msg is None and trigger_error:
            error_msg = trigger_error

        conditional_valid, conditional_error = self._validate_conditional_section()
        if error_msg is None and conditional_error:
            error_msg = conditional_error

        # Update UI based on validation results
        self._update_validation_ui(trigger_valid, conditional_valid)

        # Enable/disable OK button
        overall_valid = main_action_valid and trigger_valid and conditional_valid
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button:
            ok_button.setEnabled(overall_valid)

        self.error_label.setText(error_msg or "")

    def _validate_main_action(self):
        """Validate the main action section."""
        if not self.target_tag_selector.get_data():
            return False, "Target Tag must be selected."

        if not self.value_selector.get_data():
            return False, "A value or tag must be provided."

        # Validate data type compatibility between target and value
        target_type = None
        if self.target_tag_selector.current_tag_data:
            target_type = self.target_tag_selector.current_tag_data.get('data_type')
            if target_type:
                target_type = DataTypeMapper.normalize_type(target_type)

        value_type = None
        if self.value_selector.current_tag_data:
            value_type = self.value_selector.current_tag_data.get('data_type')
            if value_type:
                value_type = DataTypeMapper.normalize_type(value_type)

        if target_type and value_type:
            if not DataTypeMapper.are_types_compatible(target_type, value_type):
                return False, "Data type must match Target Tag."

        return True, None

    def _validate_trigger_section(self):
        """Validate the trigger section."""
        trigger_mode = self.trigger_mode_combo.currentText()

        if trigger_mode == TriggerMode.ORDINARY.value:
            return True, None
        elif trigger_mode in [TriggerMode.ON.value, TriggerMode.OFF.value]:
            return self._validate_on_off_trigger()
        elif trigger_mode == TriggerMode.RANGE.value:
            return self._validate_range_trigger()

        return True, None

    def _validate_on_off_trigger(self):
        """Validate On/Off trigger configuration."""
        if not (self.on_off_tag_selector and self.on_off_tag_selector.get_data()):
            trigger_mode = self.trigger_mode_combo.currentText()
            return False, f"A tag must be selected for '{trigger_mode}' trigger."
        return True, None

    def _validate_range_trigger(self):
        """Validate Range trigger configuration."""
        if not (self.range_operand1_selector and self.range_operator_combo):
            return True, None

        return validate_range_section(
            self.range_operand1_selector,
            self.range_operator_combo.currentText(),
            self.range_operand2_selector,
            self.range_lower_bound_selector,
            self.range_upper_bound_selector,
            "Range Trigger",
        )

    def _validate_conditional_section(self):
        """Validate the conditional reset section."""
        # During early build, the conditional section may not exist yet.
        if not hasattr(self, 'conditional_reset_group') or not self.conditional_reset_group:
            return True, None
        if not self.conditional_reset_group.isChecked():
            return True, None

        valid, error = validate_range_section(
            self.operand1_selector,
            self.operator_combo.currentText(),
            self.cond_operand2_selector,
            self.cond_lower_bound_selector,
            self.cond_upper_bound_selector,
            "Conditional Reset",
        )
        if not valid:
            return False, error

        if not self.reset_selector.get_data():
            return False, "Reset value must be specified."

        if self.else_checkbox.isChecked() and not self.else_selector.get_data():
            return False, "Else value must be specified."

        return True, None

    def _update_validation_ui(self, trigger_valid: bool, conditional_valid: bool):
        """Update the UI status indicators based on validation results."""
        trigger_mode = self.trigger_mode_combo.currentText()
        
        if trigger_mode == TriggerMode.ORDINARY.value:
            self.trigger_box.setStatus(CollapsibleBox.Status.NEUTRAL)
        else:
            self.trigger_box.setStatus(CollapsibleBox.Status.OK if trigger_valid else CollapsibleBox.Status.ERROR)
        
        # Guard: conditional section may not exist during early build
        if hasattr(self, 'conditional_reset_group') and self.conditional_reset_group:
            if self.conditional_reset_group.isChecked():
                self.conditional_reset_group.setStatus(CollapsibleBox.Status.OK if conditional_valid else CollapsibleBox.Status.ERROR)
            else:
                self.conditional_reset_group.setStatus(CollapsibleBox.Status.NEUTRAL)


    # -------------------------------------------------------------------------
    # Data Load/Save
    # -------------------------------------------------------------------------

    def _set_tag_selector_data(self, selector: TagSelector, data: Optional[Dict]):
        if selector and data:
            selector.set_data(data)

    def _initialize_dialog(self, action_data: Optional[Dict]):
        """Initialize dialog state without destroying UI widgets."""
        # Default states
        self.conditional_reset_group.setChecked(False)
        self.else_checkbox.setChecked(False)
        self.else_group.setVisible(False)

        # Load provided data
        if action_data:
            self.action_mode_combo.setCurrentText(action_data.get("action_mode", "Addition"))
            self.trigger_mode_combo.setCurrentText(action_data.get("trigger", {}).get("mode", TriggerMode.ORDINARY.value))

            cond_data = action_data.get("conditional_reset")
            if cond_data:
                self.conditional_reset_group.setChecked(True)
                self.operator_combo.setCurrentText(cond_data.get("operator", "=="))
                if "else_value" in cond_data:
                    self.else_checkbox.setChecked(True)

            # Set expansion states
            self.trigger_box.setExpanded(bool(action_data.get("trigger")))
            self.conditional_reset_group.setExpanded(bool(cond_data))

        # Apply current selections to stacked widgets
        self._on_action_mode_changed(self.action_mode_combo.currentText())
        self._on_trigger_mode_changed(self.trigger_mode_combo.currentText())
        self._on_conditional_operator_changed(self.operator_combo.currentText())

        # Populate widgets with data if editing
        if action_data:
            self._populate_widgets_with_data(action_data)

        # Run initial validation
        self._validate_form()

    def _populate_widgets_with_data(self, data: Dict):
        """Populate widgets with loaded data after dynamic UI is built."""
        # Main action data
        self._set_tag_selector_data(self.target_tag_selector, data.get("target_tag"))
        self._set_tag_selector_data(self.value_selector, data.get("value"))

        # Trigger data
        trigger_data = data.get("trigger", {})
        trigger_mode = trigger_data.get("mode")
        if trigger_mode in [TriggerMode.ON.value, TriggerMode.OFF.value] and self.on_off_tag_selector:
            self._set_tag_selector_data(self.on_off_tag_selector, trigger_data.get("tag"))
        elif trigger_mode == TriggerMode.RANGE.value and self.range_operator_combo:
            self.range_operator_combo.setCurrentText(trigger_data.get("operator", "=="))
            self._on_range_operator_changed(self.range_operator_combo.currentText())
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
        
        # Conditional reset data
        cond_data = data.get("conditional_reset")
        if cond_data:
            self._set_tag_selector_data(self.operand1_selector, cond_data.get("operand1"))
            if cond_data.get("operator") in ["between", "outside"]:
                self._set_tag_selector_data(self.cond_lower_bound_selector, cond_data.get("lower_bound"))
                self._set_tag_selector_data(self.cond_upper_bound_selector, cond_data.get("upper_bound"))
            else:
                self._set_tag_selector_data(self.cond_operand2_selector, cond_data.get("operand2"))
            self._set_tag_selector_data(self.reset_selector, cond_data.get("reset_value"))
            if "else_value" in cond_data:
                self._set_tag_selector_data(self.else_selector, cond_data.get("else_value"))

    def get_data(self) -> Optional[Dict]:
        self._validate_form()
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if not ok_button or not ok_button.isEnabled():
            return None

        action_data = {
            "action_type": ActionType.WORD.value,
            "target_tag": self.target_tag_selector.get_data(),
            "action_mode": self.action_mode_combo.currentText(),
            "value": self.value_selector.get_data(),
        }

        trigger_mode = self.trigger_mode_combo.currentText()
        if trigger_mode != TriggerMode.ORDINARY.value:
            trigger_dict = {"mode": trigger_mode}
            if trigger_mode in [TriggerMode.ON.value, TriggerMode.OFF.value] and self.on_off_tag_selector:
                trigger_dict["tag"] = self.on_off_tag_selector.get_data()
            elif trigger_mode == TriggerMode.RANGE.value and self.range_operator_combo and self.range_operand1_selector:
                trigger_dict["operator"] = self.range_operator_combo.currentText()
                trigger_dict["operand1"] = self.range_operand1_selector.get_data()
                if trigger_dict["operator"] in ["between", "outside"]:
                    if self.range_lower_bound_selector:
                        trigger_dict["lower_bound"] = self.range_lower_bound_selector.get_data()
                    if self.range_upper_bound_selector:
                        trigger_dict["upper_bound"] = self.range_upper_bound_selector.get_data()
                else:
                    if self.range_operand2_selector:
                        trigger_dict["operand2"] = self.range_operand2_selector.get_data()
            action_data["trigger"] = trigger_dict

        if self.conditional_reset_group.isChecked():
            cond_dict = {
                "operator": self.operator_combo.currentText(),
                "operand1": self.operand1_selector.get_data(),
                "reset_value": self.reset_selector.get_data()
            }
            if cond_dict["operator"] in ["between", "outside"]:
                cond_dict["lower_bound"] = self.cond_lower_bound_selector.get_data()
                cond_dict["upper_bound"] = self.cond_upper_bound_selector.get_data()
            else:
                cond_dict["operand2"] = self.cond_operand2_selector.get_data()
            
            if self.else_checkbox.isChecked():
                cond_dict["else_value"] = self.else_selector.get_data()
            action_data["conditional_reset"] = cond_dict
        
        target_str = self._format_operand_for_display(action_data["target_tag"])
        value_str = self._format_operand_for_display(action_data["value"])
        mode = action_data["action_mode"]
        details_map = {
            "Addition": f"{target_str} += {value_str}", "Subtraction": f"{target_str} -= {value_str}",
            "Set Value": f"{target_str} = {value_str}", "Multiplication": f"{target_str} *= {value_str}",
            "Division": f"{target_str} /= {value_str}"
        }
        action_data["details"] = details_map.get(mode, "Invalid Action")
        
        return action_data

    def _format_operand_for_display(self, data: Optional[Dict]) -> str:
        if not data: return "?"
        main_tag = data.get("main_tag")
        if not main_tag: return "?"
        
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
