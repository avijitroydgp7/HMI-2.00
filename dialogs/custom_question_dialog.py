# dialogs/custom_question_dialog.py
# A custom, stylable dialog for asking Yes/No questions.

from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QMessageBox
from .base_dialog import CustomDialog

class CustomQuestionDialog(CustomDialog):
    """
    A custom dialog for asking Yes/No questions, inheriting the
    custom title bar and application theme.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(400)
        self.answer = QMessageBox.StandardButton.No # Default answer is No

        content_layout = self.get_content_layout()
        
        self.question_label = QLabel("Question text goes here.")
        self.question_label.setWordWrap(True)
        content_layout.addWidget(self.question_label)
        
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        yes_button = QPushButton("Yes")
        yes_button.setDefault(True)
        yes_button.clicked.connect(self._on_yes)
        
        no_button = QPushButton("No")
        no_button.clicked.connect(self.reject)
        
        button_layout.addWidget(yes_button)
        button_layout.addWidget(no_button)
        
        content_layout.addLayout(button_layout)
        
    def setText(self, text):
        """Sets the main question text of the dialog."""
        self.question_label.setText(text)
        
    def _on_yes(self):
        """Sets the answer to Yes and closes the dialog."""
        self.answer = QMessageBox.StandardButton.Yes
        self.accept()
        
    @staticmethod
    def ask(parent, title, text) -> QMessageBox.StandardButton:
        """A static method to quickly ask a Yes/No question."""
        dialog = CustomQuestionDialog(parent)
        dialog.setWindowTitle(title)
        dialog.setText(text)
        dialog.exec()
        return dialog.answer
