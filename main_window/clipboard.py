# --- main_window/clipboard.py ---
# MODIFIED: Removed local imports and calls to actions.update_edit_actions
# The main window will now be responsible for updating the action states.

def cut_item(win):
    """Triggers the 'cut' action on the currently focused widget."""
    if win.last_focused_copypaste_widget and hasattr(win.last_focused_copypaste_widget, 'cut_selected'):
        win.last_focused_copypaste_widget.cut_selected()

def copy_item(win):
    """Triggers the 'copy' action on the currently focused widget."""
    if win.last_focused_copypaste_widget and hasattr(win.last_focused_copypaste_widget, 'copy_selected'):
        win.last_focused_copypaste_widget.copy_selected()

def paste_item(win):
    """Triggers the 'paste' action on the currently focused widget."""
    if win.last_focused_copypaste_widget and hasattr(win.last_focused_copypaste_widget, 'paste'):
        win.last_focused_copypaste_widget.paste()
