# dialogs/custom_info_dialog.py
# A custom, stylable dialog for showing simple informational messages.

from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QDialog

class CustomInfoDialog(QDialog):
    """
    A custom dialog for showing information, warnings, or errors,
    with a single "OK" button. It inherits the custom title bar.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumWidth(400)

        content_layout = QVBoxLayout(self)
        
        # Main content layout
        main_content_layout = QVBoxLayout()
        main_content_layout.setSpacing(15)
        
        self.info_label = QLabel("Information text goes here.")
        self.info_label.setWordWrap(True)
        main_content_layout.addWidget(self.info_label)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        ok_button = QPushButton("OK")
        ok_button.setDefault(True)
        ok_button.clicked.connect(self.accept)
        button_layout.addWidget(ok_button)
        
        main_content_layout.addLayout(button_layout)
        content_layout.addLayout(main_content_layout)

    def setText(self, text):
        """Sets the main text of the dialog."""
        self.info_label.setText(text)

    @staticmethod
    def show_info(parent, title, text):
        """A static method to quickly show an informational dialog."""
        dialog = CustomInfoDialog(parent)
        dialog.setWindowTitle(title)
        dialog.setText(text)
        dialog.exec()
