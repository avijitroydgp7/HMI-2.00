from __future__ import annotations

from typing import Any, Dict, List, Optional

from PyQt6.QtCore import QAbstractTableModel, QModelIndex, Qt

from .actions.constants import ActionType, TriggerMode


class ButtonActionsModel(QAbstractTableModel):
    """Table model that exposes button actions for a QTableView.

    Columns:
    0. Serial (1-based)
    1. Action Type (capitalized)
    2. Target Tag (formatted)
    3. Trigger (formatted)
    4. Conditional Reset (formatted)
    5. Details (from action data)
    """

    HEADERS = [
        "#",
        "Action Type",
        "Target Tag",
        "Trigger",
        "Conditional Reset",
        "Details",
    ]

    def __init__(self, actions: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        # Keep a reference to the mutable list owned by the dialog
        self._actions: List[Dict[str, Any]] = actions

    # Basic model API -------------------------------------------------
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: D401
        return 0 if parent.isValid() else len(self._actions)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:  # noqa: D401
        return 0 if parent.isValid() else len(self.HEADERS)

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.ItemDataRole.DisplayRole):
        if role == Qt.ItemDataRole.DisplayRole and orientation == Qt.Orientation.Horizontal:
            if 0 <= section < len(self.HEADERS):
                return self.HEADERS[section]
        return super().headerData(section, orientation, role)

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole):  # noqa: D401
        if not index.isValid():
            return None
        row = index.row()
        col = index.column()
        if row < 0 or row >= len(self._actions):
            return None
        action = self._actions[row]

        # Lazy role handling: only compute strings for display/tooltip roles
        if role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole):
            if col == 0:
                return str(row + 1)
            if col == 1:
                return str(action.get("action_type", "")).capitalize()
            if col == 2:
                return self._format_operand_for_display(action.get("target_tag"))
            if col == 3:
                return self._format_trigger_for_display(action.get("trigger"))
            if col == 4:
                return self._format_conditional_reset_for_display(action.get("conditional_reset"))
            if col == 5:
                return action.get("details", "")
            return None

        if role == Qt.ItemDataRole.ToolTipRole:
            # Provide details (if available) as tooltip to aid discoverability
            return action.get("details", "")

        if role == Qt.ItemDataRole.UserRole:
            # Expose raw action dict for convenience
            return action

        if role == Qt.ItemDataRole.TextAlignmentRole:
            if col == 0:
                return int(Qt.AlignmentFlag.AlignCenter)
            return int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft)

        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:  # noqa: D401
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    # Mutating helpers -----------------------------------------------
    def refresh(self) -> None:
        """Reset the model to reflect external changes to the list."""
        self.beginResetModel()
        self.endResetModel()

    def insert_action(self, row: int, action: Dict[str, Any]) -> None:
        row = max(0, min(row, len(self._actions)))
        self.beginInsertRows(QModelIndex(), row, row)
        self._actions.insert(row, action)
        self.endInsertRows()
        self._emit_serials_changed(from_row=row)

    def update_action(self, row: int, action: Dict[str, Any]) -> None:
        if 0 <= row < len(self._actions):
            self._actions[row] = action
            top_left = self.index(row, 0)
            bottom_right = self.index(row, self.columnCount() - 1)
            self.dataChanged.emit(top_left, bottom_right, [
                Qt.ItemDataRole.DisplayRole,
                Qt.ItemDataRole.ToolTipRole,
                Qt.ItemDataRole.UserRole,
            ])

    def remove_action(self, row: int) -> None:
        if 0 <= row < len(self._actions):
            self.beginRemoveRows(QModelIndex(), row, row)
            self._actions.pop(row)
            self.endRemoveRows()
            self._emit_serials_changed(from_row=row)

    def move_action(self, source_row: int, dest_row: int) -> None:
        if source_row == dest_row:
            return
        if not (0 <= source_row < len(self._actions)):
            return
        dest_row = max(0, min(dest_row, len(self._actions) - 1))
        if dest_row == source_row:
            return

        # Compute destinationRow for beginMoveRows (insert before)
        destination_row_param = dest_row if dest_row < source_row else dest_row + 1
        if not self.beginMoveRows(QModelIndex(), source_row, source_row, QModelIndex(), destination_row_param):
            # Fallback to reset if move could not start
            self.refresh()
            return
        item = self._actions.pop(source_row)
        self._actions.insert(dest_row, item)
        self.endMoveRows()
        self._emit_serials_changed(min(source_row, dest_row))

    def duplicate_action(self, row: int, action_copy: Dict[str, Any]) -> None:
        self.insert_action(row + 1, action_copy)

    # Formatting helpers ---------------------------------------------
    def _format_operand_for_display(self, data: Optional[Dict]) -> str:
        if not data:
            return "N/A"
        # Direct tag structure (db_name/tag_name)
        if isinstance(data, dict) and "db_name" in data and "tag_name" in data:
            db_name = data.get("db_name", "??")
            tag_name = data.get("tag_name", "??")
            indices = data.get("indices", []) or []
            index_str = "".join(
                f"[{self._format_operand_for_display({'main_tag': idx})}]" for idx in indices
            )
            return f"[{db_name}]::{tag_name}{index_str}"

        main_tag = data.get("main_tag") if isinstance(data, dict) else None
        if not main_tag:
            return "N/A"
        source = main_tag.get("source")
        value = main_tag.get("value")
        if source == "constant":
            return str(value)
        if source == "tag" and isinstance(value, dict):
            db_name = value.get("db_name", "??")
            tag_name = value.get("tag_name", "??")
            indices = data.get("indices", []) or []
            index_str = "".join(
                f"[{self._format_operand_for_display({'main_tag': idx})}]" for idx in indices
            )
            return f"[{db_name}]::{tag_name}{index_str}"
        return "N/A"

    def _format_trigger_for_display(self, trigger_data: Optional[Dict]) -> str:
        if not trigger_data:
            return ""
        mode = trigger_data.get("mode", TriggerMode.ORDINARY.value)
        if mode == TriggerMode.ORDINARY.value:
            return ""
        if mode == TriggerMode.ON.value:
            tag_data = trigger_data.get("tag")
            return f"ON = {self._format_operand_for_display(tag_data)}" if tag_data else "ON"
        if mode == TriggerMode.OFF.value:
            tag_data = trigger_data.get("tag")
            return f"OFF = {self._format_operand_for_display(tag_data)}" if tag_data else "OFF"
        if mode == TriggerMode.RANGE.value:
            operator = trigger_data.get("operator", "==")
            operand1 = trigger_data.get("operand1")
            if operand1:
                operand1_display = self._format_operand_for_display(operand1)
                if operator in ["between", "outside"]:
                    lower = trigger_data.get("lower_bound")
                    upper = trigger_data.get("upper_bound")
                    if lower and upper:
                        lower_display = self._format_operand_for_display(lower)
                        upper_display = self._format_operand_for_display(upper)
                        return f"RANGE {operand1_display} {operator} [{lower_display}, {upper_display}]"
                else:
                    operand2 = trigger_data.get("operand2")
                    if operand2:
                        operand2_display = self._format_operand_for_display(operand2)
                        return f"RANGE {operand1_display} {operator} {operand2_display}"
                    return f"RANGE {operand1_display} {operator}"
            return "RANGE"
        return mode

    def _format_conditional_reset_for_display(self, conditional_data: Optional[Dict]) -> str:
        if not conditional_data:
            return ""
        operator = conditional_data.get("operator", "==")
        operand1 = conditional_data.get("operand1")
        if operand1:
            operand1_display = self._format_operand_for_display(operand1)
            if operator in ["between", "outside"]:
                lower = conditional_data.get("lower_bound")
                upper = conditional_data.get("upper_bound")
                if lower and upper:
                    lower_display = self._format_operand_for_display(lower)
                    upper_display = self._format_operand_for_display(upper)
                    return f"COND {operand1_display} {operator} [{lower_display}, {upper_display}]"
            else:
                operand2 = conditional_data.get("operand2")
                if operand2:
                    operand2_display = self._format_operand_for_display(operand2)
                    return f"COND {operand1_display} {operator} {operand2_display}"
                return f"COND {operand1_display} {operator}"
        return "COND"

    # Internal utilities ---------------------------------------------
    def _emit_serials_changed(self, from_row: int = 0) -> None:
        if self.rowCount() == 0:
            return
        top_left = self.index(max(0, from_row), 0)
        bottom_right = self.index(self.rowCount() - 1, 0)
        self.dataChanged.emit(top_left, bottom_right, [Qt.ItemDataRole.DisplayRole])

