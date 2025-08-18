# components/docks.py
from PyQt6.QtWidgets import QDockWidget, QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QMenu, QMessageBox, QAbstractItemView
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
import qtawesome as qta
import copy

from services.tag_data_service import tag_data_service
from services.comment_data_service import comment_data_service
from services.clipboard_service import clipboard_service
from services.command_history_service import command_history_service
from services.commands import (
    AddTagDatabaseCommand, RemoveTagDatabaseCommand, RenameTagDatabaseCommand,
    AddCommentGroupCommand, RemoveCommentGroupCommand, RenameCommentGroupCommand
)
from dialogs import NewTagDatabaseDialog, NewCommentTableDialog
from utils import constants
from components.tree_widget import CustomTreeWidget

class ProjectTreeWidget(CustomTreeWidget):

    delete_key_pressed = pyqtSignal()
    rename_key_pressed = pyqtSignal()
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setHeaderHidden(True)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setIndentation(20)  # Increased to 20px for consistent expand/collapse area
        self.setRootIsDecorated(True)
    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_key_pressed.emit()
            event.accept()
        elif event.key() == Qt.Key.Key_F2:
            self.rename_key_pressed.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

class ProjectDock(QDockWidget):
    tag_database_open_requested = pyqtSignal(str)
    comment_table_open_requested = pyqtSignal(str)
    project_info_requested = pyqtSignal()
    system_tab_requested = pyqtSignal()
    screens_tab_requested = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Project", parent)
        self.setObjectName("ProjectDock")
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        self.tree = ProjectTreeWidget(self)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tree.delete_key_pressed.connect(self._handle_delete_key_press)
        self.tree.rename_key_pressed.connect(self._handle_rename_key_press)
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.tree)
        self.setWidget(container)
        self._populate_tree()
        tag_data_service.database_list_changed.connect(self._populate_tree)
        comment_data_service.comment_group_list_changed.connect(self._populate_tree)

    def _populate_tree(self):
        self.tree.clear()
        info_item = QTreeWidgetItem(self.tree, ["Project Information"])
        info_item.setIcon(0, qta.icon('fa5s.info-circle', color='#5dadec'))
        info_item.setData(0, Qt.ItemDataRole.UserRole, constants.PROJECT_TREE_ITEM_PROJECT_INFO)
        system_item = QTreeWidgetItem(self.tree, ["System"])
        system_item.setIcon(0, qta.icon('fa5s.cogs', color='#5dadec'))
        system_item.setData(0, Qt.ItemDataRole.UserRole, constants.PROJECT_TREE_ITEM_SYSTEM)
        screens_item = QTreeWidgetItem(self.tree, ["Screens"])
        screens_item.setIcon(0, qta.icon('fa5.clone', color='#5dadec'))
        screens_item.setData(0, Qt.ItemDataRole.UserRole, constants.PROJECT_TREE_ITEM_SCREENS)
        comment_root = QTreeWidgetItem(self.tree, ["Comment Tables"])
        comment_root.setIcon(0, qta.icon('fa5s.comments', color='#5dadec'))
        comment_root.setData(0, Qt.ItemDataRole.UserRole, constants.PROJECT_TREE_ITEM_COMMENT_ROOT)
        for gid, gdata in comment_data_service.get_all_groups().items():
            label = f"[{gdata.get('number','')}] - {gdata.get('name','')}"
            item = QTreeWidgetItem(comment_root, [label])
            item.setIcon(0, qta.icon('fa5s.comment', color='#c8cdd4'))
            item.setData(0, Qt.ItemDataRole.UserRole, gid)
        comment_root.setExpanded(True)
        tags_root = QTreeWidgetItem(self.tree, ["Tag Databases"])
        tags_root.setIcon(0, qta.icon('fa5s.tags', color='#5dadec'))
        tags_root.setData(0, Qt.ItemDataRole.UserRole, constants.PROJECT_TREE_ITEM_TAGS_ROOT)
        for db_id, db_data in tag_data_service.get_all_tag_databases().items():
            db_item = QTreeWidgetItem(tags_root, [db_data.get('name', 'Unnamed DB')])
            db_item.setIcon(0, qta.icon('fa5s.database', color='#c8cdd4'))
            db_item.setData(0, Qt.ItemDataRole.UserRole, db_id)
        tags_root.setExpanded(True)

    def _get_selected_db_ids_and_names(self):
        selected_items = self.tree.selectedItems()
        db_ids, db_names = [], []
        for item in selected_items:
            if item.parent() and item.parent().data(0, Qt.ItemDataRole.UserRole) == constants.PROJECT_TREE_ITEM_TAGS_ROOT:
                db_ids.append(item.data(0, Qt.ItemDataRole.UserRole))
                db_names.append(item.text(0))
        return db_ids, db_names

    def _get_selected_comment_group_ids_and_labels(self):
        selected_items = self.tree.selectedItems()
        group_ids, labels = [], []
        for item in selected_items:
            if item.parent() and item.parent().data(0, Qt.ItemDataRole.UserRole) == constants.PROJECT_TREE_ITEM_COMMENT_ROOT:
                group_ids.append(item.data(0, Qt.ItemDataRole.UserRole))
                labels.append(item.text(0))
        return group_ids, labels

    def _handle_delete_key_press(self):
        db_ids, db_names = self._get_selected_db_ids_and_names()
        if db_ids:
            self._delete_databases(db_ids, db_names)
            return
        group_ids, labels = self._get_selected_comment_group_ids_and_labels()
        if group_ids:
            self._delete_comment_groups(group_ids, labels)

    def _handle_rename_key_press(self):
        item = self.tree.currentItem()
        if not item:
            return
        item_id = item.data(0, Qt.ItemDataRole.UserRole)
        parent_type = item.parent().data(0, Qt.ItemDataRole.UserRole) if item.parent() else None
        if parent_type == constants.PROJECT_TREE_ITEM_TAGS_ROOT:
            self._rename_database(item_id, item.text(0))
        elif parent_type == constants.PROJECT_TREE_ITEM_COMMENT_ROOT:
            self._rename_comment_group(item_id)

    def _show_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item: return
        menu = QMenu()
        item_id = item.data(0, Qt.ItemDataRole.UserRole)
        parent_type = item.parent().data(0, Qt.ItemDataRole.UserRole) if item.parent() else None
        content_type, _ = clipboard_service.get_content()
        if item_id == constants.PROJECT_TREE_ITEM_PROJECT_INFO:
            menu.addAction("Edit Properties...").triggered.connect(self.project_info_requested.emit)
        elif item_id == constants.PROJECT_TREE_ITEM_TAGS_ROOT:
            menu.addAction("New Tag Database...").triggered.connect(self._add_new_tag_database)
            paste_action = menu.addAction("Paste")
            paste_action.triggered.connect(self.paste)
            paste_action.setEnabled(content_type == constants.CLIPBOARD_TYPE_TAG_DATABASE)
        elif item_id == constants.PROJECT_TREE_ITEM_COMMENT_ROOT:
            menu.addAction("New Comment Table...").triggered.connect(self._add_new_comment_table)
            paste_action = menu.addAction("Paste")
            paste_action.triggered.connect(self.paste)
            paste_action.setEnabled(content_type == constants.CLIPBOARD_TYPE_COMMENT_GROUP)
        elif parent_type == constants.PROJECT_TREE_ITEM_COMMENT_ROOT:
            menu.addAction("Open Comment Table").triggered.connect(lambda: self.comment_table_open_requested.emit(item_id))
            menu.addSeparator()
            menu.addAction("Cut").triggered.connect(self.cut_selected)
            menu.addAction("Copy").triggered.connect(self.copy_selected)
            menu.addSeparator()
            menu.addAction("Delete").triggered.connect(lambda: self._delete_comment_groups([item_id], [item.text(0)]))
            menu.addAction("Rename...").triggered.connect(lambda: self._rename_comment_group(item_id))
        elif parent_type == constants.PROJECT_TREE_ITEM_TAGS_ROOT:
            menu.addAction("Open Tag Editor").triggered.connect(lambda: self.tag_database_open_requested.emit(item_id))
            menu.addSeparator()
            menu.addAction("Cut").triggered.connect(self.cut_selected)
            menu.addAction("Copy").triggered.connect(self.copy_selected)
            menu.addSeparator()
            menu.addAction("Delete").triggered.connect(lambda: self._delete_databases([item_id], [item.text(0)]))
            menu.addAction("Rename...").triggered.connect(lambda: self._rename_database(item_id, item.text(0)))
        if not menu.isEmpty(): menu.exec(self.tree.viewport().mapToGlobal(position))

    def _on_item_double_clicked(self, item, column):
        item_id = item.data(0, Qt.ItemDataRole.UserRole)
        parent_type = item.parent().data(0, Qt.ItemDataRole.UserRole) if item.parent() else None
        if item_id == constants.PROJECT_TREE_ITEM_PROJECT_INFO: self.project_info_requested.emit()
        elif item_id == constants.PROJECT_TREE_ITEM_SYSTEM: self.system_tab_requested.emit()
        elif item_id == constants.PROJECT_TREE_ITEM_SCREENS: self.screens_tab_requested.emit()
        elif parent_type == constants.PROJECT_TREE_ITEM_COMMENT_ROOT: self.comment_table_open_requested.emit(item_id)
        elif parent_type == constants.PROJECT_TREE_ITEM_TAGS_ROOT: self.tag_database_open_requested.emit(item_id)

    def _add_new_tag_database(self):
        dialog = NewTagDatabaseDialog(self)
        if dialog.exec():
            db_name = dialog.get_database_name()
            if db_name:
                command = AddTagDatabaseCommand({"name": db_name, "tags": []})
                command_history_service.add_command(command)

    def _add_new_comment_table(self):
        dialog = NewCommentTableDialog(self)
        if dialog.exec():
            number, name = dialog.get_values()
            if number and name:
                command = AddCommentGroupCommand({
                    "number": number,
                    "name": name,
                    "columns": ["Comment"],
                    "comments": [],
                    "excel": {},
                })
                command_history_service.add_command(command)

    def _delete_databases(self, db_ids, db_names):
        count = len(db_ids)
        if count == 0: return
        message = f"Are you sure you want to delete '{db_names[0]}'?" if count == 1 else f"Are you sure you want to delete the {count} selected databases?"
        if QMessageBox.question(self, "Delete Database(s)", message) == QMessageBox.StandardButton.Yes:
            for db_id in db_ids:
                command = RemoveTagDatabaseCommand(db_id)
                command_history_service.add_command(command)

    def _delete_comment_groups(self, group_ids, labels):
        count = len(group_ids)
        if count == 0: return
        message = (
            f"Are you sure you want to delete '{labels[0]}'?" if count == 1
            else f"Are you sure you want to delete the {count} selected comment tables?"
        )
        if QMessageBox.question(self, "Delete Comment Table(s)", message) == QMessageBox.StandardButton.Yes:
            for gid in group_ids:
                command = RemoveCommentGroupCommand(gid)
                command_history_service.add_command(command)

    def _rename_database(self, db_id, old_name):
        dialog = NewTagDatabaseDialog(self, edit_name=old_name)
        if dialog.exec():
            new_name = dialog.get_database_name()
            if new_name != old_name:
                command = RenameTagDatabaseCommand(db_id, new_name, old_name)
                command_history_service.add_command(command)

    def _rename_comment_group(self, group_id):
        group_data = comment_data_service.get_group(group_id) or {}
        old_name = group_data.get('name', '')
        old_number = group_data.get('number', '')
        dialog = NewCommentTableDialog(self, edit_group=group_id)
        if dialog.exec():
            new_number, new_name = dialog.get_values()
            if new_name != old_name or new_number != old_number:
                command = RenameCommentGroupCommand(group_id, new_name, new_number, old_name, old_number)
                command_history_service.add_command(command)

    def has_selection(self): return len(self.tree.selectedItems()) > 0
    def clear_selection(self): self.tree.clearSelection()

    def get_selected_item_data(self):
        selected_items = self.tree.selectedItems()
        if not selected_items:
            return None

        item = selected_items[0]
        item_id = item.data(0, Qt.ItemDataRole.UserRole)
        parent_type = item.parent().data(0, Qt.ItemDataRole.UserRole) if item.parent() else None
        if item_id == constants.PROJECT_TREE_ITEM_COMMENT_ROOT:
            return {'name': 'Comment Tables', 'type': 'Comment Tables'}
        if parent_type == constants.PROJECT_TREE_ITEM_COMMENT_ROOT:
            return {'name': item.text(0), 'type': 'Comment Table'}

        db_ids, db_names = self._get_selected_db_ids_and_names()
        if not db_ids:
            return None
        if len(db_ids) > 1:
            return {'name': f"{len(db_ids)} Databases", 'type': 'Tag Databases'}
        else:
            return {'name': db_names[0], 'type': 'Tag Database'}

    def copy_selected(self):
        db_ids, _ = self._get_selected_db_ids_and_names()
        if db_ids:
            databases_data = [copy.deepcopy(tag_data_service.get_tag_database(db_id)) for db_id in db_ids]
            if databases_data:
                clipboard_service.set_content(constants.CLIPBOARD_TYPE_TAG_DATABASE, databases_data)
            return
        group_ids, _ = self._get_selected_comment_group_ids_and_labels()
        if group_ids:
            groups_data = [copy.deepcopy(comment_data_service.get_group(gid)) for gid in group_ids]
            if groups_data:
                clipboard_service.set_content(constants.CLIPBOARD_TYPE_COMMENT_GROUP, groups_data)

    def cut_selected(self):
        self.copy_selected()
        self._handle_delete_key_press()

    def paste(self):
        content_type, data = clipboard_service.get_content()
        if content_type == constants.CLIPBOARD_TYPE_TAG_DATABASE and data:
            databases_to_paste = data if isinstance(data, list) else [data]
            for db_data in databases_to_paste:
                new_data = copy.deepcopy(db_data)
                new_data.pop('id', None)
                original_name = new_data.get('name', 'Pasted_DB')
                new_name = original_name
                count = 1
                while not tag_data_service.is_database_name_unique(new_name):
                    new_name = f"{original_name}_{count}"
                    count += 1
                new_data['name'] = new_name
                command = AddTagDatabaseCommand(new_data)
                command_history_service.add_command(command)
        elif content_type == constants.CLIPBOARD_TYPE_COMMENT_GROUP and data:
            groups_to_paste = data if isinstance(data, list) else [data]
            for group_data in groups_to_paste:
                new_data = copy.deepcopy(group_data)
                new_data.pop('id', None)
                original_number = new_data.get('number', '')
                original_name = new_data.get('name', 'Pasted')
                new_number = original_number
                try:
                    base_num = int(original_number)
                    while not comment_data_service.is_group_number_unique(str(base_num)):
                        base_num += 1
                    new_number = str(base_num)
                except ValueError:
                    count = 1
                    while not comment_data_service.is_group_number_unique(new_number):
                        new_number = f"{original_number}_{count}"
                        count += 1
                new_name = original_name
                count = 1
                while not comment_data_service.is_group_name_unique(new_name):
                    new_name = f"{original_name}_{count}"
                    count += 1
                new_data['number'] = new_number
                new_data['name'] = new_name
                command = AddCommentGroupCommand(new_data)
                command_history_service.add_command(command)

class SystemDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("System", parent)
        self.setObjectName("SystemDock")
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )

class ScreensDock(QDockWidget):
    def __init__(self, parent=None):
        super().__init__("Screens", parent)
        self.setObjectName("ScreensDock")
        self.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
        self.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetClosable
            | QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        from components.screen.screen_manager_widget import ScreenManagerWidget
        self.setWidget(ScreenManagerWidget(self))
    

    
    def widget(self):
        return super().widget()

def create_docks(parent):
    """Factory function to create all dock widgets."""
    project_dock = ProjectDock(parent)
    system_dock = SystemDock(parent)
    screens_dock = ScreensDock(parent)
    from components.property_editor import PropertyEditor
    properties_dock = QDockWidget("Properties", parent)
    properties_dock.setObjectName("PropertiesDock")
    properties_dock.setAllowedAreas(Qt.DockWidgetArea.AllDockWidgetAreas)
    properties_dock.setFeatures(
        QDockWidget.DockWidgetFeature.DockWidgetClosable
        | QDockWidget.DockWidgetFeature.DockWidgetMovable
        | QDockWidget.DockWidgetFeature.DockWidgetFloatable
    )
    properties_dock.setWidget(PropertyEditor(parent))
    return {
        'project': project_dock, 'system': system_dock, 'screens': screens_dock,
        'properties': properties_dock
    }
