from PyQt6.QtCore import QSortFilterProxyModel, Qt


class CommentFilterProxyModel(QSortFilterProxyModel):
    """Proxy model that filters rows if any column contains the filter text."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter_text = ""
        self.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.setDynamicSortFilter(True)

    def set_filter_text(self, text: str) -> None:
        self._filter_text = text.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row: int, source_parent) -> bool:  # noqa: D401
        if not self._filter_text:
            return True
        model = self.sourceModel()
        columns = model.columnCount()
        for col in range(columns):
            idx = model.index(source_row, col, source_parent)
            data = model.data(idx, Qt.ItemDataRole.DisplayRole)
            if data is not None and self._filter_text in str(data).lower():
                return True
        return False
