# components/toolbar.py
from PyQt6.QtWidgets import QToolBar

from PyQt6.QtCore import Qt, QSize, pyqtSignal
from PyQt6.QtGui import QAction, QActionGroup, QKeySequence
from utils.icon_manager import IconManager
from utils import constants

def build_actions(actions_config, toolbar: QToolBar, group: QActionGroup | None = None):
    """Build QActions from a configuration and add them to a toolbar.

    Supports both a flat list of action dicts or a list of lists to create
    grouped actions with separators between groups.

    Each action config may include:
    - name: Text label for the action (required)
    - icon: qtawesome icon name (required)
    - animated: Use animated icon helper (bool, default False)
    - id: Arbitrary data stored via action.setData
    - shortcut: Shortcut string (e.g., "Ctrl+T")
    - standard_shortcut: QKeySequence.StandardKey for platform-specific text
    - apply_shortcut: Whether to apply the shortcut to the action (default True)
    - checkable: Whether the action is checkable (default True if group provided)
    - checked: Initial checked state (bool)
    - triggered: Optional callable connected to action.triggered

    Returns a flat list of created QActions in creation order.
    """

    def _process_group(items):
        created = []
        icon_sz = toolbar.iconSize().width()
        for cfg in items:
            if isinstance(cfg, dict) and cfg.get("separator", False):
                toolbar.addSeparator()
                continue

            name = cfg.get("name", "")
            icon_name = cfg.get("icon")
            if not icon_name:
                continue

            if cfg.get("animated", False):
                anim = IconManager.create_animated_icon(icon_name, size=icon_sz)
                action = QAction(anim.icon, name, toolbar)
                anim.add_target(action)
                # Keep a reference to prevent GC
                action._animated_icon = anim  # type: ignore[attr-defined]
            else:
                action = QAction(IconManager.create_icon(icon_name, size=icon_sz), name, toolbar)

            # Shortcut handling and tooltip text
            apply_shortcut = cfg.get("apply_shortcut", True)
            shortcut_text = cfg.get("tooltip_shortcut_text")
            std_key = cfg.get("standard_shortcut")
            shortcut = cfg.get("shortcut")

            if apply_shortcut:
                if shortcut:
                    action.setShortcut(shortcut)
                elif std_key is not None:
                    action.setShortcut(QKeySequence(std_key))

            if shortcut_text is None:
                if shortcut:
                    shortcut_text = shortcut
                elif std_key is not None:
                    shortcut_text = QKeySequence(std_key).toString()

            if shortcut_text:
                action.setToolTip(f"{name} ({shortcut_text})")
            else:
                action.setToolTip(name)

            # Checkable state
            checkable_default = group is not None
            if cfg.get("checkable", checkable_default):
                action.setCheckable(True)
                if cfg.get("checked", False):
                    action.setChecked(True)

            # Data payload
            if "id" in cfg:
                action.setData(cfg["id"])

            # Optional per-action signal wiring
            on_triggered = cfg.get("triggered")
            if callable(on_triggered):
                action.triggered.connect(on_triggered)

            # Add to group and toolbar
            if group is not None:
                group.addAction(action)
            toolbar.addAction(action)
            created.append(action)
        return created

    created_actions: list[QAction] = []
    if isinstance(actions_config, list) and actions_config and isinstance(actions_config[0], list):
        for i, grp in enumerate(actions_config):
            created_actions.extend(_process_group(grp))
            if i < len(actions_config) - 1:
                toolbar.addSeparator()
    else:
        created_actions.extend(_process_group(actions_config or []))

    return created_actions

class QuickAccessToolBar(QToolBar):
    """A customizable toolbar for frequently used actions, typically at the top
    of the window."""

    def __init__(self, parent=None):
        super().__init__("Quick Access", parent)
        self.setObjectName("QuickAccessToolBar")
        self.setMovable(True)
        self.setIconSize(QSize(20, 20))

        # Do not set shortcuts here to avoid duplicates with Ribbon actions
        qa_config = [
            {
                "name": "New",
                "icon": "fa5s.file",
                "animated": True,
                "standard_shortcut": QKeySequence.StandardKey.New,
                "apply_shortcut": False,
            },
            {
                "name": "Open",
                "icon": "fa5s.folder-open",
                "animated": True,
                "standard_shortcut": QKeySequence.StandardKey.Open,
                "apply_shortcut": False,
            },
            {
                "name": "Save",
                "icon": "fa5s.save",
                "animated": True,
                "standard_shortcut": QKeySequence.StandardKey.Save,
                "apply_shortcut": False,
            },
        ]

        actions = build_actions(qa_config, self)
        # Keep explicit handles used elsewhere in the app
        self.new_action, self.open_action, self.save_action = actions
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

        build_actions(tools, self, group=self._action_group)

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

        build_actions(tool_groups, self, group=self._action_group)

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
