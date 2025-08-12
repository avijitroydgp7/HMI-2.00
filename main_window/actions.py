# main_window/actions.py
from PyQt6.QtGui import QAction, QKeySequence
from utils.icon_manager import IconManager
from services.command_history_service import command_history_service
from services.clipboard_service import clipboard_service
from components.docks import ProjectDock
from components.screen.screen_widget import ScreenWidget
from components.tag_editor_widget import TagEditorWidget
from utils import constants

def create_actions(win):
    """Creates all global QAction objects for the main window."""
    win.cut_action = QAction(IconManager.create_icon('fa5s.cut'), "Cut", win)
    win.cut_action.setShortcut(QKeySequence.StandardKey.Cut)
    win.copy_action = QAction(IconManager.create_icon('fa5s.copy'), "Copy", win)
    win.copy_action.setShortcut(QKeySequence.StandardKey.Copy)
    win.paste_action = QAction(IconManager.create_icon('fa5s.paste'), "Paste", win)
    win.paste_action.setShortcut(QKeySequence.StandardKey.Paste)
    win.undo_action = QAction(IconManager.create_icon('fa5s.undo'), "Undo", win)
    win.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
    win.redo_action = QAction(IconManager.create_icon('fa5s.redo'), "Redo", win)
    win.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
    
    win.addActions([win.cut_action, win.copy_action, win.paste_action, win.undo_action, win.redo_action])
    
    win.quick_access_toolbar.add_undo_redo_actions(win.undo_action, win.redo_action)
    win.quick_access_toolbar.add_clipboard_actions(win.cut_action, win.copy_action, win.paste_action)
    win.ribbon.add_undo_redo_actions(win.undo_action, win.redo_action)
    win.ribbon.add_clipboard_actions(win.cut_action, win.copy_action, win.paste_action)
    
    for action in [win.cut_action, win.copy_action, win.paste_action, win.undo_action, win.redo_action]:
        action.setEnabled(False)

def update_edit_actions(win):
    """Updates the enabled state of all edit-related actions."""
    update_undo_redo_actions(win)
    update_clipboard_actions(win)

def update_undo_redo_actions(win):
    """Updates the enabled state of the undo and redo actions."""
    win.undo_action.setEnabled(command_history_service.can_undo())
    win.redo_action.setEnabled(command_history_service.can_redo())

def update_clipboard_actions(win):
    """Updates the enabled state of clipboard actions based on focus."""
    can_copy = can_paste = False
    focused_widget = win.last_focused_copypaste_widget
    content_type, _ = clipboard_service.get_content()
    
    if hasattr(focused_widget, 'has_selection'):
        can_copy = focused_widget.has_selection()
    
    if isinstance(focused_widget, ProjectDock):
        can_paste = content_type in (constants.CLIPBOARD_TYPE_TAG_DATABASE, constants.CLIPBOARD_TYPE_SCREEN)
    elif isinstance(focused_widget, ScreenWidget):
        can_paste = content_type == constants.CLIPBOARD_TYPE_HMI_OBJECTS
    elif isinstance(focused_widget, TagEditorWidget):
        can_paste = content_type == constants.CLIPBOARD_TYPE_TAG
    
    win.cut_action.setEnabled(can_copy)
    win.copy_action.setEnabled(can_copy)
    win.paste_action.setEnabled(can_paste)
