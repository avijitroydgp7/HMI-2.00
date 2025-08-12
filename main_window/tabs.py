# main_window/tabs.py
# MODIFIED: Ensures the active tool is set when a tab is changed.

from PyQt6.QtWidgets import QMenu, QMessageBox
from components.screen.screen_widget import ScreenWidget
from components.tag_editor_widget import TagEditorWidget
from services.screen_data_service import screen_service
from services.tag_data_service import tag_data_service
from services.project_service import project_service

def update_central_widget(win):
    if project_service.is_project_open():
        win.central_stacked_widget.setCurrentWidget(win.tab_widget)
    else:
        win.central_stacked_widget.setCurrentWidget(win.welcome_widget)

def close_current_tab(win):
    index = win.tab_widget.currentIndex()
    if index != -1:
        close_tab(win, index)

def close_tab(win, index):
    widget = win.tab_widget.widget(index)
    if isinstance(widget, ScreenWidget):
        if widget.screen_id in win.open_screen_tabs:
            del win.open_screen_tabs[widget.screen_id]
    elif isinstance(widget, TagEditorWidget):
        if widget.db_id in win.open_tag_tabs:
            del win.open_tag_tabs[widget.db_id]
    win.tab_widget.removeTab(index)

def _close_all_tabs(win):
    while win.tab_widget.count() > 0:
        close_tab(win, 0)

def show_tab_context_menu(win, position):
    index = win.tab_widget.tabBar().tabAt(position)
    if index == -1: return
    menu = QMenu()
    close_action = menu.addAction("Close")
    close_others_action = menu.addAction("Close Others")
    close_all_action = menu.addAction("Close All")
    menu.addSeparator()
    close_right_action = menu.addAction("Close Tabs to the Right")
    close_left_action = menu.addAction("Close Tabs to the Left")
    
    if win.tab_widget.count() <= 1: close_others_action.setEnabled(False)
    if index == win.tab_widget.count() - 1: close_right_action.setEnabled(False)
    if index == 0: close_left_action.setEnabled(False)
    
    action = menu.exec(win.tab_widget.mapToGlobal(position))
    if action == close_action: close_tab(win, index)
    elif action == close_others_action: _close_other_tabs(win, index)
    elif action == close_all_action: _close_all_tabs(win)
    elif action == close_right_action: _close_tabs_to_right(win, index)
    elif action == close_left_action: _close_tabs_to_left(win, index)

def _close_other_tabs(win, index_to_keep):
    for i in range(win.tab_widget.count() - 1, -1, -1):
        if i != index_to_keep: close_tab(win, i)

def _close_tabs_to_right(win, index):
    for i in range(win.tab_widget.count() - 1, index, -1): close_tab(win, i)

def _close_tabs_to_left(win, index):
    for _ in range(index): close_tab(win, 0)

def _format_tab_title(screen_data):
    if not screen_data: return "Invalid Screen"
    type_char = screen_data.get('type', '?')[0].upper()
    number = screen_data.get('number', '??')
    name = screen_data.get('name', 'Unnamed')
    return f"[{type_char}] - [{number}] - {name}"

def open_screen_in_tab(win, screen_id):
    from . import actions, handlers
    if screen_id in win.open_screen_tabs:
        win.tab_widget.setCurrentWidget(win.open_screen_tabs[screen_id])
        return
    screen_data = screen_service.get_screen(screen_id)
    if not screen_data:
        QMessageBox.critical(win, "Error", f"Could not find screen data for ID: {screen_id}")
        return
    
    screen_widget = ScreenWidget(screen_id, win)
    screen_widget.selection_changed.connect(win.docks['properties'].widget().set_current_object)
    screen_widget.selection_changed.connect(lambda: actions.update_clipboard_actions(win))
    screen_widget.selection_changed.connect(lambda p_id, s_data: handlers.update_selection_status(win, s_data))
    
    screen_widget.selection_dragged.connect(lambda pos: handlers.update_drag_position_status(win, pos))
    screen_widget.mouse_moved_on_scene.connect(lambda pos: handlers.update_mouse_position(win, pos))
    screen_widget.mouse_left_scene.connect(lambda: handlers.clear_mouse_position(win))
    
    screen_widget.zoom_changed.connect(win.zoom_level_label.setText)
    screen_widget.open_screen_requested.connect(lambda sid: open_screen_in_tab(win, sid))
    
    tab_title = _format_tab_title(screen_data)
    tab_index = win.tab_widget.addTab(screen_widget, tab_title)
    win.tab_widget.setCurrentIndex(tab_index)
    win.open_screen_tabs[screen_id] = screen_widget

def open_tag_editor_in_tab(win, db_id: str):
    from . import actions, handlers
    if db_id in win.open_tag_tabs:
        win.tab_widget.setCurrentWidget(win.open_tag_tabs[db_id])
        return
    db_data = tag_data_service.get_tag_database(db_id)
    if not db_data:
        QMessageBox.critical(win, "Error", f"Could not find tag database with ID: {db_id}")
        return
        
    db_name = db_data.get('name', 'Unnamed DB')
    editor_widget = TagEditorWidget(db_id, db_name, win)
    editor_widget.validation_error_occurred.connect(lambda msg: handlers.show_status_bar_message(win, msg))
    editor_widget.selection_changed.connect(lambda: actions.update_clipboard_actions(win))
    
    tab_title = f"Tags: {db_name}"
    tab_index = win.tab_widget.addTab(editor_widget, tab_title)
    win.tab_widget.setCurrentIndex(tab_index)
    win.open_tag_tabs[db_id] = editor_widget

def on_tab_changed(win, index):
    from . import handlers, actions
    screen_manager = win.docks['screens'].widget()
    widget = win.tab_widget.widget(index)
    
    if isinstance(widget, ScreenWidget):
        widget.setFocus()
        # MODIFIED: Set the active tool when the tab is focused
        widget.set_active_tool(win.active_tool)
        win.zoom_level_label.setText(widget.get_zoom_percentage())
        screen_manager.update_active_screen_highlight(widget.screen_id)
        if widget.design_canvas and widget.design_canvas.screen_data:
            size = widget.design_canvas.screen_data.get('size', {})
            win.screen_dim_label.setText(f"W {size.get('width', '----')}, H {size.get('height', '----')}")
        else:
            win.screen_dim_label.setText("W ----, H ----")
        widget.refresh_selection_status()
    elif isinstance(widget, TagEditorWidget):
        widget.tag_tree.setFocus()
        win.screen_dim_label.setText("W ----, H ----")
        win.object_size_label.setText("W ----, H ----")
        win.object_pos_label.setText("X ----, Y ----")
        handlers.clear_mouse_position(win)
        win.zoom_level_label.setText("---%")
        screen_manager.update_active_screen_highlight(None)
        win.docks['properties'].widget().set_current_object(None, None)
    else:
        if project_service.is_project_open():
            screen_manager.tree.setFocus()
        win.screen_dim_label.setText("W ----, H ----")
        win.object_size_label.setText("W ----, H ----")
        win.object_pos_label.setText("X ----, Y ----")
        handlers.clear_mouse_position(win)
        win.zoom_level_label.setText("---%")
        screen_manager.update_active_screen_highlight(None)
        win.docks['properties'].widget().set_current_object(None, None)
        
    actions.update_edit_actions(win)
