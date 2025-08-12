# main_window/events.py
from PyQt6.QtWidgets import QApplication
from components.docks import ProjectDock
# MODIFIED: Direct import
from components.screen.screen_widget import ScreenWidget
from components.tag_editor_widget import TagEditorWidget

def closeEvent(win, event):
    """Handles the main window's close event, prompting to save if necessary."""
    from . import project_actions, ui_setup
    if project_actions.prompt_to_save_if_dirty(win):
        ui_setup.save_window_state(win)
        event.accept()
    else:
        event.ignore()

def _get_selectable_parent(win, widget):
    """Finds the main selectable widget containing the currently focused widget."""
    current = widget
    while current:
        if isinstance(current, (ProjectDock, ScreenWidget, TagEditorWidget)):
            return current
        current = current.parent()
    return None

def on_focus_changed(win, old, new):
    """Updates UI state based on which widget has gained focus."""
    from . import actions, handlers
    if new is None: return
    new_selectable = _get_selectable_parent(win, new)
    
    if win.last_focused_copypaste_widget and win.last_focused_copypaste_widget != new_selectable:
        if hasattr(win.last_focused_copypaste_widget, 'clear_selection'):
             win.last_focused_copypaste_widget.clear_selection()
    
    win.last_focused_copypaste_widget = new_selectable
    
    project_dock = win.docks['project']

    if new_selectable == project_dock:
        win.active_area_label.setText("Project Explorer")
        handlers.update_selection_status(win, project_dock.get_selected_item_data(), is_tree_item=True)
    elif isinstance(new_selectable, ScreenWidget):
        if new_selectable.design_canvas and new_selectable.design_canvas.screen_data:
            screen_data = new_selectable.design_canvas.screen_data
            win.active_area_label.setText(f"Canvas: {screen_data.get('name', 'Unnamed')}")
        new_selectable.refresh_selection_status()
    elif isinstance(new_selectable, TagEditorWidget):
        win.active_area_label.setText(f"Tag Editor: {new_selectable.db_name}")
    else:
        win.active_area_label.setText("None")
        handlers.update_selection_status(win, None)
    
    actions.update_edit_actions(win)
