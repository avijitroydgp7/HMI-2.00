# components/toolbar.py
from PyQt6.QtWidgets import QToolBar, QComboBox, QWidget, QSizePolicy

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup
from utils.icon_manager import IconManager
from utils import constants

class QuickAccessToolBar(QToolBar):
    """
    A customizable toolbar for frequently used actions, typically at the top
    of the window.
    """
    theme_changed = pyqtSignal(str)

    def __init__(self, parent=None):

        super().__init__("Quick Access", parent)
        self.setObjectName("QuickAccessToolBar")
        self.setMovable(True)
        self.setIconSize(QSize(16, 16))

        self.new_action = QAction(IconManager.create_icon('fa5s.file'), "New", self)
        self.open_action = QAction(IconManager.create_icon('fa5s.folder-open'), "Open", self)
        self.save_action = QAction(IconManager.create_icon('fa5s.save'), "Save", self)
        
        self.addAction(self.new_action)
        self.addAction(self.open_action)
        self.addAction(self.save_action)
        self.addSeparator()

    def populate_themes(self, themes, current_theme):
        """Legacy method - themes are now handled elsewhere."""
        pass

    def add_clipboard_actions(self, cut_action, copy_action, paste_action):

        """Adds shared clipboard actions to the toolbar."""
        self.addAction(cut_action)
        self.addAction(copy_action)
        self.addAction(paste_action)
        self.addSeparator()

    def add_undo_redo_actions(self, undo_action, redo_action):
        """Adds shared undo/redo actions to the toolbar."""
        self.addAction(undo_action)
        self.addAction(redo_action)
        self.addSeparator()

    def add_view_action(self, action):
        """Adds a shared view toggle action to the toolbar."""
        self.addAction(action)

class ToolsToolbar(QToolBar):
    """
    A toolbar that provides a selection of design tools.
    """
    tool_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Tools", parent)
        self.setObjectName("ToolsToolbar")
        self.setMovable(True)
        self.setFloatable(True)
        self.setOrientation(Qt.Orientation.Vertical)
        self.setIconSize(QSize(20, 20))
        self._action_group = QActionGroup(self)
        self._create_actions()

    def _create_actions(self):
        """Creates the tool actions and adds them to the toolbar."""
        self._action_group.setExclusive(True)
        self._action_group.triggered.connect(lambda action: self.tool_changed.emit(action.data()))

        tools = [
            {"id": constants.TOOL_SELECT, "name": "Select Tool", "icon": "fa5s.mouse-pointer", "shortcut": "V", "checked": True},
            {"id": constants.TOOL_BUTTON, "name": "Button Tool", "icon": "fa5s.hand-pointer", "shortcut": "B", "checked": False},
        ]

        for tool in tools:
            action = QAction(IconManager.create_icon(tool["icon"]), tool["name"], self)
            action.setToolTip(f"{tool['name']} ({tool['shortcut']})")
            action.setShortcut(tool["shortcut"])
            action.setCheckable(True)
            action.setChecked(tool["checked"])
            action.setData(tool["id"])
            self._action_group.addAction(action)
            self.addAction(action)

    def set_active_tool(self, tool_id: str):
        """Programmatically sets the active tool in the toolbar."""
        for action in self._action_group.actions():
            if action.data() == tool_id:
                action.setChecked(True)
                break


class DrawingToolbar(QToolBar):
    """A toolbar dedicated to drawing tools."""

    tool_changed = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__("Drawing", parent)
        self.setObjectName("DrawingToolbar")
        self.setMovable(True)
        self.setFloatable(True)
        self.setOrientation(Qt.Orientation.Vertical)
        self.setIconSize(QSize(20, 20))
        self._action_group = QActionGroup(self)
        self._create_actions()

    def _create_actions(self):
        """Creates the drawing tool actions and adds them to the toolbar."""
        self._action_group.setExclusive(True)
        self._action_group.triggered.connect(lambda action: self.tool_changed.emit(action.data()))

        tools = [
            {"id": constants.TOOL_LINE, "name": "Line Tool", "icon": "fa5s.minus", "shortcut": "L"},
            {"id": constants.TOOL_FREEFORM, "name": "Freeform Tool", "icon": "fa5s.pencil-alt", "shortcut": "F"},
            {"id": constants.TOOL_RECT, "name": "Rectangle Tool", "icon": "fa5s.square", "shortcut": "R"},
            {"id": constants.TOOL_POLYGON, "name": "Polygon Tool", "icon": "fa5s.draw-polygon", "shortcut": "P"},
            {"id": constants.TOOL_CIRCLE, "name": "Circle Tool", "icon": "fa5s.circle", "shortcut": "C"},
            {"id": constants.TOOL_ARC, "name": "Arc Tool", "icon": "fa5s.circle-notch", "shortcut": "A"},
            {"id": constants.TOOL_SECTOR, "name": "Sector Tool", "icon": "fa5s.chart-pie", "shortcut": "S"},
            {"id": constants.TOOL_TEXT, "name": "Text Tool", "icon": "fa5s.font", "shortcut": "T", "checked": False},
            {"id": constants.TOOL_TABLE, "name": "Table Tool", "icon": "fa5s.table", "shortcut": "Ctrl+T", "checked": False},
            {"id": constants.TOOL_SCALE, "name": "Scale Tool", "icon": "fa5s.ruler-combined", "shortcut": "K", "checked": False},
            {"id": constants.TOOL_IMAGE, "name": "Image Tool", "icon": "fa5s.image", "shortcut": "I", "checked": False},
            {"id": constants.TOOL_DXF, "name": "DXF Tool", "icon": "fa5s.file-import", "shortcut": "D", "checked": False},
        ]

        for tool in tools:
            action = QAction(IconManager.create_icon(tool["icon"]), tool["name"], self)
            action.setToolTip(f"{tool['name']} ({tool['shortcut']})")
            action.setShortcut(tool["shortcut"])
            action.setCheckable(True)
            action.setData(tool["id"])
            self._action_group.addAction(action)
            self.addAction(action)

    def set_active_tool(self, tool_id: str):
        """Programmatically sets the active drawing tool in the toolbar."""
        for action in self._action_group.actions():
            if action.data() == tool_id:
                action.setChecked(True)
                break