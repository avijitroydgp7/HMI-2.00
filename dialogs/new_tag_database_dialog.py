# dialogs/new_tag_database_dialog.py
from PyQt6.QtWidgets import (
    QFormLayout, QLineEdit, QDialogButtonBox, QLabel
)
from PyQt6.QtCore import pyqtSlot
from services.tag_data_service import tag_data_service
from .base_dialog import CustomDialog

class NewTagDatabaseDialog(CustomDialog):
    """
    A simple dialog to get a name for a new tag database or to rename an
    existing one, with a custom title bar.
    """
    def __init__(self, parent=None, edit_name=None):
        super().__init__(parent)
        self.edit_name = edit_name
        
        title = "Rename Tag Database" if edit_name else "New Tag Database"
        self.setWindowTitle(title)
        self.setMinimumWidth(350)

        content_layout = self.get_content_layout()
        form_layout = QFormLayout()

        self.name_edit = QLineEdit()
        if edit_name:
            self.name_edit.setText(edit_name)
            
        form_layout.addRow("Database Name:", self.name_edit)
        content_layout.addLayout(form_layout)

        self.error_label = QLabel()
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setVisible(False)
        content_layout.addWidget(self.error_label)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        content_layout.addWidget(self.button_box)

        self.name_edit.textChanged.connect(self.validate_input)
        self.validate_input()

    def get_database_name(self):
        """Returns the entered database name."""
        return self.name_edit.text().strip()

    @pyqtSlot()
    def validate_input(self):
        """Validates the input name and enables/disables the OK button."""
        name = self.get_database_name()
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        
        if not name:
            self.error_label.setText("Database name cannot be empty.")
            self.error_label.setVisible(True)
            ok_button.setEnabled(False)
        elif name != self.edit_name and not tag_data_service.is_database_name_unique(name):
            self.error_label.setText(f"A database named '{name}' already exists.")
            self.error_label.setVisible(True)
            ok_button.setEnabled(False)
        else:
            self.error_label.setVisible(False)
            ok_button.setEnabled(True)
