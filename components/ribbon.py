# components/ribbon.py
# The main application ribbon (toolbar) for accessing common tools.

from PyQt6.QtWidgets import (
    QToolBar, QWidget, QVBoxLayout, QTabWidget, QHBoxLayout, QLabel, 
    QPushButton, QSpinBox, QCheckBox, QComboBox
)
from PyQt6.QtGui import QAction, QIcon, QKeySequence
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from utils.icon_manager import IconManager
from utils.stylesheet_loader import get_available_themes

class RibbonTab(QWidget):
    """A single tab within the ribbon."""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.toolbar = QToolBar()
        self.toolbar.setIconSize(QSize(24, 24))
        self.toolbar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.toolbar)

class Ribbon(QToolBar):
    """
    The main tabbed ribbon for the application.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("MainRibbon")
        self.setMovable(False)
        self.setFloatable(False)
        self.setIconSize(QSize(16, 16))

        self.tab_widget = QTabWidget()
        font = self.tab_widget.font()
        font.setPointSize(8)
        self.tab_widget.setFont(font)
        self.addWidget(self.tab_widget)

        # --- Create Tabs ---
        self.project_tab = RibbonTab()
        self.edit_tab = RibbonTab()
        self.search_tab = RibbonTab()
        self.view_tab = RibbonTab()
        self.common_tab = RibbonTab()
        self.figure_tab = RibbonTab()
        self.object_tab = RibbonTab()
        self.comm_tab = RibbonTab()

        # --- Add Tabs to Widget ---
        self.tab_widget.addTab(self.project_tab, "Project")
        self.tab_widget.addTab(self.edit_tab, "Edit")
        self.tab_widget.addTab(self.search_tab, "Search/Replace")
        self.tab_widget.addTab(self.view_tab, "View")
        self.tab_widget.addTab(self.common_tab, "Common")
        self.tab_widget.addTab(self.figure_tab, "Figure")
        self.tab_widget.addTab(self.object_tab, "Object")
        self.tab_widget.addTab(self.comm_tab, "Communication")

        self._populate_project_tab()
        # The view tab is now populated just by adding actions to it.

    def _populate_project_tab(self):
        tb = self.project_tab.toolbar
        self.new_action = QAction(IconManager.create_icon('fa5s.file'), "New", self)
        self.new_action.setShortcut(QKeySequence.StandardKey.New)
        tb.addAction(self.new_action)
        self.open_action = QAction(IconManager.create_icon('fa5s.folder-open'), "Open", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        tb.addAction(self.open_action)
        self.save_action = QAction(IconManager.create_icon('fa5s.save'), "Save", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        tb.addAction(self.save_action)
        self.save_as_action = QAction(IconManager.create_icon('fa5s.save'), "Save As...", self)
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        tb.addAction(self.save_as_action)
        tb.addSeparator()
        self.close_tab_action = QAction(IconManager.create_icon('fa5s.window-close'), "Close Tab", self)
        self.close_tab_action.setShortcut(QKeySequence.StandardKey.Close)
        tb.addAction(self.close_tab_action)
        tb.addSeparator()
        self.exit_action = QAction(IconManager.create_icon('fa5s.sign-out-alt'), "Exit", self)
        self.exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        tb.addAction(self.exit_action)

    def add_clipboard_actions(self, cut_action, copy_action, paste_action):
        """Adds the centralized clipboard actions to the Edit tab."""
        self.edit_tab.toolbar.addAction(cut_action)
        self.edit_tab.toolbar.addAction(copy_action)
        self.edit_tab.toolbar.addAction(paste_action)
        self.edit_tab.toolbar.addSeparator()

    def add_undo_redo_actions(self, undo_action, redo_action):
        """Adds the centralized undo/redo actions to the Edit tab."""
        self.edit_tab.toolbar.addAction(undo_action)
        self.edit_tab.toolbar.addAction(redo_action)

    def add_view_action(self, action: QAction):
        """Adds a shared view action to the View tab's toolbar."""
        self.view_tab.toolbar.addAction(action)

    def populate_theme_selector(self, themes, current_theme, on_theme_changed):
        """Adds a theme selector to the View tab."""
        # Add separator
        self.view_tab.toolbar.addSeparator()
        
        # Add label
        label = QLabel("Theme:")
        self.view_tab.toolbar.addWidget(label)
        
        # Create theme combo box
        self.theme_combo = QComboBox()
        self.theme_combo.setObjectName("RibbonThemeSelector")
        self.theme_combo.setFixedWidth(120)
        self.theme_combo.addItems(themes)
        
        # Set current theme
        if current_theme in themes:
            self.theme_combo.setCurrentText(current_theme)
            
        # Connect signal
        self.theme_combo.currentTextChanged.connect(on_theme_changed)
        
        self.view_tab.toolbar.addWidget(self.theme_combo)
