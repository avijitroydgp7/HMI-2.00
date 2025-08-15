# components/screen/screen_manager_widget.py
# MODIFIED: Fixed a critical bug where editing screen properties deleted all child objects.

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QMenu, QMessageBox
from PyQt6.QtCore import Qt, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QKeyEvent
import qtawesome as qta
import copy
from services.screen_data_service import screen_service
from services.clipboard_service import clipboard_service
from services.command_history_service import command_history_service
from services.commands import AddScreenCommand, RemoveScreenCommand, UpdateScreenPropertiesCommand
from dialogs import ScreenPropertiesDialog
from .screen_tree import ScreenTreeWidget, ScreenTreeItem

class ScreenManagerWidget(QWidget):
    screen_open_requested = pyqtSignal(str)
    selection_changed = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.item_map = {}
        self.root_items = {}
        self.current_screen_type_for_dialog = None
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.tree = ScreenTreeWidget(self)
        layout.addWidget(self.tree)

        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.show_context_menu)
        self.tree.itemDoubleClicked.connect(self.handle_item_double_clicked)
        self.tree.delete_key_pressed.connect(self.handle_delete_key_press)
        self.tree.rename_key_pressed.connect(self.handle_rename_key_press)
        self.tree.itemSelectionChanged.connect(self.selection_changed.emit)
        
        screen_service.screen_list_changed.connect(self.sync_tree_with_service)
        screen_service.screen_modified.connect(self._on_screen_modified)
        
        self.sync_tree_with_service()

    def clear_selection(self):
        self.tree.clearSelection()

    def has_selection(self):
        item = self.tree.currentItem()
        return item is not None and item.data(0, Qt.ItemDataRole.UserRole + 1) is not None

    def get_selected_item_data(self):
        item = self.tree.currentItem()
        if not item or not self.has_selection(): return None
        screen_id = item.data(0, Qt.ItemDataRole.UserRole)
        screen_data = screen_service.get_screen(screen_id)
        if screen_data:
            return {'name': f"[{screen_data.get('number', '?')}] {screen_data.get('name', 'Unknown')}", 'type': 'Screen'}
        return None

    @pyqtSlot()
    def sync_tree_with_service(self):
        self.tree.blockSignals(True)

        expanded_ids = {sid for sid, itm in self.item_map.items() if itm.isExpanded()}

        self._get_or_create_root_item('base', "Base Screens", 'fa5.clone', '#5dadec')
        self._get_or_create_root_item('window', "Window Screens", 'fa5.window-maximize', '#5dadec')
        self._get_or_create_root_item('report', "Report Screens", 'fa5.file-alt', '#5dadec')
        
        all_screens = screen_service.get_all_screens()
        existing_ids = set(self.item_map.keys())
        service_ids = set(all_screens.keys())

        for removed_id in existing_ids - service_ids:
            item = self.item_map.pop(removed_id)
            parent = item.parent()
            if parent: parent.removeChild(item)

        for screen_id, screen_data in all_screens.items():
            parent_root = self.root_items.get(screen_data.get('type'))
            item = self.item_map.get(screen_id)
            if item is None:
                if parent_root:
                    item = self._create_item(screen_id, screen_data, parent_root)
                    self.item_map[screen_id] = item
            else:
                if item.parent() != parent_root:
                    item.parent().removeChild(item)
                    parent_root.addChild(item)
                self._update_item(item, screen_id, screen_data)

            if item:
                self._sync_item_children(item, screen_data)

        self.tree.sortItems(0, Qt.SortOrder.AscendingOrder)
        for root_item in self.root_items.values():
            root_item.setExpanded(True)
        for sid, itm in self.item_map.items():
            itm.setExpanded(sid in expanded_ids)
        self.tree.blockSignals(False)

    @pyqtSlot(str)
    def _on_screen_modified(self, screen_id: str):
        self.sync_tree_with_service()

    def _get_or_create_root_item(self, type_name, display_text, icon, color):
        if type_name in self.root_items: return self.root_items[type_name]
        item = ScreenTreeItem(self.tree, [display_text])
        font = item.font(0); font.setBold(True); item.setFont(0, font)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDragEnabled)
        item.setData(0, Qt.ItemDataRole.UserRole, type_name)
        item.setIcon(0, qta.icon(icon, color=color))
        self.root_items[type_name] = item
        return item

    def _sync_item_children(self, item, screen_data):
        existing = {item.child(i).data(0, Qt.ItemDataRole.UserRole): item.child(i) for i in range(item.childCount())}
        desired = []
        for child in screen_data.get('children', []):
            child_id = child.get('screen_id')
            if not child_id:
                continue
            child_data = screen_service.get_screen(child_id)
            if not child_data:
                if child_id in existing:
                    item.removeChild(existing[child_id])
                continue
            desired.append(child_id)
            if child_id in existing:
                self._update_item(existing[child_id], child_id, child_data, is_reference=True)
            else:
                self._create_item(child_id, child_data, item, is_reference=True)
        for cid, citem in existing.items():
            if cid not in desired:
                item.removeChild(citem)

    def _create_item(self, screen_id, screen_data, parent_widget, is_reference=False):
        item = ScreenTreeItem(parent_widget)
        item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | (Qt.ItemFlag.ItemIsDragEnabled if not is_reference else Qt.ItemFlag.NoItemFlags))
        self._update_item(item, screen_id, screen_data, is_reference)
        return item
    
    def _update_item(self, item, screen_id, screen_data, is_reference=False):
        if is_reference:
            type_char = screen_data.get('type', 'B')[0].upper()
            item_text = f"[{type_char}] – [{screen_data.get('number', '?')}] - {screen_data.get('name', 'Ref')}"
            item.setIcon(0, qta.icon('fa5s.link', color='#9da5b4'))
            item.setData(0, Qt.ItemDataRole.UserRole + 1, None)
        else:
            item_text = f"[{screen_data.get('number', '?')}] - {screen_data.get('name', 'Screen')}"
            icon_map = {'base': 'fa5.clone', 'window': 'fa5.window-maximize', 'report': 'fa5.file-alt'}
            item.setIcon(0, qta.icon(icon_map.get(screen_data.get('type'), 'fa5.square'), color='#c8cdd4'))
            item.setData(0, Qt.ItemDataRole.UserRole + 1, screen_data.get('number'))
        item.setText(0, item_text)
        item.setData(0, Qt.ItemDataRole.UserRole, screen_id)
        item.setToolTip(0, f"ID: {screen_id}\nType: {screen_data.get('type', 'N/A')}\nDesc: {screen_data.get('description', '')}")
    
    def update_active_screen_highlight(self, active_screen_id=None):
        for item in self.item_map.values():
            font = item.font(0)
            font.setBold(item.data(0, Qt.ItemDataRole.UserRole) == active_screen_id)
            item.setFont(0, font)

    def show_context_menu(self, position):
        menu = QMenu(); item = self.tree.itemAt(position)
        if not item: return
        content_type, _ = clipboard_service.get_content()
        paste_action = menu.addAction(qta.icon('fa5s.paste', color='#dbe0e8'), "Paste")
        paste_action.triggered.connect(self.paste); paste_action.setEnabled(content_type == 'screen')
        menu.addSeparator()
        item_id = item.data(0, Qt.ItemDataRole.UserRole)
        is_primary = item.data(0, Qt.ItemDataRole.UserRole + 1) is not None
        if item in self.root_items.values():
            menu.addAction(f"Add New {item.text(0).replace('s', '')}").triggered.connect(lambda: self.handle_add_screen(item))
        elif is_primary:
            menu.addAction("Open").triggered.connect(lambda: self.screen_open_requested.emit(item_id))
            menu.addSeparator()
            menu.addAction(qta.icon('fa5s.copy', color='#dbe0e8'), "Copy").triggered.connect(self.copy_selected)
            menu.addAction(qta.icon('fa5s.cut', color='#dbe0e8'), "Cut").triggered.connect(self.cut_selected)
            menu.addSeparator()
            menu.addAction("Properties...").triggered.connect(lambda: self.handle_edit_screen(item_id))
            menu.addAction("Delete").triggered.connect(lambda: self.handle_delete_screen(item_id, item.text(0)))
        if not menu.isEmpty(): menu.exec(self.tree.viewport().mapToGlobal(position))
    
    def handle_item_double_clicked(self, item, column):
        is_primary_item = item.data(0, Qt.ItemDataRole.UserRole + 1) is not None
        if is_primary_item:
            screen_id = item.data(0, Qt.ItemDataRole.UserRole)
            if screen_id: self.screen_open_requested.emit(screen_id)

    def handle_add_screen(self, parent_root_item):
        self.current_screen_type_for_dialog = parent_root_item.data(0, Qt.ItemDataRole.UserRole)
        dialog = ScreenPropertiesDialog(self.current_screen_type_for_dialog, self)
        if dialog.exec():
            new_data = dialog.get_data()
            new_data['type'] = self.current_screen_type_for_dialog
            command = AddScreenCommand(new_data)
            command_history_service.add_command(command)
            if command.screen_id: self.screen_open_requested.emit(command.screen_id)

    def handle_edit_screen(self, screen_id):
        old_data = screen_service.get_screen(screen_id)
        if not old_data: return
        
        dialog = ScreenPropertiesDialog(old_data['type'], self, edit_data=old_data)
        if dialog.exec():
            # --- MODIFIED: The critical fix is here ---
            # 1. Get the partial data from the dialog
            partial_new_data = dialog.get_data()
            
            # 2. Create a full copy of the old data to preserve fields like 'children'
            full_new_data = copy.deepcopy(old_data)
            
            # 3. Update the full copy with the partial changes
            full_new_data.update(partial_new_data)
            
            # 4. Create the command with the complete "before" and "after" states
            command = UpdateScreenPropertiesCommand(screen_id, full_new_data, old_data)
            command_history_service.add_command(command)
            # --- End of modification ---

    def handle_rename_key_press(self):
        item = self.tree.currentItem()
        is_primary_item = item and item.data(0, Qt.ItemDataRole.UserRole + 1) is not None
        if is_primary_item:
            screen_id = item.data(0, Qt.ItemDataRole.UserRole)
            if screen_id: self.handle_edit_screen(screen_id)

    def handle_delete_key_press(self):
        item = self.tree.currentItem()
        is_primary_item = item and item.data(0, Qt.ItemDataRole.UserRole + 1) is not None
        if is_primary_item:
            self.handle_delete_screen(item.data(0, Qt.ItemDataRole.UserRole), item.text(0))

    def handle_delete_screen(self, screen_id, screen_name):
        from dialogs.question_dialog import CustomQuestionDialog
        dialog = CustomQuestionDialog(self)
        dialog.setWindowTitle("Delete Screen")
        dialog.setText(f"Are you sure you want to permanently delete '{screen_name}'?")
        result = dialog.exec()
        if result == dialog.accepted and dialog.answer == dialog.Yes:
            command = RemoveScreenCommand(screen_id)
            command_history_service.add_command(command)

    def copy_selected(self):
        if not self.has_selection(): return
        screen_data = screen_service.get_screen(self.tree.currentItem().data(0, Qt.ItemDataRole.UserRole))
        if screen_data: clipboard_service.set_content('screen', screen_data)

    def cut_selected(self):
        self.copy_selected()
        if self.has_selection():
            screen_id = self.tree.currentItem().data(0, Qt.ItemDataRole.UserRole)
            command = RemoveScreenCommand(screen_id)
            command_history_service.add_command(command)

    def paste(self):
        content_type, data = clipboard_service.get_content()
        if content_type != 'screen': return
        new_data = copy.deepcopy(data); new_data.pop('id', None)
        new_data['name'] = f"{new_data.get('name', 'Screen')} (Copy)"
        num = new_data.get('number', 1)
        while not screen_service.is_screen_number_unique(new_data['type'], num): num += 1
        new_data['number'] = num
        dialog = ScreenPropertiesDialog(new_data['type'], self, edit_data=new_data)
        if dialog.exec():
            final_data = dialog.get_data()
            final_data['children'] = new_data.get('children', [])
            final_data['type'] = new_data['type']
            command = AddScreenCommand(final_data)
            command_history_service.add_command(command)
