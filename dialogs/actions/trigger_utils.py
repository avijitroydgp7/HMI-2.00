"""Shared utilities for building and validating trigger UI sections.

This module centralizes the construction of the Trigger section used by
BitActionDialog and WordActionDialog, and provides helpers to validate,
get, and set trigger data. It exposes callbacks so each dialog can hook
into tag selection and validation as needed.
"""

from typing import Optional, Dict, Tuple, List

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QComboBox, QStackedWidget, QLabel,
    QGroupBox, QGridLayout
)
from PyQt6.QtCore import Qt

from ..widgets import TagSelector, CollapsibleBox
from .constants import TriggerMode
from .range_helpers import DataTypeMapper, validate_range_section


class TriggerUI:
    """Encapsulates the trigger section UI and behavior.

    Attributes are exposed so dialogs can wire custom behavior and keep the
    same attribute names as before (e.g. `on_off_tag_selector`,
    `range_operand1_selector`, etc.).
    """

    def __init__(
        self,
        parent: Optional[QWidget] = None,
        on_change: Optional[callable] = None,
        on_range_operand1_selected: Optional[callable] = None,
        allowed_range_types: Optional[List[str]] = None,
    ) -> None:
        self.parent = parent
        self.on_change = on_change
        self.on_range_operand1_selected = on_range_operand1_selected

        # Resolve allowed types for range components (default: INT, DINT, REAL)
        if allowed_range_types is None:
            allowed_range_types = [
                DataTypeMapper.normalize_type(t) for t in ["INT", "DINT", "REAL"]
            ]
        self.allowed_range_types = allowed_range_types

        # Top-level container
        self.box = CollapsibleBox("Trigger")

        content = QWidget()
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(5, 10, 5, 5)

        # Mode selector
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(TriggerMode.values())
        content_layout.addWidget(self.mode_combo)

        # Stacked pages: empty, on/off, range
        self.stack = QStackedWidget()
        content_layout.addWidget(self.stack)

        # 1) Empty page
        self.trigger_empty_page = QWidget()
        self.stack.addWidget(self.trigger_empty_page)

        # 2) On/Off page
        self.trigger_onoff_page = QWidget()
        onoff_layout = QVBoxLayout(self.trigger_onoff_page)
        onoff_layout.setContentsMargins(0, 10, 0, 0)
        self.on_off_tag_selector = TagSelector()
        self.on_off_tag_selector.set_allowed_tag_types(["BOOL"])
        self.on_off_tag_selector.main_tag_selector.set_mode_fixed("Tag")
        if self.on_change:
            self.on_off_tag_selector.inputChanged.connect(self.on_change)
        onoff_layout.addWidget(self.on_off_tag_selector)
        onoff_layout.addStretch(1)
        self.stack.addWidget(self.trigger_onoff_page)

        # 3) Range page
        self.trigger_range_page = self._create_range_page()
        self.stack.addWidget(self.trigger_range_page)

        self.box.setContent(content)

    # ------------------------------------------------------------------
    # UI construction helpers
    # ------------------------------------------------------------------
    def _create_range_page(self) -> QWidget:
        group = QGroupBox("Range Configuration")
        group.setObjectName("CardGroup")
        layout = QGridLayout(group)
        layout.setSpacing(10)

        # Operand 1
        op1_layout = QVBoxLayout()
        self.range_operand1_selector = TagSelector(allowed_tag_types=self.allowed_range_types)
        self.range_operand1_selector.main_tag_selector.set_mode_fixed("Tag")
        if self.on_change:
            self.range_operand1_selector.inputChanged.connect(self.on_change)
        if self.on_range_operand1_selected:
            self.range_operand1_selector.tag_selected.connect(self.on_range_operand1_selected)
        op1_layout.addWidget(QLabel("Operand 1"))
        op1_layout.addWidget(self.range_operand1_selector)
        op1_layout.addStretch(1)

        # Operator
        op_layout = QVBoxLayout()
        self.range_operator_combo = QComboBox()
        self.range_operator_combo.addItems(["==", "!=", ">", ">=", "<", "<=", "between", "outside"])
        op_layout.addWidget(QLabel("Operator"))
        op_layout.addWidget(self.range_operator_combo)
        op_layout.addStretch(1)

        # RHS stack (op2 vs. (lower, upper))
        self.range_rhs_stack = QStackedWidget()

        layout.addLayout(op1_layout, 0, 0)
        layout.addLayout(op_layout, 0, 1)
        layout.addWidget(self.range_rhs_stack, 0, 2, alignment=Qt.AlignmentFlag.AlignTop)
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(2, 1)

        # Operand 2 page
        op2_page = QWidget()
        op2_layout = QVBoxLayout(op2_page)
        op2_layout.setContentsMargins(0, 0, 0, 0)
        self.range_operand2_selector = TagSelector(allowed_tag_types=self.allowed_range_types)
        if self.on_change:
            self.range_operand2_selector.inputChanged.connect(self.on_change)
        op2_layout.addWidget(QLabel("Operand 2"))
        op2_layout.addWidget(self.range_operand2_selector)
        op2_layout.addStretch(1)
        self.range_rhs_stack.addWidget(op2_page)

        # Between page (lower + upper)
        between_page = QWidget()
        between_layout = QGridLayout(between_page)
        between_layout.setContentsMargins(0, 0, 0, 0)
        self.range_lower_bound_selector = TagSelector(allowed_tag_types=self.allowed_range_types)
        self.range_upper_bound_selector = TagSelector(allowed_tag_types=self.allowed_range_types)
        if self.on_change:
            self.range_lower_bound_selector.inputChanged.connect(self.on_change)
            self.range_upper_bound_selector.inputChanged.connect(self.on_change)
        between_layout.addWidget(QLabel("Lower Bound"), 0, 0)
        between_layout.addWidget(self.range_lower_bound_selector, 1, 0)
        between_layout.addWidget(QLabel("Upper Bound"), 0, 1)
        between_layout.addWidget(self.range_upper_bound_selector, 1, 1)
        between_layout.setRowStretch(2, 1)
        self.range_rhs_stack.addWidget(between_page)

        # Note: We intentionally do not connect operator changes here so each
        # dialog can wire its own handler to keep existing behavior. However,
        # we provide a helper method below to update the RHS page.
        self.on_range_operator_changed(self.range_operator_combo.currentText())

        return group

    # ------------------------------------------------------------------
    # Behavior helpers
    # ------------------------------------------------------------------
    def on_mode_changed(self, mode: str) -> None:
        if mode == TriggerMode.ORDINARY.value:
            self.stack.setCurrentWidget(self.trigger_empty_page)
        elif mode in [TriggerMode.ON.value, TriggerMode.OFF.value]:
            self.stack.setCurrentWidget(self.trigger_onoff_page)
        elif mode == TriggerMode.RANGE.value:
            self.stack.setCurrentWidget(self.trigger_range_page)
        else:
            self.stack.setCurrentWidget(self.trigger_empty_page)

    def on_range_operator_changed(self, operator: str) -> None:
        if self.range_rhs_stack:
            self.range_rhs_stack.setCurrentIndex(1 if operator in ["between", "outside"] else 0)

    # ------------------------------------------------------------------
    # Validation and data helpers
    # ------------------------------------------------------------------
    def validate(self) -> Tuple[bool, Optional[str]]:
        """Validate the trigger section and return (is_valid, error_message)."""
        mode = self.mode_combo.currentText()
        if mode == TriggerMode.ORDINARY.value:
            return True, None
        if mode in [TriggerMode.ON.value, TriggerMode.OFF.value]:
            if not (self.on_off_tag_selector and self.on_off_tag_selector.get_data()):
                return False, f"A tag must be selected for '{mode}' trigger."
            return True, None
        if mode == TriggerMode.RANGE.value:
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
        return True, None

    def get_data(self) -> Optional[Dict]:
        """Return trigger data dict or None if ordinary mode."""
        mode = self.mode_combo.currentText()
        if mode == TriggerMode.ORDINARY.value:
            return None
        data: Dict = {"mode": mode}
        if mode in [TriggerMode.ON.value, TriggerMode.OFF.value]:
            data["tag"] = self.on_off_tag_selector.get_data()
        elif mode == TriggerMode.RANGE.value:
            data["operator"] = self.range_operator_combo.currentText()
            data["operand1"] = self.range_operand1_selector.get_data()
            if data["operator"] in ["between", "outside"]:
                data["lower_bound"] = self.range_lower_bound_selector.get_data()
                data["upper_bound"] = self.range_upper_bound_selector.get_data()
            else:
                data["operand2"] = self.range_operand2_selector.get_data()
        return data

    def load_data(self, trigger_data: Optional[Dict]) -> None:
        """Populate the trigger widgets from a trigger data dict."""
        if not trigger_data:
            # Reset to ordinary
            self.mode_combo.setCurrentText(TriggerMode.ORDINARY.value)
            self.on_mode_changed(TriggerMode.ORDINARY.value)
            return

        mode = trigger_data.get("mode", TriggerMode.ORDINARY.value)
        self.mode_combo.setCurrentText(mode)
        self.on_mode_changed(mode)

        if mode in [TriggerMode.ON.value, TriggerMode.OFF.value] and self.on_off_tag_selector:
            self.on_off_tag_selector.set_data(trigger_data.get("tag"))
        elif mode == TriggerMode.RANGE.value and self.range_operator_combo:
            operator = trigger_data.get("operator", "==")
            self.range_operator_combo.setCurrentText(operator)
            self.on_range_operator_changed(operator)
            if self.range_operand1_selector:
                self.range_operand1_selector.set_data(trigger_data.get("operand1"))
            if operator in ["between", "outside"]:
                if self.range_lower_bound_selector:
                    self.range_lower_bound_selector.set_data(trigger_data.get("lower_bound"))
                if self.range_upper_bound_selector:
                    self.range_upper_bound_selector.set_data(trigger_data.get("upper_bound"))
            else:
                if self.range_operand2_selector:
                    self.range_operand2_selector.set_data(trigger_data.get("operand2"))

