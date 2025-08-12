# components/welcome_widget.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from utils.icon_manager import IconManager

class WelcomeWidget(QWidget):
    new_project_requested = pyqtSignal()
    open_project_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("WelcomeWidget")

        main_layout = QVBoxLayout(self)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setSpacing(20)

        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title = QLabel("HMI Designer")
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle_font = QFont()
        subtitle_font.setPointSize(11)
        subtitle = QLabel("Create, design, and manage your HMI projects.")
        subtitle.setFont(subtitle_font)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setObjectName("SubtitleLabel")

        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)

        new_button = self._create_action_button(
            "New Project", "Start a new project from scratch.",
            'fa5s.file-alt', self.new_project_requested.emit
        )
        open_button = self._create_action_button(
            "Open Project", "Open an existing project file.",
            'fa5s.folder-open', self.open_project_requested.emit
        )

        button_layout.addWidget(new_button)
        button_layout.addWidget(open_button)

        main_layout.addStretch()
        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)
        main_layout.addSpacing(30)
        main_layout.addLayout(button_layout)
        main_layout.addStretch()

    def _create_action_button(self, title_text, desc_text, icon_name, on_click):
        button = QPushButton()
        button.setFixedSize(220, 100)
        button.setCursor(Qt.CursorShape.PointingHandCursor)
        button.clicked.connect(on_click)

        layout = QVBoxLayout(button)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(10, 10, 10, 10)

        icon_label = QLabel()
        icon_label.setPixmap(IconManager.create_pixmap(icon_name, 24, color="#dbe0e8"))
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        title_label = QLabel(title_text)
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)

        desc_label = QLabel(desc_text)
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setObjectName("SubtitleLabel")

        layout.addWidget(icon_label)
        layout.addWidget(title_label)
        layout.addWidget(desc_label)

        return button
