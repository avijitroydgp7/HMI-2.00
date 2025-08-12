# components/theme_selector.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QComboBox, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from utils.icon_manager import IconManager
from utils.stylesheet_loader import get_available_themes

class ThemeSelectorWidget(QWidget):
    """
    A theme selector widget positioned below the close button
    """
    theme_changed = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("ThemeSelectorWidget")
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        # Create theme combo box
        self.theme_combo = QComboBox(self)
        self.theme_combo.setObjectName("ThemeSelectorCombo")
        self.theme_combo.setFixedWidth(120)
        self.theme_combo.setFont(QFont("Segoe UI", 8))
        
        # Populate themes
        themes = get_available_themes()
        self.theme_combo.addItems(themes)
        
        # Connect signal
        self.theme_combo.currentTextChanged.connect(self.theme_changed)
        
        layout.addWidget(self.theme_combo)
        
    def set_current_theme(self, theme_name):
        """Set the current theme in the combo box"""
        index = self.theme_combo.findText(theme_name)
        if index >= 0:
            self.theme_combo.setCurrentIndex(index)
            
    def get_current_theme(self):
        """Get the current selected theme"""
        return self.theme_combo.currentText()
