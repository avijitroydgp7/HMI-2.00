# main_window/actions.py
from PyQt6.QtGui import QAction, QKeySequence
from utils.icon_manager import IconManager
from services.command_history_service import command_history_service
from services.clipboard_service import clipboard_service
from services.commands import BulkMoveChildCommand
from components.docks import ProjectDock
from components.screen.screen_widget import ScreenWidget
from components.screen.graphics_items import BaseGraphicsItem
from components.tag_editor_widget import TagEditorWidget
from utils import constants

def create_actions(win):
    """Creates all global QAction objects for the main window."""
    def _animated_action(icon_name: str, text: str):
        anim = IconManager.create_animated_icon(icon_name)
        action = QAction(anim.icon, text, win)
        anim.add_target(action)
        action._animated_icon = anim
        return action

    win.cut_action = _animated_action('fa5s.cut', "Cut")
    win.cut_action.setShortcut(QKeySequence.StandardKey.Cut)
    win.copy_action = _animated_action('fa5s.copy', "Copy")
    win.copy_action.setShortcut(QKeySequence.StandardKey.Copy)
    win.paste_action = _animated_action('fa5s.paste', "Paste")
    win.paste_action.setShortcut(QKeySequence.StandardKey.Paste)
    win.undo_action = _animated_action('fa5s.undo', "Undo")
    win.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
    win.redo_action = _animated_action('fa5s.redo', "Redo")
    win.redo_action.setShortcut(QKeySequence.StandardKey.Redo)

    # Alignment and distribution actions
    win.align_left_action = _animated_action('mdi.align-horizontal-left', "Align Left")
    win.align_center_action = _animated_action('mdi.align-horizontal-center', "Align Center")
    win.align_right_action = _animated_action('mdi.align-horizontal-right', "Align Right")
    win.align_top_action = _animated_action('mdi.align-vertical-top', "Align Top")
    win.align_middle_action = _animated_action('mdi.align-vertical-center', "Align Middle")
    win.align_bottom_action = _animated_action('mdi.align-vertical-bottom', "Align Bottom")
    win.distribute_h_action = _animated_action('mdi.format-horizontal-align-center', "Distribute Horizontally")
    win.distribute_v_action = _animated_action('mdi.format-vertical-align-center', "Distribute Vertically")

    win.addActions([
        win.cut_action,
        win.copy_action,
        win.paste_action,
        win.undo_action,
        win.redo_action,
        win.align_left_action,
        win.align_center_action,
        win.align_right_action,
        win.align_top_action,
        win.align_middle_action,
        win.align_bottom_action,
        win.distribute_h_action,
        win.distribute_v_action,
    ])

    win.quick_access_toolbar.add_undo_redo_actions(win.undo_action, win.redo_action)
    win.quick_access_toolbar.add_clipboard_actions(win.cut_action, win.copy_action, win.paste_action)
    win.quick_access_toolbar.addAction(win.align_left_action)
    win.quick_access_toolbar.addAction(win.align_center_action)
    win.quick_access_toolbar.addAction(win.align_right_action)
    win.quick_access_toolbar.addAction(win.align_top_action)
    win.quick_access_toolbar.addAction(win.align_middle_action)
    win.quick_access_toolbar.addAction(win.align_bottom_action)
    win.quick_access_toolbar.addAction(win.distribute_h_action)
    win.quick_access_toolbar.addAction(win.distribute_v_action)

    win.ribbon.add_undo_redo_actions(win.undo_action, win.redo_action)
    win.ribbon.add_clipboard_actions(win.cut_action, win.copy_action, win.paste_action)
    win.ribbon.edit_tab.toolbar.addAction(win.align_left_action)
    win.ribbon.edit_tab.toolbar.addAction(win.align_center_action)
    win.ribbon.edit_tab.toolbar.addAction(win.align_right_action)
    win.ribbon.edit_tab.toolbar.addAction(win.align_top_action)
    win.ribbon.edit_tab.toolbar.addAction(win.align_middle_action)
    win.ribbon.edit_tab.toolbar.addAction(win.align_bottom_action)
    win.ribbon.edit_tab.toolbar.addAction(win.distribute_h_action)
    win.ribbon.edit_tab.toolbar.addAction(win.distribute_v_action)

    for action in [
        win.cut_action,
        win.copy_action,
        win.paste_action,
        win.undo_action,
        win.redo_action,
    ]:
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


def _get_selected_items(win):
    """Return current ScreenWidget, canvas and selected BaseGraphicsItems."""
    tab_widget = getattr(win, 'tab_widget', None)
    if tab_widget is None:
        return None, None, []
    current_widget = tab_widget.currentWidget()
    if not isinstance(current_widget, ScreenWidget):
        return None, None, []
    canvas = current_widget.design_canvas
    items = [
        item for item in canvas.scene.selectedItems()
        if isinstance(item, BaseGraphicsItem)
    ]
    return current_widget, canvas, items


def align_left(win):
    widget, canvas, items = _get_selected_items(win)
    if len(items) < 2:
        return
    left = min(item.pos().x() for item in items)
    move_list = []
    for item in items:
        old_x = item.pos().x()
        old_y = item.pos().y()
        if old_x != left:
            item.setPos(left, old_y)
            move_list.append((
                item.get_instance_id(),
                {'x': left, 'y': old_y},
                {'x': old_x, 'y': old_y},
            ))
    if move_list:
        command_history_service.add_command(
            BulkMoveChildCommand(canvas.screen_id, move_list)
        )
        widget.refresh_selection_status()


def align_right(win):
    widget, canvas, items = _get_selected_items(win)
    if len(items) < 2:
        return
    right = max(item.pos().x() + item.boundingRect().width() for item in items)
    move_list = []
    for item in items:
        w = item.boundingRect().width()
        new_x = right - w
        old_x = item.pos().x()
        old_y = item.pos().y()
        if old_x != new_x:
            item.setPos(new_x, old_y)
            move_list.append((
                item.get_instance_id(),
                {'x': new_x, 'y': old_y},
                {'x': old_x, 'y': old_y},
            ))
    if move_list:
        command_history_service.add_command(
            BulkMoveChildCommand(canvas.screen_id, move_list)
        )
        widget.refresh_selection_status()


def align_center(win):
    widget, canvas, items = _get_selected_items(win)
    if len(items) < 2:
        return
    left = min(item.pos().x() for item in items)
    right = max(item.pos().x() + item.boundingRect().width() for item in items)
    center_x = (left + right) / 2.0
    move_list = []
    for item in items:
        w = item.boundingRect().width()
        new_x = center_x - w / 2.0
        old_x = item.pos().x()
        old_y = item.pos().y()
        if old_x != new_x:
            item.setPos(new_x, old_y)
            move_list.append((
                item.get_instance_id(),
                {'x': new_x, 'y': old_y},
                {'x': old_x, 'y': old_y},
            ))
    if move_list:
        command_history_service.add_command(
            BulkMoveChildCommand(canvas.screen_id, move_list)
        )
        widget.refresh_selection_status()


def align_top(win):
    widget, canvas, items = _get_selected_items(win)
    if len(items) < 2:
        return
    top = min(item.pos().y() for item in items)
    move_list = []
    for item in items:
        old_x = item.pos().x()
        old_y = item.pos().y()
        if old_y != top:
            item.setPos(old_x, top)
            move_list.append(
                (
                    item.get_instance_id(),
                    {'x': old_x, 'y': top},
                    {'x': old_x, 'y': old_y},
                )
            )
    if move_list:
        command_history_service.add_command(
            BulkMoveChildCommand(canvas.screen_id, move_list)
        )
        widget.refresh_selection_status()


def align_bottom(win):
    widget, canvas, items = _get_selected_items(win)
    if len(items) < 2:
        return
    bottom = max(item.pos().y() + item.boundingRect().height() for item in items)
    move_list = []
    for item in items:
        h = item.boundingRect().height()
        new_y = bottom - h
        old_x = item.pos().x()
        old_y = item.pos().y()
        if old_y != new_y:
            item.setPos(old_x, new_y)
            move_list.append(
                (
                    item.get_instance_id(),
                    {'x': old_x, 'y': new_y},
                    {'x': old_x, 'y': old_y},
                )
            )
    if move_list:
        command_history_service.add_command(
            BulkMoveChildCommand(canvas.screen_id, move_list)
        )
        widget.refresh_selection_status()


def align_middle(win):
    widget, canvas, items = _get_selected_items(win)
    if len(items) < 2:
        return
    top = min(item.pos().y() for item in items)
    bottom = max(item.pos().y() + item.boundingRect().height() for item in items)
    center_y = (top + bottom) / 2.0
    move_list = []
    for item in items:
        h = item.boundingRect().height()
        new_y = center_y - h / 2.0
        old_x = item.pos().x()
        old_y = item.pos().y()
        if old_y != new_y:
            item.setPos(old_x, new_y)
            move_list.append(
                (
                    item.get_instance_id(),
                    {'x': old_x, 'y': new_y},
                    {'x': old_x, 'y': old_y},
                )
            )
    if move_list:
        command_history_service.add_command(
            BulkMoveChildCommand(canvas.screen_id, move_list)
        )
        widget.refresh_selection_status()


def distribute_horizontally(win):
    widget, canvas, items = _get_selected_items(win)
    if len(items) < 3:
        return
    items_sorted = sorted(items, key=lambda it: it.pos().x())
    left = min(item.pos().x() for item in items_sorted)
    right = max(item.pos().x() + item.boundingRect().width() for item in items_sorted)
    total_width = sum(item.boundingRect().width() for item in items_sorted)
    space = (right - left - total_width) / (len(items_sorted) - 1)
    current_x = left
    move_list = []
    for item in items_sorted:
        old_x = item.pos().x()
        old_y = item.pos().y()
        new_x = current_x
        current_x += item.boundingRect().width() + space
        if old_x != new_x:
            item.setPos(new_x, old_y)
            move_list.append((
                item.get_instance_id(),
                {'x': new_x, 'y': old_y},
                {'x': old_x, 'y': old_y},
            ))
    if move_list:
        command_history_service.add_command(
            BulkMoveChildCommand(canvas.screen_id, move_list)
        )
        widget.refresh_selection_status()


def distribute_vertically(win):
    widget, canvas, items = _get_selected_items(win)
    if len(items) < 3:
        return
    items_sorted = sorted(items, key=lambda it: it.pos().y())
    top = min(item.pos().y() for item in items_sorted)
    bottom = max(item.pos().y() + item.boundingRect().height() for item in items_sorted)
    total_height = sum(item.boundingRect().height() for item in items_sorted)
    space = (bottom - top - total_height) / (len(items_sorted) - 1)
    current_y = top
    move_list = []
    for item in items_sorted:
        old_x = item.pos().x()
        old_y = item.pos().y()
        new_y = current_y
        current_y += item.boundingRect().height() + space
        if old_y != new_y:
            item.setPos(old_x, new_y)
            move_list.append((
                item.get_instance_id(),
                {'x': old_x, 'y': new_y},
                {'x': old_x, 'y': old_y},
            ))
    if move_list:
        command_history_service.add_command(
            BulkMoveChildCommand(canvas.screen_id, move_list)
        )
        widget.refresh_selection_status()