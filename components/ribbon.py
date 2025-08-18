# components/ribbon.py
# The main application ribbon (toolbar) for accessing common tools.

from PyQt6.QtWidgets import (
    QToolBar, QWidget, QVBoxLayout, QTabWidget, QHBoxLayout,
    QPushButton, QCheckBox
)
from PyQt6.QtGui import QAction, QIcon, QKeySequence
from PyQt6.QtCore import QSize, Qt, pyqtSignal
from utils.icon_manager import IconManager

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
        self.new_anim = IconManager.create_animated_icon('fa5s.file')
        self.new_action = QAction(self.new_anim.icon, "New", self)
        self.new_anim.add_target(self.new_action)
        self.new_action._animated_icon = self.new_anim
        self.new_action.setShortcut(QKeySequence.StandardKey.New)
        tb.addAction(self.new_action)
        self.open_anim = IconManager.create_animated_icon('fa5s.folder-open')
        self.open_action = QAction(self.open_anim.icon, "Open", self)
        self.open_anim.add_target(self.open_action)
        self.open_action._animated_icon = self.open_anim
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        tb.addAction(self.open_action)
        self.save_anim = IconManager.create_animated_icon('fa5s.save')
        self.save_action = QAction(self.save_anim.icon, "Save", self)
        self.save_anim.add_target(self.save_action)
        self.save_action._animated_icon = self.save_anim
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        tb.addAction(self.save_action)
        self.save_as_anim = IconManager.create_animated_icon('fa5s.save')
        self.save_as_action = QAction(self.save_as_anim.icon, "Save As...", self)
        self.save_as_anim.add_target(self.save_as_action)
        self.save_as_action._animated_icon = self.save_as_anim
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        tb.addAction(self.save_as_action)
        tb.addSeparator()
        self.close_tab_anim = IconManager.create_animated_icon('fa5s.window-close')
        self.close_tab_action = QAction(self.close_tab_anim.icon, "Close Tab", self)
        self.close_tab_anim.add_target(self.close_tab_action)
        self.close_tab_action._animated_icon = self.close_tab_anim
        self.close_tab_action.setShortcut(QKeySequence.StandardKey.Close)
        tb.addAction(self.close_tab_action)
        tb.addSeparator()
        self.exit_anim = IconManager.create_animated_icon('fa5s.sign-out-alt')
        self.exit_action = QAction(self.exit_anim.icon, "Exit", self)
        self.exit_anim.add_target(self.exit_action)
        self.exit_action._animated_icon = self.exit_anim
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
