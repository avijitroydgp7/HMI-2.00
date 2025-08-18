# components/button/conditional_style_editor_dialog.py
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QSpinBox, QGroupBox,
    QPushButton, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView, QDialogButtonBox, QComboBox
)
from typing import Optional
import copy

from .conditional_style import ConditionalStyle, StyleCondition
from dialogs.tag_browser_dialog import TagBrowserDialog


class ConditionEditorDialog(QDialog):
    def __init__(self, parent=None, condition: Optional[StyleCondition] = None):
        super().__init__(parent)
        self.setWindowTitle("Edit Condition")
        self.condition = copy.deepcopy(condition) if condition else StyleCondition()

        layout = QFormLayout(self)
        tag_layout = QHBoxLayout()
        self.tag_edit = QLineEdit(self.condition.tag_path)
        browse_btn = QPushButton("...")
        browse_btn.clicked.connect(self._browse_tag)
        tag_layout.addWidget(self.tag_edit)
        tag_layout.addWidget(browse_btn)
        layout.addRow("Tag Path:", tag_layout)

        self.operator_combo = QComboBox()
        self.operator_combo.addItems(["==", "!=", ">", "<", ">=", "<=", "between", "outside"])
        self.operator_combo.setCurrentText(self.condition.operator)
        layout.addRow("Operator:", self.operator_combo)

        self.value_edit = QLineEdit(str(self.condition.value) if self.condition.value is not None else "")
        self.value2_edit = QLineEdit(str(self.condition.value2) if self.condition.value2 is not None else "")
        layout.addRow("Value:", self.value_edit)
        layout.addRow("Value2:", self.value2_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _browse_tag(self):
        dlg = TagBrowserDialog(self)
        if dlg.exec():
            info = dlg.get_selected_tag_info()
            if info:
                db_id, db_name, tag_name = info
                self.tag_edit.setText(f"[{db_name}]::{tag_name}")

    def get_condition(self) -> StyleCondition:
        cond = StyleCondition(
            tag_path=self.tag_edit.text(),
            operator=self.operator_combo.currentText(),
            value=self.value_edit.text() or None,
            value2=self.value2_edit.text() or None,
        )
        return cond


class ConditionalStyleEditorDialog(QDialog):
    def __init__(self, parent=None, style: Optional[ConditionalStyle] = None):
        super().__init__(parent)
        self.setWindowTitle("Conditional Style")
        self.style = copy.deepcopy(style) if style else ConditionalStyle()

        self.conditions = copy.deepcopy(self.style.conditions)

        layout = QVBoxLayout(self)

        form = QFormLayout()
        self.name_edit = QLineEdit(self.style.name)
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(-100000, 100000)
        self.priority_spin.setValue(self.style.priority)
        self.tooltip_edit = QLineEdit(self.style.properties.get("tooltip", ""))
        form.addRow("Name:", self.name_edit)
        form.addRow("Priority:", self.priority_spin)
        form.addRow("Tooltip:", self.tooltip_edit)
        layout.addLayout(form)

        # Base style group
        base_group = QGroupBox("Base Style")
        base_form = QFormLayout(base_group)
        self.bg_color_edit = QLineEdit(self.style.properties.get("background_color", ""))
        self.text_color_edit = QLineEdit(self.style.properties.get("text_color", ""))
        self.font_size_spin = QSpinBox(); self.font_size_spin.setRange(1, 1000)
        self.font_size_spin.setValue(self.style.properties.get("font_size", 10))
        self.width_spin = QSpinBox(); self.width_spin.setRange(0, 10000)
        self.width_spin.setValue(self.style.properties.get("width", 0))
        self.height_spin = QSpinBox(); self.height_spin.setRange(0, 10000)
        self.height_spin.setValue(self.style.properties.get("height", 0))
        base_form.addRow("Background:", self.bg_color_edit)
        base_form.addRow("Text Color:", self.text_color_edit)
        base_form.addRow("Font Size:", self.font_size_spin)
        base_form.addRow("Width:", self.width_spin)
        base_form.addRow("Height:", self.height_spin)
        layout.addWidget(base_group)

        # Hover style group
        hover_group = QGroupBox("Hover Style")
        hover_form = QFormLayout(hover_group)
        self.hover_bg_edit = QLineEdit(self.style.properties.get("hover_background_color", ""))
        self.hover_text_edit = QLineEdit(self.style.properties.get("hover_text_color", ""))
        hover_form.addRow("Background:", self.hover_bg_edit)
        hover_form.addRow("Text Color:", self.hover_text_edit)
        layout.addWidget(hover_group)

        # Click style group
        click_group = QGroupBox("Click Style")
        click_form = QFormLayout(click_group)
        self.click_bg_edit = QLineEdit(self.style.properties.get("click_background_color", ""))
        self.click_text_edit = QLineEdit(self.style.properties.get("click_text_color", ""))
        click_form.addRow("Background:", self.click_bg_edit)
        click_form.addRow("Text Color:", self.click_text_edit)
        layout.addWidget(click_group)

        # Conditions group
        cond_group = QGroupBox("Conditions")
        cond_layout = QVBoxLayout(cond_group)
        self.condition_table = QTableWidget()
        self.condition_table.setColumnCount(4)
        self.condition_table.setHorizontalHeaderLabels(["Tag Path", "Operator", "Value", "Value2"])
        self.condition_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.condition_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.condition_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.condition_table.verticalHeader().setVisible(False)
        header = self.condition_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        cond_layout.addWidget(self.condition_table)

        cond_buttons = QHBoxLayout()
        add_cond_btn = QPushButton("Add")
        edit_cond_btn = QPushButton("Edit")
        remove_cond_btn = QPushButton("Remove")
        add_cond_btn.clicked.connect(self._add_condition)
        edit_cond_btn.clicked.connect(self._edit_condition)
        remove_cond_btn.clicked.connect(self._remove_condition)
        cond_buttons.addWidget(add_cond_btn)
        cond_buttons.addWidget(edit_cond_btn)
        cond_buttons.addWidget(remove_cond_btn)
        cond_buttons.addStretch()
        cond_layout.addLayout(cond_buttons)
        layout.addWidget(cond_group)

        self._refresh_condition_table()

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)

    def _refresh_condition_table(self):
        self.condition_table.setRowCount(0)
        for i, cond in enumerate(self.conditions):
            self.condition_table.insertRow(i)
            self.condition_table.setItem(i, 0, QTableWidgetItem(cond.tag_path))
            self.condition_table.setItem(i, 1, QTableWidgetItem(cond.operator))
            self.condition_table.setItem(i, 2, QTableWidgetItem(str(cond.value)))
            self.condition_table.setItem(i, 3, QTableWidgetItem(str(cond.value2) if cond.value2 is not None else ""))

    def _add_condition(self):
        dlg = ConditionEditorDialog(self)
        if dlg.exec():
            self.conditions.append(dlg.get_condition())
            self._refresh_condition_table()

    def _edit_condition(self):
        rows = self.condition_table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        cond = self.conditions[row]
        dlg = ConditionEditorDialog(self, cond)
        if dlg.exec():
            self.conditions[row] = dlg.get_condition()
            self._refresh_condition_table()

    def _remove_condition(self):
        rows = self.condition_table.selectionModel().selectedRows()
        if not rows:
            return
        row = rows[0].row()
        if 0 <= row < len(self.conditions):
            del self.conditions[row]
            self._refresh_condition_table()

    def get_style(self) -> ConditionalStyle:
        props = {
            "background_color": self.bg_color_edit.text(),
            "text_color": self.text_color_edit.text(),
            "font_size": self.font_size_spin.value(),
            "width": self.width_spin.value(),
            "height": self.height_spin.value(),
            "hover_background_color": self.hover_bg_edit.text(),
            "hover_text_color": self.hover_text_edit.text(),
            "click_background_color": self.click_bg_edit.text(),
            "click_text_color": self.click_text_edit.text(),
            "tooltip": self.tooltip_edit.text(),
        }
        style = ConditionalStyle(
            name=self.name_edit.text(),
            style_id=self.style.style_id,
            conditions=self.conditions,
            properties=props,
            priority=self.priority_spin.value(),
        )
        return style