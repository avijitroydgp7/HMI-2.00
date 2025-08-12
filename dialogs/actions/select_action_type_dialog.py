# dialogs/actions/select_action_type_dialog.py
# A simple dialog to let the user choose the type of action to create.

from PyQt6.QtWidgets import QPushButton
from ..base_dialog import CustomDialog

class SelectActionTypeDialog(CustomDialog):
    """
    A dialog that prompts the user to select what kind of action
    they want to add to a button, with a custom title bar.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Select Action Type")
        self.selected_action_type = None

        content_layout = self.get_content_layout()
        
        self.bit_button = QPushButton("Bit Action")
        self.bit_button.setToolTip("Control a single bit (ON/OFF, Toggle, etc.)")
        self.bit_button.clicked.connect(lambda: self.select_type("bit"))

        self.word_button = QPushButton("Word Action")
        self.word_button.setToolTip("Manipulate numerical data (INT, REAL, etc.)")
        self.word_button.clicked.connect(lambda: self.select_type("word"))

        content_layout.addWidget(self.bit_button)
        content_layout.addWidget(self.word_button)
        
        # The base dialog's close button will act as a cancel.

    def select_type(self, action_type):
        """Sets the selected type and accepts the dialog."""
        self.selected_action_type = action_type
        self.accept()
