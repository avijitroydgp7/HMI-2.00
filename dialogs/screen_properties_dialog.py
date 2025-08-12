# dialogs/screen_properties_dialog.py
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QGroupBox,
    QFormLayout, QLineEdit, QTextEdit, QSpinBox, QColorDialog,
    QDialogButtonBox, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QIntValidator, QColor
from typing import Optional, Dict, Any
from services.screen_data_service import screen_service
from .base_dialog import CustomDialog

class ScreenPropertiesDialog(CustomDialog):
    """Dialog for creating and editing screen properties with a custom title bar."""
    def __init__(self, screen_type, parent=None, edit_data=None):
        super().__init__(parent)
        self.screen_type = screen_type
        self.edit_mode = edit_data is not None
        
        self.original_id = edit_data.get('id') if self.edit_mode and edit_data else None
        self.original_number = edit_data.get('number') if self.edit_mode and edit_data else None
        
        title = f"{'Edit' if self.edit_mode else 'New'} {self.screen_type.capitalize()} Screen"
        self.setWindowTitle(title)
        self.setMinimumWidth(450)
        
        content_layout = self.get_content_layout()
        content_layout.addWidget(self._create_main_properties_group())
        content_layout.addWidget(self._create_style_group())
        
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        content_layout.addWidget(self.button_box)
        
        self.num_input.textChanged.connect(self.validate_inputs)
        self.name_input.textChanged.connect(self.validate_inputs)
        self.transparent_checkbox.toggled.connect(self._update_style_controls_state)
        
        if self.edit_mode and edit_data:
            self._populate_initial_data(edit_data)
        else:
            self._populate_initial_data_for_new()
        
        self.validate_inputs()
        self._update_style_controls_state()

    def _create_main_properties_group(self):
        main_group = QGroupBox("Screen Properties")
        form_layout = QFormLayout()
        form_layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.num_input = QLineEdit()
        self.num_input.setValidator(QIntValidator(1, 9999))
        self.name_input = QLineEdit()
        self.desc_input = QTextEdit()
        self.desc_input.setFixedHeight(60)
        
        self.error_label = QLabel("Error message here")
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setVisible(False)
        
        num_layout = QVBoxLayout()
        num_layout.setSpacing(2)
        num_layout.addWidget(self.num_input)
        num_layout.addWidget(self.error_label)
        
        form_layout.addRow("Screen Number:", num_layout)
        form_layout.addRow("Screen Name:", self.name_input)
        form_layout.addRow("Description:", self.desc_input)
        
        size_layout = QHBoxLayout()
        self.width_spinbox = QSpinBox(); self.width_spinbox.setRange(100, 8000)
        self.height_spinbox = QSpinBox(); self.height_spinbox.setRange(100, 8000)
        size_layout.addWidget(self.width_spinbox); size_layout.addWidget(QLabel("x")); size_layout.addWidget(self.height_spinbox)
        form_layout.addRow("Size (W x H):", size_layout)
        
        main_group.setLayout(form_layout)
        return main_group

    def _create_style_group(self):
        style_group = QGroupBox("Background Style")
        layout = QFormLayout()
        layout.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        self.transparent_checkbox = QCheckBox("Transparent Background")
        self.solid_color_btn = QPushButton("Choose Color")
        self.solid_color_btn.clicked.connect(lambda: self._pick_color(self.solid_color_btn))
        
        layout.addRow(self.transparent_checkbox)
        layout.addRow("Color:", self.solid_color_btn)
        
        style_group.setLayout(layout)
        return style_group

    def _update_style_controls_state(self):
        is_transparent = self.transparent_checkbox.isChecked()
        self.solid_color_btn.setEnabled(not is_transparent)

    def _populate_initial_data(self, data):
        self.num_input.setText(str(data.get('number', '')))
        self.name_input.setText(data.get('name', ''))
        self.desc_input.setPlainText(data.get('description', ''))
        size = data.get('size', {'width': 1920, 'height': 1080})
        self.width_spinbox.setValue(size.get('width', 1920))
        self.height_spinbox.setValue(size.get('height', 1080))
        
        style = data.get('style', {})
        is_transparent = style.get('transparent', False)
        self.transparent_checkbox.setChecked(is_transparent)

        color = style.get('color1')
        if color:
            self._set_button_color(self.solid_color_btn, color)
    
    def _populate_initial_data_for_new(self):
        self.width_spinbox.setValue(1920)
        self.height_spinbox.setValue(1080)
        self.transparent_checkbox.setChecked(False)

    def _pick_color(self, button):
        initial_color = button.property("color") or "#ffffff"
        color = QColorDialog.getColor(QColor(initial_color), self, "Select Color")
        if color.isValid():
            self._set_button_color(button, color.name())
            self.transparent_checkbox.setChecked(False)

    def _set_button_color(self, button, color_hex):
        color = QColor(color_hex)
        lightness = color.lightnessF()
        text_color = "#ffffff" if lightness < 0.5 else "#000000"
        button.setStyleSheet(f"background-color: {color_hex}; color: {text_color}; border: 1px solid #5a6270; padding: 5px; border-radius: 4px;")
        button.setProperty("color", color_hex)

    def validate_inputs(self):
        num_text = self.num_input.text()
        name_text = self.name_input.text().strip()
        
        if not num_text or not name_text:
            self.ok_button.setEnabled(False)
            self.error_label.setVisible(False)
            return

        try:
            screen_num = int(num_text)
            if self.edit_mode and screen_num == self.original_number:
                self.error_label.setVisible(False)
                self.ok_button.setEnabled(True)
                return

            is_unique = screen_service.is_screen_number_unique(self.screen_type, screen_num, self.original_id)
            if not is_unique:
                self.error_label.setText("This screen number is already in use.")
                self.error_label.setVisible(True)
                self.ok_button.setEnabled(False)
            else:
                self.error_label.setVisible(False)
                self.ok_button.setEnabled(True)
        except ValueError:
            self.ok_button.setEnabled(False)
            self.error_label.setText("Invalid number.")
            self.error_label.setVisible(True)

    def get_data(self):
        style_data = {
            'transparent': self.transparent_checkbox.isChecked()
        }
        if not style_data['transparent']:
            chosen_color = self.solid_color_btn.property("color")
            if chosen_color:
                style_data['color1'] = chosen_color

        return {
            'number': int(self.num_input.text()), 
            'name': self.name_input.text().strip(), 
            'description': self.desc_input.toPlainText().strip(), 
            'size': {'width': self.width_spinbox.value(), 'height': self.height_spinbox.value()}, 
            'style': style_data
        }
