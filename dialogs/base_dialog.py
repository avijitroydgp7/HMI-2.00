# dialogs/base_dialog.py
# A custom, stylable base dialog with a movable title bar.

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QWidget, QSizePolicy
)
from PyQt6.QtCore import Qt, QPoint
from utils.icon_manager import IconManager

class CustomDialog(QDialog):
    """
    A base class for all custom dialogs in the application.
    It provides a consistent, stylable, and movable title bar.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.drag_pos = QPoint()

        # Make the dialog frameless and transparent to draw our own frame
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.Dialog)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        # Main layout for the entire dialog window
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(1, 1, 1, 1)
        main_layout.setSpacing(0)

        # --- Custom Title Bar ---
        self.title_bar = QWidget()
        self.title_bar.setObjectName("TitleBar")
        self.title_bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        title_bar_layout = QHBoxLayout(self.title_bar)
        title_bar_layout.setContentsMargins(10, 5, 5, 5)
        
        self.title_label = QLabel("Dialog")
        self.title_label.setObjectName("TitleLabel")
        
        self.close_icon = IconManager.create_animated_icon('fa5s.times')
        self.close_button = QPushButton(self.close_icon.icon, "")
        self.close_icon.add_target(self.close_button)
        self.close_button.setObjectName("CloseButton")
        self.close_button.clicked.connect(self.reject) # Default close action is reject/cancel
        
        title_bar_layout.addWidget(self.title_label)
        title_bar_layout.addStretch()
        title_bar_layout.addWidget(self.close_button)
        main_layout.addWidget(self.title_bar)

        # --- Content Area ---
        # Subclasses will add their widgets to this layout
        self.content_layout = QVBoxLayout()
        self.content_layout.setContentsMargins(15, 15, 15, 15)
        self.content_layout.setSpacing(10)
        main_layout.addLayout(self.content_layout)

    def get_content_layout(self):
        """Returns the layout of the content area for subclass widgets."""
        return self.content_layout

    def setWindowTitle(self, title):
        """Overrides the default setWindowTitle to update our custom label."""
        self.title_label.setText(title)
        super().setWindowTitle(title)

    # --- Drag Logic ---
    def mousePressEvent(self, event):
        # Only start a drag if the click is on the title bar
        if self.title_bar.underMouse():
            self.drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseMoveEvent(self, event):
        # Check if a drag has been initiated
        if not self.drag_pos.isNull():
            self.move(self.pos() + event.globalPosition().toPoint() - self.drag_pos)
            self.drag_pos = event.globalPosition().toPoint()
            event.accept()

    def mouseReleaseEvent(self, event):
        self.drag_pos = QPoint()
        event.accept()