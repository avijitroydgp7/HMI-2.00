# components/toolbar.py
from PyQt6.QtWidgets import QToolBar

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QKeySequence
from utils.icon_manager import IconManager
from utils import constants

class QuickAccessToolBar(QToolBar):
    """A customizable toolbar for frequently used actions, typically at the top
    of the window."""

    def __init__(self, parent=None):
        super().__init__("Quick Access", parent)
        self.setObjectName("QuickAccessToolBar")
        self.setMovable(True)
        self.setIconSize(QSize(20, 20))

        icon_sz = self.iconSize().width()
        self.new_icon = IconManager.create_animated_icon('fa5s.file', size=icon_sz)
        self.new_action = QAction(self.new_icon.icon, "New", self)
        self.new_icon.add_target(self.new_action)
        self.new_action._animated_icon = self.new_icon
        self.new_action.setShortcut(QKeySequence.StandardKey.New)
        self.new_action.setToolTip(f"New ({self.new_action.shortcut().toString()})")
        self.open_icon = IconManager.create_animated_icon('fa5s.folder-open', size=icon_sz)
        self.open_action = QAction(self.open_icon.icon, "Open", self)
        self.open_icon.add_target(self.open_action)
        self.open_action._animated_icon = self.open_icon
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.setToolTip(f"Open ({self.open_action.shortcut().toString()})")
        self.save_icon = IconManager.create_animated_icon('fa5s.save', size=icon_sz)
        self.save_action = QAction(self.save_icon.icon, "Save", self)
        self.save_icon.add_target(self.save_action)
        self.save_action._animated_icon = self.save_icon
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.setToolTip(f"Save ({self.save_action.shortcut().toString()})")

        self.addAction(self.new_action)
        self.addAction(self.open_action)
        self.addAction(self.save_action)
        self.addSeparator()

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
            {"id": constants.TOOL_BUTTON, "name": "Button Tool", "icon": "mdi.gesture-tap-box", "shortcut": "B", "checked": False},
        ]

        icon_sz = self.iconSize().width()
        for tool in tools:
            action = QAction(IconManager.create_icon(tool["icon"], size=icon_sz), tool["name"], self)
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

    def clear_selection(self):
        """Clears any active tool selection."""
        for action in self._action_group.actions():
            action.setChecked(False)

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

        tool_groups = [
            [
                {"id": constants.TOOL_LINE, "name": "Line Tool", "icon": "fa5s.slash", "shortcut": "L"},
                {"id": constants.TOOL_FREEFORM, "name": "Freeform Tool", "icon": "fa5s.pencil-alt", "shortcut": "F"},
            ],
            [
                {"id": constants.TOOL_RECT, "name": "Rectangle Tool", "icon": "fa5.square", "shortcut": "R"},
                {"id": constants.TOOL_POLYGON, "name": "Polygon Tool", "icon": "fa5s.draw-polygon", "shortcut": "P"},
                {"id": constants.TOOL_CIRCLE, "name": "Circle Tool", "icon": "fa5s.circle", "shortcut": "C"},
                {"id": constants.TOOL_ARC, "name": "Arc Tool", "icon": "fa5s.circle-notch", "shortcut": "A"},
                {"id": constants.TOOL_SECTOR, "name": "Sector Tool", "icon": "fa5s.chart-pie", "shortcut": "S"},
            ],
            [
                {"id": constants.TOOL_TEXT, "name": "Text Tool", "icon": "fa5s.font", "shortcut": "T"},
                {"id": constants.TOOL_TABLE, "name": "Table Tool", "icon": "fa5s.table", "shortcut": "Ctrl+T"},
                {"id": constants.TOOL_SCALE, "name": "Scale Tool", "icon": "fa5s.ruler-combined", "shortcut": "K"},
            ],
            [
                {"id": constants.TOOL_IMAGE, "name": "Image Tool", "icon": "fa5s.image", "shortcut": "I"},
                {"id": constants.TOOL_DXF, "name": "DXF Tool", "icon": "fa5s.file-import", "shortcut": "D"},
            ],
        ]

        icon_sz = self.iconSize().width()
        for i, group in enumerate(tool_groups):
            for tool in group:
                action = QAction(IconManager.create_icon(tool["icon"], size=icon_sz), tool["name"], self)
                action.setToolTip(f"{tool['name']} ({tool['shortcut']})")
                action.setShortcut(tool["shortcut"])
                action.setCheckable(True)
                action.setData(tool["id"])
                self._action_group.addAction(action)
                self.addAction(action)
            if i < len(tool_groups) - 1:
                self.addSeparator()

    def set_active_tool(self, tool_id: str):
        """Programmatically sets the active drawing tool in the toolbar."""
        for action in self._action_group.actions():
            if action.data() == tool_id:
                action.setChecked(True)
                break

    def clear_selection(self):
        """Clears any active drawing tool selection."""
        for action in self._action_group.actions():
            action.setChecked(False)