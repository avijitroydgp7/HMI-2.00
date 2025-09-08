# main_window/window.py
# The core MainWindow class, which orchestrates all UI components and services.

from PyQt6.QtWidgets import QMainWindow, QStackedWidget, QTabWidget, QDockWidget
from PyQt6.QtCore import Qt, pyqtSignal
from functools import partial

from components.ribbon import Ribbon
from components.toolbar import QuickAccessToolBar, ToolsToolbar
from components.docks import create_docks
from components.welcome_widget import WelcomeWidget
# Import ScreenWidget to check the type of the current tab
from components.screen.screen_widget import ScreenWidget
from services.project_service import project_service
from services.command_history_service import command_history_service
from services.settings_service import settings_service
from utils import constants

from . import ui_setup, actions, project_actions, tabs, events


class MainWindow(QMainWindow):
    """
    The main application window. This class is responsible for initializing the UI,
    connecting signals to slots, and managing the overall application state.
    """

    screen_detached = pyqtSignal(object)
    screen_reattached = pyqtSignal(object)
    def __init__(self, initial_project_path=None):
        super().__init__()
        
        self.open_screen_tabs = {}
        self.open_tag_tabs = {}
        self.open_comment_tabs = {}
        self.last_focused_copypaste_widget = None
        self.active_tool = constants.ToolType.SELECT

        ui_setup.setup_window(self)


        self.central_stacked_widget = QStackedWidget()
        self.welcome_widget = WelcomeWidget()
        self.tab_widget = QTabWidget()
        self.tab_widget.setObjectName("DocumentTabWidget")
        self.tab_widget.setTabsClosable(True)
        self.tab_widget.setMovable(True)
        self.tab_widget.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.central_stacked_widget.addWidget(self.welcome_widget)
        self.central_stacked_widget.addWidget(self.tab_widget)
        self.setCentralWidget(self.central_stacked_widget)

        self.quick_access_toolbar = QuickAccessToolBar(self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.quick_access_toolbar)
        
        self.ribbon = Ribbon(self)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, self.ribbon)
        
        self.tools_toolbar = ToolsToolbar(self)
        self.addToolBar(Qt.ToolBarArea.LeftToolBarArea, self.tools_toolbar)

        self.docks = create_docks(self)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.docks['project'])
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.docks['system'])
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.docks['screens'])
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self.docks['properties'])
        
        self.tabifyDockWidget(self.docks['project'], self.docks['system'])
        self.tabifyDockWidget(self.docks['system'], self.docks['screens'])
        self.docks['project'].raise_()

        actions.create_actions(self)
        ui_setup.setup_status_bar(self)
        ui_setup.setup_view_actions(self)
        ui_setup.restore_window_state(self)
        
        self._connect_signals()
        
        if initial_project_path:
            project_actions.load_project(self, initial_project_path)
        
        tabs.update_central_widget(self)
        self.update_window_title()
        actions.update_edit_actions(self)


    def set_active_tool(self, tool_name):

        """
        Sets the active tool for the application and informs the current canvas.
        """
        self.active_tool = tool_name
        # Inform the active canvas about the tool change.
        current_widget = self.tab_widget.currentWidget()
        if isinstance(current_widget, ScreenWidget):
            current_widget.set_active_tool(tool_name)

    def revert_to_select_tool(self):
        self.tools_toolbar.set_active_tool(constants.ToolType.SELECT)
        self.set_active_tool(constants.ToolType.SELECT)
        self.docks['properties'].widget().set_active_tool(constants.ToolType.SELECT)

    def on_tools_toolbar_tool_changed(self, tool_name: str):
        """Handle selection from the tools toolbar."""
        self.set_active_tool(tool_name)


    def on_cut(self):
        from . import clipboard
        clipboard.cut_item(self)
        actions.update_edit_actions(self)

    def on_copy(self):
        from . import clipboard
        clipboard.copy_item(self)
        actions.update_edit_actions(self)

    def on_paste(self):
        from . import clipboard
        clipboard.paste_item(self)
        actions.update_edit_actions(self)

    def _connect_signals(self):
        """Connect all UI signals, grouped by functional area.

        Uses small helper methods and mapping lists to keep this method concise.
        """
        from PyQt6.QtWidgets import QApplication
        from . import events, tabs, project_actions, handlers
        from services.screen_data_service import screen_service
        from services.tag_data_service import tag_data_service

        # Helper to bulk-connect a list of (signal, handler) pairs
        def bulk_connect(pairs):
            for sig, handler in pairs:
                sig.connect(handler)

        # Application focus and data-service updates
        bulk_connect([
            (QApplication.instance().focusChanged, partial(events.on_focus_changed, self)),
            (screen_service.screen_list_changed, partial(handlers.on_screen_data_changed, self)),
            (tag_data_service.database_list_changed, partial(handlers.on_database_list_changed, self)),
            (command_history_service.history_changed, partial(actions.update_undo_redo_actions, self)),
        ])
        project_service.project_state_changed.connect(self.update_window_title)
        bulk_connect([
            (project_service.project_loaded, partial(tabs.update_central_widget, self)),
            (project_service.project_closed, partial(tabs.update_central_widget, self)),
        ])

        # Tab widget + window screen attach/detach
        bulk_connect([
            (self.tab_widget.tabCloseRequested, partial(tabs.close_tab, self)),
            (self.tab_widget.currentChanged, partial(tabs.on_tab_changed, self)),
            (self.tab_widget.customContextMenuRequested, partial(tabs.show_tab_context_menu, self)),
            (self.screen_detached, partial(tabs.focus_detached_screen, self)),
            (self.screen_reattached, partial(tabs.focus_detached_screen, self)),
        ])

        # Welcome screen actions
        bulk_connect([
            (self.welcome_widget.new_project_requested, partial(project_actions.new_project, self)),
            (self.welcome_widget.open_project_requested, partial(project_actions.open_project, self)),
        ])

        # Project/ribbon/quick-access related actions
        bulk_connect([
            (self.ribbon.new_action.triggered, partial(project_actions.new_project, self)),
            (self.quick_access_toolbar.new_action.triggered, partial(project_actions.new_project, self)),
            (self.ribbon.open_action.triggered, partial(project_actions.open_project, self)),
            (self.quick_access_toolbar.open_action.triggered, partial(project_actions.open_project, self)),
            (self.ribbon.save_action.triggered, partial(project_actions.save_project, self)),
            (self.quick_access_toolbar.save_action.triggered, partial(project_actions.save_project, self)),
            (self.ribbon.save_as_action.triggered, partial(project_actions.save_project_as, self)),
            (self.ribbon.run_action.triggered, partial(project_actions.run_simulator, self)),
            (self.ribbon.close_tab_action.triggered, partial(tabs.close_current_tab, self)),
            (self.ribbon.exit_action.triggered, self.close),
        ])

        # Toolbars and properties linking
        bulk_connect([
            (self.tools_toolbar.tool_changed, self.on_tools_toolbar_tool_changed),
            (self.tools_toolbar.tool_changed, self.docks['properties'].widget().set_active_tool),
        ])

        # Edit actions
        bulk_connect([
            (self.undo_action.triggered, command_history_service.undo),
            (self.redo_action.triggered, command_history_service.redo),
            (self.cut_action.triggered, self.on_cut),
            (self.copy_action.triggered, self.on_copy),
            (self.paste_action.triggered, self.on_paste),
            (self.align_left_action.triggered, partial(actions.align_left, self)),
            (self.align_center_action.triggered, partial(actions.align_center, self)),
            (self.align_right_action.triggered, partial(actions.align_right, self)),
            (self.align_top_action.triggered, partial(actions.align_top, self)),
            (self.align_middle_action.triggered, partial(actions.align_middle, self)),
            (self.align_bottom_action.triggered, partial(actions.align_bottom, self)),
            (self.distribute_h_action.triggered, partial(actions.distribute_horizontally, self)),
            (self.distribute_v_action.triggered, partial(actions.distribute_vertically, self)),
        ])

        # Docks and their widgets
        screens_widget = self.docks['screens'].widget()
        bulk_connect([
            (screens_widget.screen_open_requested, partial(tabs.open_screen_in_tab, self)),
            (screens_widget.selection_changed, partial(actions.update_clipboard_actions, self)),
        ])

        project_dock = self.docks['project']
        bulk_connect([
            (project_dock.tag_database_open_requested, partial(tabs.open_tag_editor_in_tab, self)),
            (project_dock.comment_table_open_requested, partial(tabs.open_comment_table_in_tab, self)),
            (project_dock.project_info_requested, partial(project_actions.edit_project_info, self)),
            (project_dock.tree.itemSelectionChanged, partial(actions.update_clipboard_actions, self)),
            (project_dock.system_tab_requested, self.docks['system'].raise_),
            (project_dock.screens_tab_requested, self.docks['screens'].raise_),
        ])

        # Snapping controls (zoom controls removed)
        bulk_connect([
            (self.snap_objects_cb.toggled, self._on_snap_objects_changed),
            (self.snap_lines_cb.toggled, self._on_snap_lines_visibility_changed),
        ])

    def update_window_title(self): project_actions.update_window_title(self)
    def closeEvent(self, event): events.closeEvent(self, event)

    def _on_snap_objects_changed(self, enabled: bool):
        settings_service.set_value("snap_to_objects", bool(enabled))
        for widget in self.open_screen_tabs.values():
            widget.design_canvas.set_snap_to_objects(enabled)

    def _on_snap_lines_visibility_changed(self, visible: bool):
        settings_service.set_value("snap_lines_visible", bool(visible))
        for widget in self.open_screen_tabs.values():
            widget.design_canvas.set_snap_lines_visible(visible)
