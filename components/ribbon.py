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
        self.new_action, self.new_anim = self._create_action('fa5s.file', "New", QKeySequence.StandardKey.New)
        tb.addAction(self.new_action)
        self.open_action, self.open_anim = self._create_action('fa5s.folder-open', "Open", QKeySequence.StandardKey.Open)
        tb.addAction(self.open_action)
        self.save_action, self.save_anim = self._create_action('fa5s.save', "Save", QKeySequence.StandardKey.Save)
        tb.addAction(self.save_action)
        self.save_as_action, self.save_as_anim = self._create_action('fa5s.save', "Save As...", QKeySequence.StandardKey.SaveAs)
        tb.addAction(self.save_as_action)
        # Run (launch simulator)
        self.run_action, self.run_anim = self._create_action('fa5s.play', "Run", QKeySequence("F5"))
        tb.addAction(self.run_action)
        tb.addSeparator()
        self.close_tab_action, self.close_tab_anim = self._create_action('fa5s.window-close', "Close Tab", QKeySequence.StandardKey.Close)
        tb.addAction(self.close_tab_action)
        tb.addSeparator()
        self.exit_action, self.exit_anim = self._create_action('fa5s.sign-out-alt', "Exit", QKeySequence.StandardKey.Quit)
        tb.addAction(self.exit_action)

    def _create_action(self, icon_name, text, shortcut=None):
        """
        Create a QAction with an animated icon and optional shortcut.

        Parameters:
        - icon_name: qtawesome icon name (e.g., 'fa5s.file') or a path to an animated
          image (GIF/APNG). Passed to IconManager.create_animated_icon.
        - text: Action label shown in the UI.
        - shortcut: Optional keyboard shortcut. Accepts QKeySequence,
          QKeySequence.StandardKey, or a string like 'F5'.

        Returns:
        (QAction, AnimatedIcon): The configured action and its AnimatedIcon.
        The AnimatedIcon is also attached to the action as "_animated_icon" to
        keep the animation alive.
        """
        anim = IconManager.create_animated_icon(icon_name)
        action = QAction(anim.icon, text, self)
        anim.add_target(action)
        action._animated_icon = anim  # keep reference alive
        if shortcut is not None:
            if isinstance(shortcut, str):
                action.setShortcut(QKeySequence(shortcut))
            else:
                action.setShortcut(shortcut)
        return action, anim

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
