from PyQt6.QtWidgets import (
    QFormLayout, QLineEdit, QDialogButtonBox, QLabel, QVBoxLayout, QDialog
)
from PyQt6.QtCore import pyqtSlot
from services.comment_data_service import comment_data_service

class NewCommentTableDialog(QDialog):
    """
    A dialog for creating new comment tables or renaming existing ones.
    """
    
    def __init__(self, parent=None, edit_group=None):
        super().__init__(parent)
        self.edit_group = edit_group
        
        title = "Rename Comment Table" if edit_group else "New Comment Table"
        self.setWindowTitle(title)
        self.setMinimumWidth(350)

        content_layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.number_edit = QLineEdit()
        self.name_edit = QLineEdit()
        
        if edit_group:
            group_data = comment_data_service.get_group(edit_group)
            if group_data:
                self.number_edit.setText(group_data.get('number', ''))
                self.name_edit.setText(group_data.get('name', ''))

        form_layout.addRow("Table Number:", self.number_edit)
        form_layout.addRow("Table Name:", self.name_edit)
        content_layout.addLayout(form_layout)

        self.error_label = QLabel()
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setVisible(False)
        content_layout.addWidget(self.error_label)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        content_layout.addWidget(self.button_box)

        self.number_edit.textChanged.connect(self.validate_input)
        self.name_edit.textChanged.connect(self.validate_input)
        self.validate_input()

    def get_values(self):
        """Returns the entered number and name."""
        return self.number_edit.text().strip(), self.name_edit.text().strip()

    @pyqtSlot()
    def validate_input(self):
        """Validates the input and enables/disables the OK button."""
        number = self.number_edit.text().strip()
        name = self.name_edit.text().strip()
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        
        if not number or not name:
            self.error_label.setText("Both number and name are required.")
            self.error_label.setVisible(True)
            ok_button.setEnabled(False)
        elif not self.edit_group and not comment_data_service.is_group_number_unique(number):
            self.error_label.setText(f"A table with number '{number}' already exists.")
            self.error_label.setVisible(True)
            ok_button.setEnabled(False)
        elif self.edit_group:
            # Check if new number is unique (excluding current group)
            group_data = comment_data_service.get_group(self.edit_group)
            if group_data and number != group_data.get('number', ''):
                if not comment_data_service.is_group_number_unique(number):
                    self.error_label.setText(f"A table with number '{number}' already exists.")
                    self.error_label.setVisible(True)
                    ok_button.setEnabled(False)
                else:
                    self.error_label.setVisible(False)
                    ok_button.setEnabled(True)
            else:
                self.error_label.setVisible(False)
                ok_button.setEnabled(True)
        else:
            self.error_label.setVisible(False)
            ok_button.setEnabled(True)
