# --- main_window/handlers.py ---
from PyQt6.QtCore import pyqtSlot, QPointF
from services.screen_data_service import screen_service
from services.tag_data_service import tag_data_service

def on_screen_data_changed(win):
    """Updates screen tabs when the underlying screen data changes."""
    from . import tabs
    all_current_screen_ids = screen_service.get_all_screens().keys()
    for screen_id in list(win.open_screen_tabs.keys()):
        if screen_id not in all_current_screen_ids:
            widget_to_close = win.open_screen_tabs.pop(screen_id)
            index = win.tab_widget.indexOf(widget_to_close)
            if index != -1: win.tab_widget.removeTab(index)
    for screen_id, widget in win.open_screen_tabs.items():
        widget.update_screen_data()
        if widget.design_canvas and widget.design_canvas.screen_data:
            screen_data = widget.design_canvas.screen_data
            index = win.tab_widget.indexOf(widget)
            if index != -1:
                tab_title = tabs._format_tab_title(screen_data)
                win.tab_widget.setTabText(index, tab_title)

def on_database_list_changed(win):
    """Closes any tag editor tabs for databases that no longer exist."""
    all_db_ids = tag_data_service.get_all_tag_databases().keys()
    for db_id in list(win.open_tag_tabs.keys()):
        if db_id not in all_db_ids:
            widget_to_close = win.open_tag_tabs.pop(db_id)
            index = win.tab_widget.indexOf(widget_to_close)
            if index != -1:
                win.tab_widget.removeTab(index)

@pyqtSlot(str)
def show_status_bar_message(win, message: str):
    """Displays a message in the status bar for 5 seconds."""
    win.statusBar().showMessage(f"Validation Error: {message}", 5000)

def update_drag_position_status(win, pos_dict):
    x_val = pos_dict.get('x', '--')
    y_val = pos_dict.get('y', '--')
    # Convert to integers if they are numeric values
    if isinstance(x_val, (int, float)):
        x_val = int(x_val)
    if isinstance(y_val, (int, float)):
        y_val = int(y_val)
    win.object_pos_label.setText(f"X {x_val}, Y {y_val}")

def update_selection_status(win, selection_data, is_tree_item=False):
    """
    Correctly updates all status bar labels (pos, size, name) based on the current selection.
    """
    if not selection_data:
        win.object_pos_label.setText("X ----, Y ----")
        win.object_size_label.setText("W ----, H ----")
        win.object_name_label.setText("None")
        return
        
    if is_tree_item:
        win.object_name_label.setText(selection_data.get('name', 'None'))
        win.object_pos_label.setText("X ----, Y ----")
        win.object_size_label.setText("W ----, H ----")
        return

    if isinstance(selection_data, list):
        if not selection_data:
            update_selection_status(win, None)
            return
        if len(selection_data) > 1:
            win.object_name_label.setText("Multiple Items")
            win.object_pos_label.setText("X --, Y --")
            win.object_size_label.setText("W --, H --")
            return
        # If list has one item, proceed as if it's a single item
        selection_data = selection_data[0]

    # Now handle the single selection_data dictionary
    pos = selection_data.get('position', {})
    if 'properties' in selection_data: # It's a tool like a button
        pos = selection_data['properties'].get('position', {})
        size = selection_data['properties'].get('size', {})
        win.object_name_label.setText(selection_data.get('tool_type', 'Object').capitalize())
    elif 'screen_id' in selection_data: # It's an embedded screen
        base_screen = screen_service.get_screen(selection_data['screen_id'])
        size = base_screen.get('size', {}) if base_screen else {}
        name = base_screen.get('name', 'Unnamed') if base_screen else 'Invalid'
        num = base_screen.get('number', '??') if base_screen else '??'
        win.object_name_label.setText(f"[{num}] {name}")
    else: # Should not happen, but as a fallback
        size = {}
        win.object_name_label.setText("Unknown Object")

    # Convert position and size values to integers
    x_val = pos.get('x', '--')
    y_val = pos.get('y', '--')
    width_val = size.get('width', '--')
    height_val = size.get('height', '--')
    
    if isinstance(x_val, (int, float)):
        x_val = int(x_val)
    if isinstance(y_val, (int, float)):
        y_val = int(y_val)
    if isinstance(width_val, (int, float)):
        width_val = int(width_val)
    if isinstance(height_val, (int, float)):
        height_val = int(height_val)
    
    win.object_pos_label.setText(f"X {x_val}, Y {y_val}")
    win.object_size_label.setText(f"W {width_val}, H {height_val}")

def update_mouse_position(win, pos: QPointF):
    win.cursor_pos_label.setText(f"X {int(pos.x())}, Y {int(pos.y())}")

def clear_mouse_position(win):
    win.cursor_pos_label.setText("X ----, Y ----")

def update_zoom_status(win, scale: float):
    try:
        percent = max(1, int(round(scale * 100)))
    except Exception:
        percent = 100
    win.zoom_label.setText(f"{percent}%")
