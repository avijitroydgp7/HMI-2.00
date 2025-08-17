from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QLabel, QDialogButtonBox
)
from PyQt6.QtCore import pyqtSlot
from services.comment_data_service import comment_data_service


class NewCommentTableDialog(QDialog):
    """Dialog for entering a unique group number and comment name."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("New Comment Table")
        self.setMinimumWidth(300)

        main_layout = QVBoxLayout(self)
        form_layout = QFormLayout()
        self.number_edit = QLineEdit()
        self.name_edit = QLineEdit()
        form_layout.addRow("Group No:", self.number_edit)
        form_layout.addRow("Name:", self.name_edit)
        main_layout.addLayout(form_layout)

        self.error_label = QLabel()
        self.error_label.setObjectName("ErrorLabel")
        self.error_label.setVisible(False)
        main_layout.addWidget(self.error_label)

        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)

        self.number_edit.textChanged.connect(self.validate_input)
        self.name_edit.textChanged.connect(self.validate_input)
        self.validate_input()

    def get_values(self) -> tuple[str, str]:
        return self.number_edit.text().strip(), self.name_edit.text().strip()

    @pyqtSlot()
    def validate_input(self) -> None:
        number, name = self.get_values()
        ok_btn = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if not number or not name:
            self.error_label.setText("Both fields are required.")
            self.error_label.setVisible(True)
            ok_btn.setEnabled(False)
        elif not comment_data_service.is_group_number_unique(number):
            self.error_label.setText(f"Group number '{number}' already exists.")
            self.error_label.setVisible(True)
            ok_btn.setEnabled(False)
        else:
            self.error_label.setVisible(False)
            ok_btn.setEnabled(True)