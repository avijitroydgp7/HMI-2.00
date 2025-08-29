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
        # Do not set shortcuts here to avoid duplicates with Ribbon actions
        new_sc_text = QKeySequence(QKeySequence.StandardKey.New).toString()
        self.new_action.setToolTip(f"New ({new_sc_text})")
        self.open_icon = IconManager.create_animated_icon('fa5s.folder-open', size=icon_sz)
        self.open_action = QAction(self.open_icon.icon, "Open", self)
        self.open_icon.add_target(self.open_action)
        self.open_action._animated_icon = self.open_icon
        open_sc_text = QKeySequence(QKeySequence.StandardKey.Open).toString()
        self.open_action.setToolTip(f"Open ({open_sc_text})")
        self.save_icon = IconManager.create_animated_icon('fa5s.save', size=icon_sz)
        self.save_action = QAction(self.save_icon.icon, "Save", self)
        self.save_icon.add_target(self.save_action)
        self.save_action._animated_icon = self.save_icon
        save_sc_text = QKeySequence(QKeySequence.StandardKey.Save).toString()
        self.save_action.setToolTip(f"Save ({save_sc_text})")

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
            {"id": constants.ToolType.SELECT, "name": "Select Tool", "icon": "fa5s.mouse-pointer", "shortcut": "V", "checked": True},
            {"id": constants.ToolType.PATH_EDIT, "name": "Path Edit Tool", "icon": "fa5s.edit", "shortcut": "E", "checked": False},
            {"id": constants.ToolType.BUTTON, "name": "Button Tool", "icon": "mdi.gesture-tap-box", "shortcut": "B", "checked": False},
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

    def set_active_tool(self, tool_id):
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
                {"id": constants.ToolType.LINE, "name": "Line Tool", "icon": "fa5s.slash", "shortcut": "L"},
                {"id": constants.ToolType.FREEFORM, "name": "Freeform Tool", "icon": "fa5s.pencil-alt", "shortcut": "F"},
            ],
            [
                {"id": constants.ToolType.RECT, "name": "Rectangle Tool", "icon": "fa5.square", "shortcut": "R"},
                {"id": constants.ToolType.POLYGON, "name": "Polygon Tool", "icon": "fa5s.draw-polygon", "shortcut": "P"},
                {"id": constants.ToolType.CIRCLE, "name": "Circle Tool", "icon": "fa5s.circle", "shortcut": "C"},
                {"id": constants.ToolType.ARC, "name": "Arc Tool", "icon": "fa5s.circle-notch", "shortcut": "A"},
                {"id": constants.ToolType.SECTOR, "name": "Sector Tool", "icon": "fa5s.chart-pie", "shortcut": "S"},
            ],
            [
                {"id": constants.ToolType.TEXT, "name": "Text Tool", "icon": "fa5s.font", "shortcut": "T"},
                {"id": constants.ToolType.TABLE, "name": "Table Tool", "icon": "fa5s.table", "shortcut": "Ctrl+T"},
                {"id": constants.ToolType.SCALE, "name": "Scale Tool", "icon": "fa5s.ruler-combined", "shortcut": "K"},
            ],
            [
                {"id": constants.ToolType.IMAGE, "name": "Image Tool", "icon": "fa5s.image", "shortcut": "I"},
                {"id": constants.ToolType.DXF, "name": "DXF Tool", "icon": "fa5s.file-import", "shortcut": "D"},
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

    def set_active_tool(self, tool_id):
        """Programmatically sets the active drawing tool in the toolbar."""
        for action in self._action_group.actions():
            if action.data() == tool_id:
                action.setChecked(True)
                break

    def clear_selection(self):
        """Clears any active drawing tool selection."""
        for action in self._action_group.actions():
            action.setChecked(False)
