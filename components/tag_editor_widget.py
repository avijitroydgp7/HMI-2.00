# components/tag_editor_widget.py
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeView,
    QPushButton, QAbstractItemView, QStyledItemDelegate,
    QLineEdit, QMenu, QFileDialog, QHeaderView
)
from PyQt6.QtCore import (
    Qt, pyqtSlot, pyqtSignal, QSortFilterProxyModel,
    QModelIndex, QItemSelectionModel, QTimer, QRegularExpression
)
from PyQt6.QtGui import (
    QKeyEvent, QStandardItemModel, QStandardItem,
    QIntValidator, QDoubleValidator, QRegularExpressionValidator
)
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
from dialogs.info_dialog import CustomInfoDialog
from dialogs.question_dialog import CustomQuestionDialog
from PyQt6.QtWidgets import QMessageBox
from utils import constants


DATA_TYPE_RANGES = {
    "INT": {"min": -32768, "max": 32767},
    "DINT": {"min": -2147483648, "max": 2147483647},
    "REAL": {"min": -3.4028235e+38, "max": 3.4028235e+38},
}

class TagTreeDelegate(QStyledItemDelegate):
    def __init__(self, parent, db_id):
        super().__init__(parent)
        self.db_id = db_id

    def createEditor(self, parent, option, index):
        editor = QLineEdit(parent)
        editor.setFrame(False)
        editor.setContentsMargins(0, 0, 0, 0)
        editor.setTextMargins(0, 0, 0, 0)

        tag_name = index.siblingAtColumn(1).data()
        tag = tag_data_service.get_tag(self.db_id, tag_name) if tag_name else None

        if tag:
            data_type = tag.get('data_type')
            if data_type in ("INT", "DINT"):
                rng = DATA_TYPE_RANGES.get(data_type)
                if rng:
                    editor.setValidator(QIntValidator(rng["min"], rng["max"], editor))
            elif data_type == "REAL":
                rng = DATA_TYPE_RANGES.get("REAL")
                if rng:
                    editor.setValidator(QDoubleValidator(rng["min"], rng["max"], 100, editor))
            elif data_type == "BOOL":
                regex = QRegularExpression("^(true|false|0|1)$", QRegularExpression.PatternOption.CaseInsensitiveOption)
                editor.setValidator(QRegularExpressionValidator(regex, editor))
            elif data_type == "STRING":
                editor.setMaxLength(tag.get('length', 0))

        return editor

    def setEditorData(self, editor, index):
        editor.setText(str(index.model().data(index, Qt.ItemDataRole.EditRole)))

    def setModelData(self, editor, model, index):
        model.setData(index, editor.text(), Qt.ItemDataRole.EditRole)

class TagTreeWidget(QTreeView):

    delete_pressed = pyqtSignal()
    edit_pressed = pyqtSignal()

    def edit(self, index, trigger, event=None):
        if index.column() < 2:
            return False
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


class TagFilterProxyModel(QSortFilterProxyModel):
    """Proxy model to filter tag tree columns without Python iteration."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._name_filter = ""
        self._type_filter = ""
        self._comment_filter = ""
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)

    def set_filters(self, name: str, type_: str, comment: str) -> None:
        self._name_filter = name.lower()
        self._type_filter = type_.lower()
        self._comment_filter = comment.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:  # type: ignore[override]
        model = self.sourceModel()
        if model is None:
            return True

        name_index = model.index(source_row, 0, source_parent)
        type_index = model.index(source_row, 1, source_parent)
        comment_index = model.index(source_row, 3, source_parent)

        name_data = (model.data(name_index) or "").lower()
        type_data = (model.data(type_index) or "").lower()
        comment_data = (model.data(comment_index) or "").lower()

        if self._name_filter and self._name_filter not in name_data:
            return False
        if self._type_filter and self._type_filter not in type_data:
            return False
        if self._comment_filter and self._comment_filter not in comment_data:
            return False
        return True

class TagEditorWidget(QWidget):
    validation_error_occurred = pyqtSignal(str)
    selection_changed = pyqtSignal()

    def __init__(self, db_id: str, db_name: str, parent=None):
        super().__init__(parent)
        self.db_id = db_id; self.db_name = db_name; self._is_updating_table = False
        self.setObjectName("TagEditorWidget")

        layout = QVBoxLayout(self); layout.setContentsMargins(5, 5, 5, 5); layout.setSpacing(5)
        
        toolbar_layout = QHBoxLayout()
        add_icon = IconManager.create_animated_icon('fa5s.plus-circle')
        add_button = QPushButton(add_icon.icon, " Add Tag"); add_icon.add_target(add_button); add_button.setObjectName("TagButton"); add_button.clicked.connect(self._open_add_tag_dialog)
        edit_icon = IconManager.create_animated_icon('fa5s.edit')
        self.edit_button = QPushButton(edit_icon.icon, " Edit Tag"); edit_icon.add_target(self.edit_button); self.edit_button.setObjectName("TagButton"); self.edit_button.clicked.connect(self._open_edit_tag_dialog)
        remove_icon = IconManager.create_animated_icon('fa5s.minus-circle')
        self.remove_button = QPushButton(remove_icon.icon, " Remove Tag"); remove_icon.add_target(self.remove_button); self.remove_button.setObjectName("TagButton"); self.remove_button.clicked.connect(self._remove_selected_tags)
        import_icon = IconManager.create_animated_icon('fa5s.file-import')
        import_button = QPushButton(import_icon.icon, " Import"); import_icon.add_target(import_button); import_button.setObjectName("TagButton"); import_button.clicked.connect(self._import_tags)
        export_icon = IconManager.create_animated_icon('fa5s.file-export')
        export_button = QPushButton(export_icon.icon, " Export"); export_icon.add_target(export_button); export_button.setObjectName("TagButton"); export_button.clicked.connect(self._export_tags)
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
        self.tag_tree.setObjectName("TagTree")
        self.tag_tree.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.tag_tree.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.tag_tree.setAlternatingRowColors(True)
        self.tag_tree.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked
            | QAbstractItemView.EditTrigger.SelectedClicked
            | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.tag_tree.setItemDelegate(TagTreeDelegate(self.tag_tree, self.db_id))
        self.tag_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        # Model and proxy for efficient filtering
        self._model = QStandardItemModel(0, 4, self.tag_tree)
        self._model.setHorizontalHeaderLabels(["Tag Name", "Data Type", "Live Value", "Comment"])
        self._proxy_model = TagFilterProxyModel(self.tag_tree)
        self._proxy_model.setSourceModel(self._model)
        self.tag_tree.setModel(self._proxy_model)
        self.tag_tree.setSortingEnabled(True)
        header = self.tag_tree.header()
        header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        layout.addWidget(self.tag_tree)

        # Cache to track current tags for incremental updates
        self._tags_cache: dict[str, dict] = {}

        tag_data_service.tags_changed.connect(self._schedule_refresh)
        self._model.itemChanged.connect(self._on_item_changed)
        self.tag_tree.doubleClicked.connect(self._on_item_double_clicked)
        self.tag_tree.selectionModel().selectionChanged.connect(lambda *_: self._update_button_states())
        self.tag_tree.selectionModel().selectionChanged.connect(lambda *_: self.selection_changed.emit())
        self.tag_tree.customContextMenuRequested.connect(self._show_context_menu)
        self.tag_tree.delete_pressed.connect(self._remove_selected_tags)
        self.tag_tree.edit_pressed.connect(self._handle_edit_key)
        
        self.refresh_table()
        self._update_button_states()

    def _filter_tree(self):
        """Update proxy model filters from UI inputs."""
        self._proxy_model.set_filters(
            self.name_filter_input.text(),
            self.type_filter_input.text(),
            self.comment_filter_input.text(),
        )

    def _schedule_refresh(self):
        """Refresh the table on the next event loop tick to avoid model churn during edits."""
        QTimer.singleShot(0, self.refresh_table)

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
        if self.tag_tree.selectionModel().hasSelection():
            menu.addAction("Cut").triggered.connect(self.cut_selected)
            menu.addAction("Copy").triggered.connect(self.copy_selected)
            menu.addAction("Delete").triggered.connect(self._remove_selected_tags)
            menu.addSeparator()
            edit_action = menu.addAction("Edit Properties...")
            edit_action.triggered.connect(self._open_edit_tag_dialog)
            edit_action.setEnabled(len(self._get_selected_tag_names()) == 1)
            menu.addSeparator()
        paste_action = menu.addAction("Paste"); paste_action.triggered.connect(self.paste)
        content_type, _ = clipboard_service.get_content(); paste_action.setEnabled(content_type == constants.CLIPBOARD_TYPE_TAG)
        menu.exec(self.tag_tree.viewport().mapToGlobal(position))

    def _on_item_double_clicked(self, index: QModelIndex):
        if index.column() < 2:
            self._open_edit_tag_dialog()

    def _handle_edit_key(self):
        if len(self._get_selected_tag_names()) != 1:
            return
        index = self.tag_tree.currentIndex()
        if index.isValid() and index.column() < 2:
            self._open_edit_tag_dialog()
        else:
            self.tag_tree.edit(index, QAbstractItemView.EditTrigger.EditKeyPressed, None)

    def _get_selected_tag_names(self):
        names = set()
        for proxy_index in self.tag_tree.selectionModel().selectedRows():
            source_index = self._proxy_model.mapToSource(proxy_index)
            name = self._model.itemFromIndex(source_index.siblingAtColumn(1)).data(Qt.ItemDataRole.UserRole)
            if name:
                names.add(name)
        return list(names)

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
            if (
                is_old_array
                and is_new_array
                and old_tag_data.get('data_type') == new_tag_data.get('data_type')
                and old_tag_data.get('array_dims') == new_tag_data.get('array_dims')
            ):
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

    @pyqtSlot(QStandardItem)
    def _on_item_changed(self, item: QStandardItem):
        if self._is_updating_table:
            return
        index = item.index()
        column = index.column()
        tag_name = self._model.itemFromIndex(index.siblingAtColumn(1)).data(Qt.ItemDataRole.UserRole)
        if not tag_name:
            return
        original_tag_data = tag_data_service.get_tag(self.db_id, tag_name)
        if not original_tag_data:
            return
        if column == 2:
            indices = self._model.itemFromIndex(index.siblingAtColumn(0)).data(Qt.ItemDataRole.UserRole) or []
            old_value = tag_data_service.get_tag_element_value(self.db_id, tag_name, indices)
            try:
                validated_value = self._parse_and_validate_value(item.text(), original_tag_data)
                if validated_value != old_value:
                    command = UpdateTagValueCommand(self.db_id, tag_name, indices, validated_value, old_value)
                    command_history_service.add_command(command)
            except ValueError as e:
                self.validation_error_occurred.emit(str(e))
                self._is_updating_table = True
                item.setText(str(old_value))
                self._is_updating_table = False
        elif column == 3 and not index.parent().isValid():
            new_comment = item.text()
            if new_comment != original_tag_data.get('comment'):
                new_tag_data = copy.deepcopy(original_tag_data)
                new_tag_data['comment'] = new_comment
                command = UpdateTagCommand(self.db_id, tag_name, new_tag_data)
                command_history_service.add_command(command)

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

    def _get_item_path(self, index: QModelIndex):
        path = []
        current = index
        model = self._model
        while current.isValid():
            path.insert(0, model.data(current))
            current = current.parent()
        return tuple(path)

    def _save_tree_state(self):
        expanded_paths, selected_paths = set(), set()

        def recurse(parent_index: QModelIndex, path):
            model = self._model
            for row in range(model.rowCount(parent_index)):
                index = model.index(row, 0, parent_index)
                new_path = path + (model.data(index),)
                proxy_index = self._proxy_model.mapFromSource(index)
                if self.tag_tree.isExpanded(proxy_index):
                    expanded_paths.add(new_path)
                if self.tag_tree.selectionModel().isSelected(proxy_index):
                    selected_paths.add(new_path)
                recurse(index, new_path)

        recurse(QModelIndex(), tuple())
        return expanded_paths, selected_paths

    def _restore_tree_state(self, expanded_paths, selected_paths):
        def recurse(parent_index: QModelIndex, path):
            model = self._model
            for row in range(model.rowCount(parent_index)):
                index = model.index(row, 0, parent_index)
                new_path = path + (model.data(index),)
                proxy_index = self._proxy_model.mapFromSource(index)
                if new_path in expanded_paths:
                    self.tag_tree.setExpanded(proxy_index, True)
                if new_path in selected_paths:
                    self.tag_tree.selectionModel().select(
                        proxy_index, QItemSelectionModel.SelectionFlag.Select | QItemSelectionModel.SelectionFlag.Rows
                    )
                recurse(index, new_path)

        recurse(QModelIndex(), tuple())

    def _get_tag_row_map(self) -> dict[str, int]:
        """Map top-level tag names to their row indices."""
        return {
            self._model.item(row, 0).text(): row
            for row in range(self._model.rowCount())
            if self._model.item(row, 0) is not None
        }

    @pyqtSlot()
    def refresh_table(self):
        self._is_updating_table = True
        expanded_paths, selected_paths = self._save_tree_state()

        db = tag_data_service.get_tag_database(self.db_id)
        if not db:
            self._is_updating_table = False
            return

        new_tags = {t.get('name', 'N/A'): t for t in db.get('tags', [])}
        current_rows = self._get_tag_row_map()

        # Remove tags that no longer exist
        rows_to_remove = sorted(
            (current_rows[name] for name in current_rows.keys() - new_tags.keys()),
            reverse=True,
        )
        for row in rows_to_remove:
            self._model.removeRow(row)

        # Refresh mapping after removals
        current_rows = self._get_tag_row_map()

        # Add new tags or update changed ones
        for name, tag in new_tags.items():
            if name in current_rows:
                if self._tags_cache.get(name) != tag:
                    row = current_rows[name]
                    self._model.removeRow(row)
                    self._create_tag_tree_item(tag, row)
            else:
                self._create_tag_tree_item(tag)

        self._tags_cache = new_tags
        self._restore_tree_state(expanded_paths, selected_paths)
        self._is_updating_table = False

    def _create_tag_tree_item(self, tag, row: int | None = None):
        name = tag.get('name', 'N/A')
        data_type = tag.get('data_type', 'N/A')
        comment = tag.get('comment', '')
        is_array = bool(tag.get('array_dims'))

        name_item = QStandardItem(name)
        type_item = QStandardItem()
        value_item = QStandardItem()
        comment_item = QStandardItem(comment)

        name_item.setEditable(False)
        type_item.setEditable(False)
        comment_item.setEditable(True)
        type_item.setData(name, Qt.ItemDataRole.UserRole)
        name_item.setData([], Qt.ItemDataRole.UserRole)

        if is_array:
            dims_str = 'x'.join(map(str, tag.get('array_dims', [])))
            type_item.setText(f"{data_type}[{dims_str}]")
            value_item.setEditable(False)
            self._populate_array_children(name_item, tag, tag.get('value', []), [])
        else:
            value = str(tag.get('value', ''))
            type_str = f"{data_type}[{tag.get('length')}]" if data_type == 'STRING' else data_type
            type_item.setText(type_str)
            value_item.setText(value)
            value_item.setEditable(True)

        items = [name_item, type_item, value_item, comment_item]
        if row is None:
            self._model.appendRow(items)
        else:
            self._model.insertRow(row, items)

    def _populate_array_children(self, parent_item, tag, data_slice, current_indices):
        if not isinstance(data_slice, list):
            return
        for i, value in enumerate(data_slice):
            new_indices = current_indices + [i]
            name_str = f"[{i}]"
            name_item = QStandardItem(name_str)
            type_item = QStandardItem()
            value_item = QStandardItem()
            comment_item = QStandardItem()

            name_item.setEditable(False)
            type_item.setEditable(False)
            comment_item.setEditable(False)
            name_item.setData(new_indices, Qt.ItemDataRole.UserRole)
            type_item.setData(tag['name'], Qt.ItemDataRole.UserRole)

            if isinstance(value, list):
                value_item.setEditable(False)
                parent_item.appendRow([name_item, type_item, value_item, comment_item])
                self._populate_array_children(name_item, tag, value, new_indices)
            else:
                value_item.setText(str(value))
                value_item.setEditable(True)
                parent_item.appendRow([name_item, type_item, value_item, comment_item])

    def has_selection(self):
        return self.tag_tree.selectionModel().hasSelection()

    def clear_selection(self):
        self.tag_tree.clearSelection()
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
