# dialogs/project_info_dialog.py
from PyQt6.QtWidgets import (
    QFormLayout, QLineEdit, QTextEdit,
    QDialogButtonBox, QLabel, QListWidget, QAbstractItemView
)
from typing import Dict, Any
from .base_dialog import CustomDialog

class ProjectInfoDialog(CustomDialog):
    """
    A dialog to display and edit project-wide information, with a custom title bar.
    """
    def __init__(self, project_info: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Project Information")
        self.setMinimumWidth(500)
        self.setMinimumHeight(450)

        content_layout = self.get_content_layout()
        form_layout = QFormLayout()

        self.author_edit = QLineEdit(project_info.get('author', ''))
        self.company_edit = QLineEdit(project_info.get('company', ''))
        self.description_edit = QTextEdit(project_info.get('description', ''))
        self.description_edit.setFixedHeight(80)

        self.creation_date_label = QLabel(project_info.get('creation_date', 'N/A'))
        self.modification_date_label = QLabel(project_info.get('modification_date', 'N/A'))

        self.history_list = QListWidget()
        self.history_list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        save_history = project_info.get('save_history', [])
        for entry in reversed(save_history):
            self.history_list.addItem(entry)

        form_layout.addRow("Author:", self.author_edit)
        form_layout.addRow("Company:", self.company_edit)
        form_layout.addRow("Description:", self.description_edit)
        form_layout.addRow("Creation Date:", self.creation_date_label)
        form_layout.addRow("Last Modified:", self.modification_date_label)
        form_layout.addRow("Save History:", self.history_list)
        
        content_layout.addLayout(form_layout)

        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        content_layout.addWidget(self.button_box)

    def get_data(self) -> Dict[str, Any]:
        """Returns the data entered in the editable dialog fields."""
        return {
            "author": self.author_edit.text(),
            "company": self.company_edit.text(),
            "description": self.description_edit.toPlainText()
        }
