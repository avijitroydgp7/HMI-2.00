# dialogs/custom_message_box.py
# A custom, stylable message box to replace the standard QMessageBox.

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget
)
from PyQt6.QtCore import Qt, QPoint
from PyQt6.QtGui import QPixmap
from utils.icon_manager import IconManager

class CustomMessageBox(QDialog):
    """
    A custom dialog that mimics QMessageBox but can be fully styled
    with QSS to match the application's theme. Includes a custom title bar.
    """
    Save = 0x00000800
    Discard = 0x00800000
    Cancel = 0x00400000

    def __init__(self, parent=None):
        super().__init__(parent)
        self.result = self.Cancel
        self.drag_pos = QPoint()

        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setObjectName("CustomMessageBox")
        self.setModal(True)
        
        self._setup_ui()

    def _setup_ui(self):
        self.container = QWidget(self)
        self.container.setObjectName("Container")
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.container)

        self.layout = QVBoxLayout(self.container)
        self.layout.setContentsMargins(1, 1, 1, 1) # Small margin for the border
        self.layout.setSpacing(0)

        # --- Custom Title Bar ---
        title_bar_widget = QWidget()
        title_bar_widget.setObjectName("TitleBar")
        title_bar_layout = QHBoxLayout(title_bar_widget)
        title_bar_layout.setContentsMargins(10, 5, 5, 5)
        
        self.title_label = QLabel()
        self.title_label.setObjectName("TitleLabel")
        
        self.close_button = QPushButton(IconManager.create_icon('fa5s.times'), "")
        self.close_button.setObjectName("CloseButton")
        self.close_button.clicked.connect(self._on_cancel)
        
        title_bar_layout.addWidget(self.title_label)
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(self.close_button)
        self.layout.addWidget(title_bar_widget)

        # --- Content Area ---
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setContentsMargins(15, 15, 15, 15)
        content_layout.setSpacing(15)
        self.layout.addWidget(content_widget)

        top_layout = QHBoxLayout()
        top_layout.setSpacing(15)
        
        self.icon_label = QLabel()
        pixmap = IconManager.create_pixmap('fa5s.question-circle', 48, color="#528bff")
        self.icon_label.setPixmap(pixmap)
        top_layout.addWidget(self.icon_label)
        
        self.text_label = QLabel()
        top_layout.addWidget(self.text_label, 1) # Add stretch factor
        content_layout.addLayout(top_layout)

        # --- Button Box ---
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.save_button = QPushButton("Save")
        self.save_button.setObjectName("SaveButton")
        self.save_button.clicked.connect(self._on_save)
        
        self.discard_button = QPushButton("Discard")
        self.discard_button.clicked.connect(self._on_discard)

        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self._on_cancel)
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.discard_button)
        button_layout.addWidget(self.cancel_button)
        content_layout.addLayout(button_layout)

    def mousePressEvent(self, event):
        self.drag_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        self.move(self.pos() + event.globalPosition().toPoint() - self.drag_pos)
        self.drag_pos = event.globalPosition().toPoint()
        event.accept()

    def setText(self, text):
        self.text_label.setText(text)
        self.text_label.setWordWrap(True)

    def setWindowTitle(self, title):
        self.title_label.setText(title)

    def exec(self):
        return super().exec()

    def result(self):
        return self.dialog_result

    def _on_save(self):
        self.dialog_result = self.Save
        self.accept()

    def _on_discard(self):
        self.dialog_result = self.Discard
        self.accept()

    def _on_cancel(self):
        self.dialog_result = self.Cancel
        self.reject()
