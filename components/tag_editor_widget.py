# components/tag_editor_widget.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QTreeWidgetItem,
    QPushButton, QAbstractItemView, QStyledItemDelegate, 
    QLineEdit, QTreeWidgetItemIterator, QMenu, QFileDialog
)
from PyQt6.QtCore import Qt, pyqtSlot, pyqtSignal
from PyQt6.QtGui import QKeyEvent
import copy
from utils.icon_manager import IconManager
from services.tag_data_service import tag_data_service
from services.clipboard_service import clipboard_service
from services.command_history_service import command_history_service
from services.csv_service import csv_service
from services.commands import (
    AddTagCommand, RemoveTagCommand, UpdateTagCommand, UpdateTagValueCommand,
    BulkAddTagsCommand
)
from dialogs import AddTagDialog
from dialogs.custom_info_dialog import CustomInfoDialog
from dialogs.custom_question_dialog import CustomQuestionDialog
from PyQt6.QtWidgets import QMessageBox
from .custom_header_view import CustomHeaderView
from .custom_tree_widget import CustomTreeWidget
from utils import constants


DATA_TYPE_RANGES = {
    "INT": {"min": -32768, "max": 32767},
    "DINT": {"min": -2147483648, "max": 2147483647},
    "REAL": {"min": -3.4028235e+38, "max": 3.4028235e+38},
}

class TagTreeDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setStyleSheet("padding: 0px; margin: 0px; border: none;")
        return editor
    def setEditorData(self, editor, index):
        editor.setText(str(index.model().data(index, Qt.ItemDataRole.EditRole)))
    def setModelData(self, editor, model, index):
        model.setData(index, editor.text(), Qt.ItemDataRole.EditRole)

class TagTreeWidget(CustomTreeWidget):

    delete_pressed = pyqtSignal()
    edit_pressed = pyqtSignal()

    def edit(self, index, trigger, event):
        if index.column() < 2: return False
        return super().edit(index, trigger, event)

    def keyPressEvent(self, event: QKeyEvent):
        if event.key() in (Qt.Key.Key_Delete, Qt.Key.Key_Backspace):
            self.delete_pressed.emit()
            event.accept()
        elif event.key() == Qt.Key.Key_F2:
            self.edit_pressed.emit()
            event.accept()
        else:
            super().keyPressEvent(event)

class TagEditorWidget(QWidget):
    validation_error_occurred = pyqtSignal(str)
    selection_changed = pyqtSignal()

    def __init__(self, db_id: str, db_name: str, parent=None):
        super().__init__(parent)
        self.db_id = db_id; self.db_name = db_name; self._is_updating_table = False
        self.setObjectName("TagEditorWidget")

        layout = QVBoxLayout(self); layout.setContentsMargins(5, 5, 5, 5); layout.setSpacing(5)
        
        toolbar_layout = QHBoxLayout()
        add_button = QPushButton(IconManager.create_icon('fa5s.plus-circle'), " Add Tag"); add_button.setObjectName("TagButton"); add_button.clicked.connect(self._open_add_tag_dialog)
        self.edit_button = QPushButton(IconManager.create_icon('fa5s.edit'), " Edit Tag"); self.edit_button.setObjectName("TagButton"); self.edit_button.clicked.connect(self._open_edit_tag_dialog)
        self.remove_button = QPushButton(IconManager.create_icon('fa5s.minus-circle'), " Remove Tag"); self.remove_button.setObjectName("TagButton"); self.remove_button.clicked.connect(self._remove_selected_tags)
        import_button = QPushButton(IconManager.create_icon('fa5s.file-import'), " Import"); import_button.setObjectName("TagButton"); import_button.clicked.connect(self._import_tags)
        export_button = QPushButton(IconManager.create_icon('fa5s.file-export'), " Export"); export_button.setObjectName("TagButton"); export_button.clicked.connect(self._export_tags)
        toolbar_layout.addWidget(add_button); toolbar_layout.addWidget(self.edit_button); toolbar_layout.addWidget(self.remove_button)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(import_button); toolbar_layout.addWidget(export_button)
        layout.addLayout(toolbar_layout)

        filter_widget = QWidget()
        filter_layout = QHBoxLayout(filter_widget)
        filter_layout.setContentsMargins(0, 5, 0, 5)
        filter_layout.setSpacing(5)
        self.name_filter_input = QLineEdit(); self.name_filter_input.setPlaceholderText("Filter by Name..."); self.name_filter_input.textChanged.connect(self._filter_tree)
        self.type_filter_input = QLineEdit(); self.type_filter_input.setPlaceholderText("Filter by Type..."); self.type_filter_input.textChanged.connect(self._filter_tree)
        self.comment_filter_input = QLineEdit(); self.comment_filter_input.setPlaceholderText("Filter by Comment..."); self.comment_filter_input.textChanged.connect(self._filter_tree)
        filter_layout.addWidget(self.name_filter_input); filter_layout.addWidget(self.type_filter_input); filter_layout.addWidget(self.comment_filter_input)
        layout.addWidget(filter_widget)

        self.tag_tree = TagTreeWidget()
        self.tag_tree.setObjectName("TagTree"); self.tag_tree.setColumnCount(4)
        self.tag_tree.setHeaderLabels(["Tag Name", "Data Type", "Live Value", "Comment"])
        self.tag_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tag_tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tag_tree.setAlternatingRowColors(True)
        self.tag_tree.setEditTriggers(QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.SelectedClicked | QAbstractItemView.EditTrigger.EditKeyPressed)
        self.tag_tree.setItemDelegate(TagTreeDelegate(self.tag_tree))
        self.tag_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tag_tree.setSortingEnabled(True)
        
        header = CustomHeaderView(Qt.Orientation.Horizontal, self.tag_tree)
        self.tag_tree.setHeader(header)
        header.setSectionResizeMode(header.Stretch)
        
        layout.addWidget(self.tag_tree)
        
        tag_data_service.tags_changed.connect(self.refresh_table)
        self.tag_tree.itemChanged.connect(self._on_item_changed)
        self.tag_tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        self.tag_tree.itemSelectionChanged.connect(self._update_button_states)
        self.tag_tree.itemSelectionChanged.connect(self.selection_changed.emit)
        self.tag_tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tag_tree.delete_pressed.connect(self._remove_selected_tags)
        self.tag_tree.edit_pressed.connect(self._handle_edit_key)
        
        self.refresh_table()
        self._update_button_states()

    def _filter_tree(self):
        name_filter = self.name_filter_input.text().lower()
        type_filter = self.type_filter_input.text().lower()
        comment_filter = self.comment_filter_input.text().lower()
        for i in range(self.tag_tree.topLevelItemCount()):
            item = self.tag_tree.topLevelItem(i)
            name_match = name_filter in item.text(0).lower()
            type_match = type_filter in item.text(1).lower()
            comment_match = comment_filter in item.text(3).lower()
            is_visible = name_match and type_match and comment_match
            item.setHidden(not is_visible)

    def _import_tags(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Import Tags from CSV", "", "CSV Files (*.csv)")
        if not file_path: return
        try:
            tags_to_import = csv_service.import_tags_from_csv(file_path)
            valid_tags = [t for t in tags_to_import if tag_data_service.is_tag_name_unique(self.db_id, t['name'])]
            if valid_tags:
                command = BulkAddTagsCommand(self.db_id, valid_tags)
                command_history_service.add_command(command)
                CustomInfoDialog.show_info(self, "Import Successful", f"{len(valid_tags)} tags were imported.")
            else:
                CustomInfoDialog.show_info(self, "Import Complete", "No new tags were imported as all tags in the file already exist or are invalid.")
        except Exception as e:
            CustomInfoDialog.show_info(self, "Import Error", f"An error occurred: {e}")

    def _export_tags(self):
        file_path, _ = QFileDialog.getSaveFileName(self, "Export Tags to CSV", f"{self.db_name}_tags.csv", "CSV Files (*.csv)")
        if file_path and csv_service.export_tags_to_csv(self.db_id, file_path):
            CustomInfoDialog.show_info(self, "Export Successful", f"Tags exported to:\n{file_path}")
        elif file_path:
            CustomInfoDialog.show_info(self, "Export Error", "An error occurred during export.")

    def _show_context_menu(self, position):
        menu = QMenu()
        if self.tag_tree.selectedItems():
            menu.addAction("Cut").triggered.connect(self.cut_selected)
            menu.addAction("Copy").triggered.connect(self.copy_selected)
            menu.addAction("Delete").triggered.connect(self._remove_selected_tags)
            menu.addSeparator()
            edit_action = menu.addAction("Edit Properties..."); edit_action.triggered.connect(self._open_edit_tag_dialog)
            edit_action.setEnabled(len(self._get_selected_tag_names()) == 1)
            menu.addSeparator()
        paste_action = menu.addAction("Paste"); paste_action.triggered.connect(self.paste)
        content_type, _ = clipboard_service.get_content(); paste_action.setEnabled(content_type == constants.CLIPBOARD_TYPE_TAG)
        menu.exec(self.tag_tree.viewport().mapToGlobal(position))

    def _on_item_double_clicked(self, item, column):
        if column < 2: self._open_edit_tag_dialog()

    def _handle_edit_key(self):
        if len(self._get_selected_tag_names()) != 1: return
        item = self.tag_tree.currentItem(); column = self.tag_tree.currentColumn()
        if item and column < 2: self._open_edit_tag_dialog();
        else: self.tag_tree.editItem(item, column)

    def _get_selected_tag_names(self):
        return list({item.data(1, Qt.ItemDataRole.UserRole) for item in self.tag_tree.selectedItems()})

    def _open_add_tag_dialog(self):
        dialog = AddTagDialog(self.db_id, self)
        if dialog.exec():
            command = AddTagCommand(self.db_id, dialog.get_final_data())
            command_history_service.add_command(command)

    def _open_edit_tag_dialog(self):
        tag_names = self._get_selected_tag_names()
        if len(tag_names) != 1: return
        tag_name = tag_names[0]
        old_tag_data = tag_data_service.get_tag(self.db_id, tag_name)
        if not old_tag_data: return
        dialog = AddTagDialog(self.db_id, self, edit_data=old_tag_data)
        if dialog.exec():
            new_tag_data = dialog.get_final_data()
            is_old_array = bool(old_tag_data.get('array_dims'))
            is_new_array = bool(new_tag_data.get('array_dims'))
            if is_old_array and is_new_array and old_tag_data.get('array_dims') == new_tag_data.get('array_dims'):
                new_tag_data['value'] = old_tag_data.get('value')
            if new_tag_data != old_tag_data:
                command = UpdateTagCommand(self.db_id, tag_name, new_tag_data)
                command_history_service.add_command(command)

    def _remove_selected_tags(self):
        tag_names = self._get_selected_tag_names()
        if not tag_names: return
        message = f"Are you sure you want to delete '{tag_names[0]}'?" if len(tag_names) == 1 else f"Are you sure you want to delete the {len(tag_names)} selected tags?"
        reply = CustomQuestionDialog.ask(self, "Delete Tag(s)", message)
        if reply == QMessageBox.StandardButton.Yes:
            for name in tag_names:
                command = RemoveTagCommand(self.db_id, name)
                command_history_service.add_command(command)

    def _update_button_states(self):
        selected_count = len(self._get_selected_tag_names())
        self.remove_button.setEnabled(selected_count > 0)
        self.edit_button.setEnabled(selected_count == 1)

    @pyqtSlot(QTreeWidgetItem, int)
    def _on_item_changed(self, item, column):
        if self._is_updating_table: return
        tag_name = item.data(1, Qt.ItemDataRole.UserRole)
        if not tag_name: return
        original_tag_data = tag_data_service.get_tag(self.db_id, tag_name)
        if not original_tag_data: return
        try:
            if column == 2:
                indices = item.data(0, Qt.ItemDataRole.UserRole)
                validated_value = self._parse_and_validate_value(item.text(2), original_tag_data)
                old_value = tag_data_service.get_tag_element_value(self.db_id, tag_name, indices)
                if validated_value != old_value:
                    command = UpdateTagValueCommand(self.db_id, tag_name, indices, validated_value, old_value)
                    command_history_service.add_command(command)
            elif column == 3 and not item.parent():
                new_comment = item.text(3)
                if new_comment != original_tag_data.get('comment'):
                    new_tag_data = copy.deepcopy(original_tag_data); new_tag_data['comment'] = new_comment
                    command = UpdateTagCommand(self.db_id, tag_name, new_tag_data)
                    command_history_service.add_command(command)
        except ValueError as e:
            self.validation_error_occurred.emit(str(e)); self.refresh_table()

    def _parse_and_validate_value(self, value_str, tag_data):
        data_type = tag_data.get('data_type'); value_str = value_str.strip()
        if not value_str:
            if data_type == 'BOOL': return False
            if data_type in ('INT', 'DINT', 'REAL'): return 0
            return ""
        try:
            if data_type in ('INT', 'DINT'): value = int(value_str)
            elif data_type == 'REAL': value = float(value_str)
            elif data_type == 'BOOL':
                if value_str.lower() in ('true', '1'): return True
                if value_str.lower() in ('false', '0'): return False
                raise ValueError("Value must be True, False, 1, or 0.")
            elif data_type == 'STRING': value = value_str
            else: raise ValueError(f"Unknown data type '{data_type}'")
        except (ValueError, TypeError): raise ValueError(f"'{value_str}' is not a valid {data_type} value.")
        if data_type in DATA_TYPE_RANGES and not (DATA_TYPE_RANGES[data_type]["min"] <= value <= DATA_TYPE_RANGES[data_type]["max"]):
            raise ValueError(f"{data_type} value out of range.")
        if data_type == 'STRING' and len(value) > tag_data.get('length', 0):
            raise ValueError(f"String length exceeds defined length.")
        return value

    def _get_item_path(self, item):
        path = []; current = item
        while current: path.insert(0, current.text(0)); current = current.parent()
        return tuple(path)

    def _save_tree_state(self):
        expanded_paths, selected_paths = set(), set()
        iterator = QTreeWidgetItemIterator(self.tag_tree)
        while iterator.value():
            item = iterator.value(); path = self._get_item_path(item)
            if item.isExpanded(): expanded_paths.add(path)
            if item.isSelected(): selected_paths.add(path)
            iterator += 1
        return expanded_paths, selected_paths

    def _restore_tree_state(self, expanded_paths, selected_paths):
        iterator = QTreeWidgetItemIterator(self.tag_tree)
        while iterator.value():
            item = iterator.value(); path = self._get_item_path(item)
            if path in expanded_paths: item.setExpanded(True)
            if path in selected_paths: item.setSelected(True)
            iterator += 1

    @pyqtSlot()
    def refresh_table(self):
        self._is_updating_table = True
        expanded_paths, selected_paths = self._save_tree_state()
        self.tag_tree.clear()
        db = tag_data_service.get_tag_database(self.db_id)
        if not db: self._is_updating_table = False; return
        for tag in db.get('tags', []):
            self._create_tag_tree_item(self.tag_tree, tag)
        self._restore_tree_state(expanded_paths, selected_paths)
        self._is_updating_table = False

    def _create_tag_tree_item(self, parent_widget, tag):
        name = tag.get('name', 'N/A'); data_type = tag.get('data_type', 'N/A')
        comment = tag.get('comment', ''); is_array = bool(tag.get('array_dims'))
        item = QTreeWidgetItem(); item.setText(0, name); item.setText(3, comment)
        item.setData(1, Qt.ItemDataRole.UserRole, name)
        flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
        if is_array:
            dims_str = 'x'.join(map(str, tag.get('array_dims', [])))
            item.setText(1, f"{data_type}[{dims_str}]")
            flags |= Qt.ItemFlag.ItemIsEditable
            self._populate_array_children(item, tag, tag.get('value', []), [])
        else:
            value = str(tag.get('value', ''))
            type_str = f"{data_type}[{tag.get('length')}]" if data_type == 'STRING' else data_type
            item.setText(1, type_str); item.setText(2, value)
            flags |= Qt.ItemFlag.ItemIsEditable
            item.setData(0, Qt.ItemDataRole.UserRole, [])
        item.setFlags(flags)
        parent_widget.addTopLevelItem(item)
        return item

    def _populate_array_children(self, parent_item, tag, data_slice, current_indices):
        if not isinstance(data_slice, list): return
        for i, value in enumerate(data_slice):
            new_indices = current_indices + [i]; name = f"[{i}]"
            child_item = QTreeWidgetItem(); child_item.setText(0, name)
            child_item.setData(0, Qt.ItemDataRole.UserRole, new_indices)
            child_item.setData(1, Qt.ItemDataRole.UserRole, tag['name'])
            flags = Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable
            if isinstance(value, list):
                # Ensure child items have children and are expandable
                child_item.setChildIndicatorPolicy(QTreeWidgetItem.ChildIndicatorPolicy.ShowIndicator)
                self._populate_array_children(child_item, tag, value, new_indices)
            else:
                child_item.setText(2, str(value))
                flags |= Qt.ItemFlag.ItemIsEditable
            child_item.setFlags(flags)
            parent_item.addChild(child_item)

    def has_selection(self): return len(self.tag_tree.selectedItems()) > 0
    def clear_selection(self): self.tag_tree.clearSelection()
    def copy_selected(self): self._copy_selected_tags()
    def cut_selected(self): self._cut_selected_tags()
    def paste(self): self._paste_tags()

    def _copy_selected_tags(self):
        tag_names = self._get_selected_tag_names()
        if not tag_names: return
        tags_data = [copy.deepcopy(tag_data_service.get_tag(self.db_id, name)) for name in tag_names if tag_data_service.get_tag(self.db_id, name)]
        if tags_data: clipboard_service.set_content(constants.CLIPBOARD_TYPE_TAG, tags_data)

    def _cut_selected_tags(self):
        self._copy_selected_tags()
        self._remove_selected_tags()

    def _paste_tags(self):
        content_type, data = clipboard_service.get_content()
        if content_type != constants.CLIPBOARD_TYPE_TAG or not data: return
        tags_to_paste = data if isinstance(data, list) else [data]
        for tag_data in tags_to_paste:
            new_data = copy.deepcopy(tag_data)
            original_name = new_data.get('name', 'Pasted_Tag')
            new_name = original_name
            count = 1
            while not tag_data_service.is_tag_name_unique(self.db_id, new_name):
                new_name = f"{original_name}_{count}"
                count += 1
            new_data['name'] = new_name
            command = AddTagCommand(self.db_id, new_data)
            command_history_service.add_command(command)
