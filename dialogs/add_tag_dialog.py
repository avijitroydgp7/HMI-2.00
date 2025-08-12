# dialogs/add_tag_dialog.py
from PyQt6.QtWidgets import (
    QFormLayout, QLineEdit, QComboBox, QDialogButtonBox, QSpinBox, 
    QLabel, QMessageBox, QCheckBox, QWidget, QHBoxLayout
)
from PyQt6.QtCore import pyqtSlot
from typing import Optional, Dict, Any
from services.tag_data_service import tag_data_service
# MODIFIED: Import the new CustomDialog base class
from .base_dialog import CustomDialog

DATA_TYPE_RANGES = {
    "INT": {"min": -32768, "max": 32767},
    "DINT": {"min": -2147483648, "max": 2147483647},
    "REAL": {"min": -3.4028235e+38, "max": 3.4028235e+38},
}

# MODIFIED: Inherit from CustomDialog
class AddTagDialog(CustomDialog):
    def __init__(self, db_id: str, parent=None, edit_data: Optional[Dict[str, Any]] = None):
        super().__init__(parent)
        self.db_id = db_id
        self.edit_data = edit_data
        self.original_name = edit_data['name'] if edit_data else None
        self._final_data = {}

        self.setWindowTitle("Edit Tag" if edit_data else "Add New Tag")
        self.setMinimumWidth(400)

        # MODIFIED: Get the content layout from the base class
        content_layout = self.get_content_layout()
        form_layout = QFormLayout()
        form_layout.setContentsMargins(0, 0, 0, 0)

        # --- All widget creation remains the same ---
        self.name_edit = QLineEdit()
        self.data_type_combo = QComboBox()
        self.data_type_combo.addItems(['BOOL', 'INT', 'DINT', 'REAL', 'STRING'])
        self.is_array_checkbox = QCheckBox("Array Tag")
        self.dim1_spin = QSpinBox(); self.dim1_spin.setRange(0, 256)
        self.dim2_spin = QSpinBox(); self.dim2_spin.setRange(0, 256)
        self.dim3_spin = QSpinBox(); self.dim3_spin.setRange(0, 256)
        self.dim1_widget = QWidget(); l1 = QHBoxLayout(self.dim1_widget); l1.setContentsMargins(0,0,0,0); l1.addWidget(QLabel("Dim 1:")); l1.addWidget(self.dim1_spin)
        self.dim2_widget = QWidget(); l2 = QHBoxLayout(self.dim2_widget); l2.setContentsMargins(0,0,0,0); l2.addWidget(QLabel("Dim 2:")); l2.addWidget(self.dim2_spin)
        self.dim3_widget = QWidget(); l3 = QHBoxLayout(self.dim3_widget); l3.setContentsMargins(0,0,0,0); l3.addWidget(QLabel("Dim 3:")); l3.addWidget(self.dim3_spin)
        self.length_label = QLabel("Length:")
        self.length_spinbox = QSpinBox(); self.length_spinbox.setRange(1, 8192)
        self.initial_value_label = QLabel("Initial Value:")
        self.initial_value_edit = QLineEdit()
        self.comment_edit = QLineEdit()

        form_layout.addRow("Tag Name:", self.name_edit)
        form_layout.addRow("Data Type:", self.data_type_combo)
        form_layout.addRow(self.is_array_checkbox)
        form_layout.addRow(self.dim1_widget)
        form_layout.addRow(self.dim2_widget)
        form_layout.addRow(self.dim3_widget)
        form_layout.addRow(self.length_label, self.length_spinbox)
        form_layout.addRow(self.initial_value_label, self.initial_value_edit)
        form_layout.addRow("Comment:", self.comment_edit)
        
        # MODIFIED: Add all widgets to the content_layout
        content_layout.addLayout(form_layout)

        self.error_label = QLabel()
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setVisible(False)
        content_layout.addWidget(self.error_label)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        content_layout.addWidget(self.button_box)

        # --- Signal connections remain the same ---
        self.name_edit.textChanged.connect(self._validate_form)
        self.initial_value_edit.textChanged.connect(self._validate_form)
        self.data_type_combo.currentIndexChanged.connect(self._update_ui_state)
        self.is_array_checkbox.toggled.connect(self._update_ui_state)
        self.dim1_spin.valueChanged.connect(self._update_ui_state)
        self.dim2_spin.valueChanged.connect(self._update_ui_state)
        self.dim3_spin.valueChanged.connect(self._validate_form)
        
        if self.edit_data:
            self._populate_fields()
        
        self._update_ui_state()

    # ... all other methods (_populate_fields, _validate_form, etc.) remain unchanged ...
    def _populate_fields(self):
        self.name_edit.setText(self.edit_data.get('name', ''))
        self.data_type_combo.setCurrentText(self.edit_data.get('data_type', 'INT'))
        self.length_spinbox.setValue(self.edit_data.get('length', 1))
        self.comment_edit.setText(self.edit_data.get('comment', ''))
        
        array_dims = self.edit_data.get('array_dims', [])
        if array_dims:
            self.is_array_checkbox.setChecked(True)
            self.dim1_spin.setValue(array_dims[0] if len(array_dims) > 0 else 0)
            self.dim2_spin.setValue(array_dims[1] if len(array_dims) > 1 else 0)
            self.dim3_spin.setValue(array_dims[2] if len(array_dims) > 2 else 0)
        else:
            self.initial_value_edit.setText(str(self.edit_data.get('value', '')))

    def _update_ui_state(self):
        is_array = self.is_array_checkbox.isChecked()
        is_string = self.data_type_combo.currentText() == 'STRING'
        
        self.dim1_widget.setVisible(is_array)
        
        dim1_active = is_array and self.dim1_spin.value() > 0
        self.dim2_widget.setVisible(dim1_active)
        if not dim1_active: self.dim2_spin.setValue(0)

        dim2_active = dim1_active and self.dim2_spin.value() > 0
        self.dim3_widget.setVisible(dim2_active)
        if not dim2_active: self.dim3_spin.setValue(0)
        
        self.length_label.setVisible(is_string and not is_array)
        self.length_spinbox.setVisible(is_string and not is_array)
        
        self.initial_value_label.setVisible(not is_array)
        self.initial_value_edit.setVisible(not is_array)
        
        self._validate_form()

    @pyqtSlot()
    def _validate_form(self):
        try:
            self.get_tag_data()
            self.error_label.setVisible(False)
            self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(True)
        except ValueError as e:
            self.error_label.setText(str(e))
            self.error_label.setVisible(True)
            self.button_box.button(QDialogButtonBox.StandardButton.Ok).setEnabled(False)

    def _parse_and_validate_value(self, value_str: str, data_type: str) -> Optional[Any]:
        value_str = value_str.strip()
        if not value_str: return None
        try:
            if data_type in ('INT', 'DINT'): value = int(value_str)
            elif data_type == 'REAL': value = float(value_str)
            elif data_type == 'BOOL':
                val_lower = value_str.lower()
                if val_lower in ('true', '1'): return True
                if val_lower in ('false', '0'): return False
                raise ValueError("Value must be True, False, 1, or 0.")
            elif data_type == 'STRING': return value_str
            else: return None
        except (ValueError, TypeError):
            raise ValueError(f"'{value_str}' is not a valid {data_type} value.")
        if data_type in DATA_TYPE_RANGES:
            type_range = DATA_TYPE_RANGES[data_type]
            if not (type_range["min"] <= value <= type_range["max"]):
                raise ValueError(f"{data_type} value must be between {type_range['min']} and {type_range['max']}.")
        return value

    def get_tag_data(self) -> Dict[str, Any]:
        data_type = self.data_type_combo.currentText()
        tag_name = self.name_edit.text().strip()
        if not tag_name: raise ValueError("Tag Name cannot be empty.")
        if tag_name != self.original_name and not tag_data_service.is_tag_name_unique(self.db_id, tag_name):
            raise ValueError(f"Tag Name '{tag_name}' already exists.")

        tag_data = {"name": tag_name, "data_type": data_type, "comment": self.comment_edit.text()}
        
        if data_type == 'STRING':
            tag_data['length'] = self.length_spinbox.value()
        else:
            tag_data['length'] = 0

        if self.is_array_checkbox.isChecked():
            dims = []
            d1 = self.dim1_spin.value()
            if d1 > 0:
                dims.append(d1)
                d2 = self.dim2_spin.value()
                if d2 > 0:
                    dims.append(d2)
                    d3 = self.dim3_spin.value()
                    if d3 > 0:
                        dims.append(d3)
            
            if not dims: raise ValueError("Array must have at least one dimension greater than 0.")
            tag_data['array_dims'] = dims
            tag_data['value'] = tag_data_service._create_default_array(dims, data_type)
        else:
            initial_val = self._parse_and_validate_value(self.initial_value_edit.text(), data_type)
            if data_type == 'STRING' and initial_val is not None and len(initial_val) > tag_data['length']:
                raise ValueError(f"Initial Value length exceeds specified Length ({tag_data['length']}).")
            
            tag_data['array_dims'] = []
            tag_data['value'] = initial_val
            if tag_data['value'] is None:
                if data_type == 'BOOL': tag_data['value'] = False
                elif data_type in ('INT', 'DINT', 'REAL'): tag_data['value'] = 0
                elif data_type == 'STRING': tag_data['value'] = ""
        return tag_data

    def accept(self):
        try:
            self._final_data = self.get_tag_data()
            super().accept()
        except ValueError as e:
            QMessageBox.critical(self, "Validation Error", str(e))

    def get_final_data(self):
        return self._final_data
