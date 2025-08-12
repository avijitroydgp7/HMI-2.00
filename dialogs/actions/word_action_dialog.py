# dialogs/actions/word_action_dialog.py
# A dialog for configuring advanced Word Actions with improved UX.

from PyQt6.QtWidgets import (
    QGroupBox, QGridLayout, QHBoxLayout, QVBoxLayout,
    QLabel, QComboBox, QDialogButtonBox, QCheckBox, QWidget,
    QStackedWidget, QFrame, QScrollArea
)
from PyQt6.QtCore import Qt
from typing import Dict, Optional

from ..base_dialog import CustomDialog
from ..custom_widgets import TagSelector, CollapsibleBox

class DataTypeMapper:
    """Centralized data type mapping to ensure consistency."""
    
    # Mapping from internal types to standardized types
    TYPE_MAPPING = {
        "INT": "INT16",
        "DINT": "INT32",
        "REAL": "REAL",
        "BOOL": "BOOL"
    }
    
    @classmethod
    def normalize_type(cls, data_type: str) -> str:
        """Convert internal data type to standardized type."""
        return cls.TYPE_MAPPING.get(data_type, data_type)
    
    @classmethod
    def are_types_compatible(cls, type1: str, type2: str) -> bool:
        """Check if two data types are compatible."""
        normalized_type1 = cls.normalize_type(type1)
        normalized_type2 = cls.normalize_type(type2)
        return normalized_type1 == normalized_type2

class WordActionDialog(CustomDialog):
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

        # Main layout from the base dialog
        content_layout = self.get_content_layout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Add a stylesheet for the card-like group boxes
        # self.setStyleSheet("""
        #     QScrollArea#ContentScrollArea, QWidget#ScrollContainer {
        #         background: transparent;
        #         border: none;
        #     }
        #     QGroupBox#CardGroup {
        #         background-color: #2F3640;
        #         border: 1px solid #454c5a;
        #         border-radius: 4px;
        #         margin-top: 6px;
        #     }
        #     QGroupBox#CardGroup::title {
        #         subcontrol-origin: margin;
        #         subcontrol-position: top left;
        #         padding: 0 5px;
        #     }
        # """)

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

        # --- Dialog Buttons ---
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        content_layout.addWidget(self.button_box)

        # --- Connect signals after all UI is built ---
        self._connect_signals()

        # --- Initialize dialog state ---
        self._initialize_dialog(action_data)

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
        self.target_tag_selector.set_allowed_tag_types(["INT16", "INT32", "REAL"])
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
        self.trigger_mode_combo.addItems(["Ordinary", "On", "Off", "Range"])
        trigger_main_layout.addWidget(self.trigger_mode_combo)
        
        self.trigger_options_container = QWidget()
        trigger_main_layout.addWidget(self.trigger_options_container)
        
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

    def _clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

    def _clear_widget_children(self, widget):
        """Helper to delete all child widgets of a given widget."""
        for child in widget.findChildren(QWidget):
            child.deleteLater()

    def _on_trigger_mode_changed(self, mode: str):
        # Hide container to prevent residual widget visibility
        self.trigger_options_container.setVisible(False)

        # Clear all child widgets explicitly
        self._clear_widget_children(self.trigger_options_container)

        layout = self.trigger_options_container.layout()
        if layout is not None:
            self._clear_layout(layout)
        else:
            layout = QVBoxLayout(self.trigger_options_container)
            self.trigger_options_container.setLayout(layout)
        layout.setContentsMargins(0, 10, 0, 0)

        # Remove any existing on_off_tag_selector widget to avoid duplicates
        if hasattr(self, 'on_off_tag_selector'):
            self.on_off_tag_selector.deleteLater()
            del self.on_off_tag_selector

        if mode in ["On", "Off"]:
            self.on_off_tag_selector = TagSelector()
            self.on_off_tag_selector.set_allowed_tag_types(["BOOL"])
            self.on_off_tag_selector.main_tag_selector.set_mode_fixed("Tag")
            self.on_off_tag_selector.inputChanged.connect(self._validate_form)
            layout.addWidget(self.on_off_tag_selector)
        elif mode == "Range":
            self._build_range_trigger_options(layout)

        # Show container after widgets are updated
        self.trigger_options_container.setVisible(True)
        
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
        
        op2_page = QWidget(); op2_page_layout = QVBoxLayout(op2_page); op2_page_layout.setContentsMargins(0,0,0,0)
        self.range_operand2_selector = TagSelector(allowed_tag_types=allowed_types)
        op2_page_layout.addWidget(QLabel("Operand 2")); op2_page_layout.addWidget(self.range_operand2_selector); op2_page_layout.addStretch(1)
        self.range_rhs_stack.addWidget(op2_page)
        
        between_page = QWidget(); between_layout = QGridLayout(between_page); between_layout.setContentsMargins(0,0,0,0)
        self.range_lower_bound_selector = TagSelector(allowed_tag_types=allowed_types)
        self.range_upper_bound_selector = TagSelector(allowed_tag_types=allowed_types)
        between_layout.addWidget(QLabel("Lower Bound"), 0, 0); between_layout.addWidget(self.range_lower_bound_selector, 1, 0)
        between_layout.addWidget(QLabel("Upper Bound"), 0, 1); between_layout.addWidget(self.range_upper_bound_selector, 1, 1)
        self.range_rhs_stack.addWidget(between_page)
        
        self.range_operand1_selector.inputChanged.connect(self._validate_form)
        self.range_operator_combo.currentTextChanged.connect(self._on_range_operator_changed)
        self.range_operand2_selector.inputChanged.connect(self._validate_form)
        self.range_lower_bound_selector.inputChanged.connect(self._validate_form)
        self.range_upper_bound_selector.inputChanged.connect(self._validate_form)
        
        self._on_range_operator_changed(self.range_operator_combo.currentText())
        parent_layout.addWidget(range_group)

    def _on_action_mode_changed(self, mode_text: str):
        label_map = {
            "Addition": "<b>Value to Add</b>", "Subtraction": "<b>Value to Subtract</b>",
            "Set Value": "<b>New Value</b>", "Multiplication": "<b>Value to Multiply By</b>",
            "Division": "<b>Value to Divide By</b>"
        }
        self.value_label.setText(label_map.get(mode_text, "<b>Value</b>"))
        self._validate_form()

    def _on_range_operator_changed(self, operator: str):
        if hasattr(self, 'range_rhs_stack'):
            self.range_rhs_stack.setCurrentIndex(1 if operator in ["between", "outside"] else 0)
        self._validate_form()

    def _on_conditional_operator_changed(self, operator: str):
        self.cond_rhs_stack.setCurrentIndex(1 if operator in ["between", "outside"] else 0)
        self._validate_form()

    def _on_tag_selected_in_child(self, tag_data: Optional[Dict]):
        sender = self.sender()
        if sender == self.target_tag_selector:
            self._on_target_tag_selected(tag_data)
        elif hasattr(self, 'range_operand1_selector') and sender == self.range_operand1_selector:
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
        allowed_types = ["INT16", "INT32", "REAL"]
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
        # Clear all existing errors
        self._clear_all_errors()
        
        # Validate each section
        main_action_valid = self._validate_main_action()
        trigger_valid = self._validate_trigger_section()
        conditional_valid = self._validate_conditional_section()
        
        # Update UI based on validation results
        self._update_validation_ui(trigger_valid, conditional_valid)
        
        # Enable/disable OK button
        overall_valid = main_action_valid and trigger_valid and conditional_valid
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button:
            ok_button.setEnabled(overall_valid)

    def _clear_all_errors(self):
        """Clear all error states from tag selectors."""
        for selector in self.findChildren(TagSelector):
            selector.clear_errors_recursive()

    def _validate_main_action(self) -> bool:
        """Validate the main action section."""
        is_valid = True
        
        if not self.target_tag_selector.get_data():
            self.target_tag_selector.setError("Target Tag must be selected.")
            is_valid = False
            
        if not self.value_selector.get_data():
            self.value_selector.setError("A value or tag must be provided.")
            is_valid = False
            
        return is_valid

    def _validate_trigger_section(self) -> bool:
        """Validate the trigger section."""
        trigger_mode = self.trigger_mode_combo.currentText()
        
        if trigger_mode == "Ordinary":
            return True
        elif trigger_mode in ["On", "Off"]:
            return self._validate_on_off_trigger()
        elif trigger_mode == "Range":
            return self._validate_range_trigger()
        
        return True

    def _validate_on_off_trigger(self) -> bool:
        """Validate On/Off trigger configuration."""
        if hasattr(self, 'on_off_tag_selector') and not self.on_off_tag_selector.get_data():
            trigger_mode = self.trigger_mode_combo.currentText()
            self.on_off_tag_selector.setError(f"A tag must be selected for '{trigger_mode}' trigger.")
            return False
        return True

    def _validate_range_trigger(self) -> bool:
        """Validate Range trigger configuration."""
        if not hasattr(self, 'range_operand1_selector'):
            return True
        
        return self._validate_range_section(
            self.range_operand1_selector,
            self.range_operator_combo.currentText(),
            self.range_operand2_selector,
            self.range_lower_bound_selector,
            self.range_upper_bound_selector,
            "Range Trigger"
        )

    def _validate_conditional_section(self) -> bool:
        """Validate the conditional reset section."""
        if not self.conditional_reset_group.isChecked():
            return True
        
        is_valid = True
        
        # Validate the conditional logic
        is_valid &= self._validate_range_section(
            self.operand1_selector,
            self.operator_combo.currentText(),
            self.cond_operand2_selector,
            self.cond_lower_bound_selector,
            self.cond_upper_bound_selector,
            "Conditional Reset"
        )
        
        # Validate reset value
        if not self.reset_selector.get_data():
            self.reset_selector.setError("Reset value must be specified.")
            is_valid = False
        
        # Validate else value if enabled
        if self.else_checkbox.isChecked() and not self.else_selector.get_data():
            self.else_selector.setError("Else value must be specified.")
            is_valid = False
        
        return is_valid

    def _update_validation_ui(self, trigger_valid: bool, conditional_valid: bool):
        """Update the UI status indicators based on validation results."""
        trigger_mode = self.trigger_mode_combo.currentText()
        
        if trigger_mode == "Ordinary":
            self.trigger_box.setStatus(CollapsibleBox.Status.NEUTRAL)
        else:
            self.trigger_box.setStatus(CollapsibleBox.Status.OK if trigger_valid else CollapsibleBox.Status.ERROR)
        
        if self.conditional_reset_group.isChecked():
            self.conditional_reset_group.setStatus(CollapsibleBox.Status.OK if conditional_valid else CollapsibleBox.Status.ERROR)
        else:
            self.conditional_reset_group.setStatus(CollapsibleBox.Status.NEUTRAL)

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
        
        # Validate data type compatibility using centralized mapper
        op1_type = op1_selector.current_tag_data.get('data_type') if op1_selector.current_tag_data else None
        if op1_type:
            op1_type = DataTypeMapper.normalize_type(op1_type)
            if operator in ["between", "outside"]:
                # Validate lower bound type compatibility
                lower_type = lower_selector.current_tag_data.get('data_type') if lower_selector.current_tag_data else None
                if lower_type:
                    if not DataTypeMapper.are_types_compatible(lower_type, op1_type):
                        lower_selector.setError("Data type must match Operand 1.")
                        is_valid = False
                
                # Validate upper bound type compatibility
                upper_type = upper_selector.current_tag_data.get('data_type') if upper_selector.current_tag_data else None
                if upper_type:
                    if not DataTypeMapper.are_types_compatible(upper_type, op1_type):
                        upper_selector.setError("Data type must match Operand 1.")
                        is_valid = False
            else:
                # Validate operand 2 type compatibility
                op2_type = op2_selector.current_tag_data.get('data_type') if op2_selector.current_tag_data else None
                if op2_type:
                    if not DataTypeMapper.are_types_compatible(op2_type, op1_type):
                        op2_selector.setError("Data type must match Operand 1.")
                        is_valid = False
        return is_valid

    # -------------------------------------------------------------------------
    # Data Load/Save
    # -------------------------------------------------------------------------

    def _set_tag_selector_data(self, selector: TagSelector, data: Optional[Dict]):
        if selector and data:
            selector.set_data(data)

    def _initialize_dialog(self, action_data: Optional[Dict]):
        """Simplified initialization logic that handles both new and existing data."""
        # Ensure clean state by clearing any existing dynamic widgets
        self._clear_dynamic_widgets()
        
        if action_data:
            # Load data into model controls
            self.action_mode_combo.setCurrentText(action_data.get("action_mode", "Addition"))
            self.trigger_mode_combo.setCurrentText(action_data.get("trigger", {}).get("mode", "Ordinary"))
            
            cond_data = action_data.get("conditional_reset")
            if cond_data:
                self.conditional_reset_group.setChecked(True)
                self.operator_combo.setCurrentText(cond_data.get("operator", "=="))
                if "else_value" in cond_data:
                    self.else_checkbox.setChecked(True)
            
            # Set expansion states
            self.trigger_box.setExpanded(bool(action_data.get("trigger")))
            self.conditional_reset_group.setExpanded(bool(cond_data))
        
        # Build dynamic UI based on current state
        self._on_action_mode_changed(self.action_mode_combo.currentText())
        self._on_trigger_mode_changed(self.trigger_mode_combo.currentText())
        self._on_conditional_operator_changed(self.operator_combo.currentText())
        
        # Populate widgets with data if editing
        if action_data:
            self._populate_widgets_with_data(action_data)
        
        # Run initial validation
        self._validate_form()

    def _clear_dynamic_widgets(self):
        """Clear any existing dynamic widgets to prevent background artifacts."""
        # Clear trigger options container
        if hasattr(self, 'trigger_options_container'):
            self._clear_layout(self.trigger_options_container.layout())
        
        # Reset conditional reset state
        self.conditional_reset_group.setChecked(False)
        self.else_checkbox.setChecked(False)
        
        # Hide conditional reset sections
        if hasattr(self, 'else_group'):
            self.else_group.setVisible(False)

    def _populate_widgets_with_data(self, data: Dict):
        """Populate widgets with loaded data after dynamic UI is built."""
        # Main action data
        self._set_tag_selector_data(self.target_tag_selector, data.get("target_tag"))
        self._set_tag_selector_data(self.value_selector, data.get("value"))

        # Trigger data
        trigger_data = data.get("trigger", {})
        trigger_mode = trigger_data.get("mode")
        if trigger_mode in ["On", "Off"] and hasattr(self, 'on_off_tag_selector'):
            self._set_tag_selector_data(self.on_off_tag_selector, trigger_data.get("tag"))
        elif trigger_mode == "Range" and hasattr(self, 'range_operator_combo'):
            self.range_operator_combo.setCurrentText(trigger_data.get("operator", "=="))
            self._on_range_operator_changed(self.range_operator_combo.currentText())
            self._set_tag_selector_data(self.range_operand1_selector, trigger_data.get("operand1"))
            if trigger_data.get("operator") in ["between", "outside"]:
                self._set_tag_selector_data(self.range_lower_bound_selector, trigger_data.get("lower_bound"))
                self._set_tag_selector_data(self.range_upper_bound_selector, trigger_data.get("upper_bound"))
            else:
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
            "action_type": "word",
            "target_tag": self.target_tag_selector.get_data(),
            "action_mode": self.action_mode_combo.currentText(),
            "value": self.value_selector.get_data(),
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
