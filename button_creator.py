from __future__ import annotations

import sys
import re
from typing import Callable, Dict, List, Tuple, Any

from PyQt6 import QtCore, QtWidgets, uic
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QWidget,
    QTabWidget,
    QLineEdit,
    QTextEdit,
    QSpinBox,
    QComboBox,
    QFontComboBox,
    QCheckBox,
)


def _natural_key(s: str) -> Tuple[Any, ...]:
    """Sort helper: 'lineEdit_10' after 'lineEdit_9'."""
    parts = re.split(r"(\d+)", s)
    return tuple(int(p) if p.isdigit() else p for p in parts)


Editable = (QLineEdit, QTextEdit, QSpinBox, QComboBox, QFontComboBox)


class MirrorLink:
    """Keeps track of live 'Base → Target' signal connections so we can disconnect later."""
    def __init__(self) -> None:
        # list of (sender, signal_name, slot)
        self._links: List[Tuple[QtCore.QObject, str, Callable]] = []

    def connect(self, sender: QtCore.QObject, signal: QtCore.pyqtBoundSignal, slot: Callable, signal_name: str) -> None:
        signal.connect(slot)
        self._links.append((sender, signal_name, slot))

    def clear(self) -> None:
        # Try to disconnect safely; ignore if already gone
        for sender, signal_name, slot in self._links:
            try:
                getattr(sender, signal_name).disconnect(slot)
            except Exception:
                pass
        self._links.clear()


class StyleDialog(QDialog):
    def __init__(self, ui_path: str, parent=None) -> None:
        super().__init__(parent)
        uic.loadUi(ui_path, self)

        # === Required widgets from your .ui ===
        self.tabWidget: QTabWidget = self.findChild(QTabWidget, "tabWidget")
        self.check_base_eq_hover: QCheckBox = self.findChild(QCheckBox, "checkBox")      # "Text base = Hover"
        self.check_base_eq_click: QCheckBox = self.findChild(QCheckBox, "checkBox_2")    # "Text base = Click"

        # Pages by objectName (from the .ui)
        self.page_base: QWidget = self.findChild(QWidget, "Base")
        self.page_hover: QWidget = self.findChild(QWidget, "Hover")
        self.page_click: QWidget = self.findChild(QWidget, "Click")

        assert self.tabWidget and self.page_base and self.page_hover and self.page_click, "UI not found. Check object names."

        # Build editable lists per page in a stable order
        self.editables_base = self._collect_editables(self.page_base)
        self.editables_hover = self._collect_editables(self.page_hover)
        self.editables_click = self._collect_editables(self.page_click)

        # Sanity: pair counts must match so we can mirror 1:1
        self._assert_same_shape(self.editables_base, self.editables_hover, "Base", "Hover")
        self._assert_same_shape(self.editables_base, self.editables_click, "Base", "Click")

        # One MirrorLink for each target page
        self._link_hover = MirrorLink()
        self._link_click = MirrorLink()

        # Hook checkboxes
        self.check_base_eq_hover.toggled.connect(self._toggle_hover_inherit)
        self.check_base_eq_click.toggled.connect(self._toggle_click_inherit)

        # Initialize to whatever the .ui has checked
        self._toggle_hover_inherit(self.check_base_eq_hover.isChecked())
        self._toggle_click_inherit(self.check_base_eq_click.isChecked())

    # --------------------------
    # Collect & Pairing Helpers
    # --------------------------
    def _collect_editables(self, page: QWidget) -> Dict[str, List[Editable]]:
        """
        Collect editable widgets for a page, grouped by type, sorted by objectName (natural sort).
        We only mirror these types: QLineEdit, QTextEdit, QSpinBox, QComboBox, QFontComboBox.
        """
        get = lambda T: sorted(page.findChildren(T), key=lambda w: _natural_key(w.objectName() or ""))
        return {
            "QLineEdit": get(QLineEdit),
            "QTextEdit": get(QTextEdit),
            "QSpinBox": get(QSpinBox),
            "QComboBox": get(QComboBox),
            "QFontComboBox": get(QFontComboBox),
        }

    def _assert_same_shape(self, a: Dict[str, List[Editable]], b: Dict[str, List[Editable]], aname: str, bname: str) -> None:
        for key in a.keys():
            if len(a[key]) != len(b[key]):
                raise RuntimeError(
                    f"Editable count mismatch for {key}: {aname}={len(a[key])}, {bname}={len(b[key])}.\n"
                    f"Ensure pages have matching fields."
                )

    # --------------------------
    # Mirror (copy + live sync)
    # --------------------------
    def _apply_mirror(self, src: Dict[str, List[Editable]], dst: Dict[str, List[Editable]], link: MirrorLink) -> None:
        """Copy current values from src → dst and wire live updates."""
        link.clear()

        # QLineEdit
        for s, d in zip(src["QLineEdit"], dst["QLineEdit"]):
            d.setText(s.text())
            link.connect(s, s.textChanged, lambda text, tgt=d: tgt.setText(text), "textChanged")

        # QTextEdit
        for s, d in zip(src["QTextEdit"], dst["QTextEdit"]):
            d.setPlainText(s.toPlainText())
            link.connect(s, s.textChanged, lambda tgt=d, srcw=s: tgt.setPlainText(srcw.toPlainText()), "textChanged")

        # QSpinBox
        for s, d in zip(src["QSpinBox"], dst["QSpinBox"]):
            d.setRange(s.minimum(), s.maximum())
            d.setValue(s.value())
            link.connect(s, s.valueChanged, lambda val, tgt=d: tgt.setValue(val), "valueChanged")

        # QComboBox
        for s, d in zip(src["QComboBox"], dst["QComboBox"]):
            # Try to align items by text. If items differ, fallback to index.
            s_items = [s.itemText(i) for i in range(s.count())]
            d_items = [d.itemText(i) for i in range(d.count())]

            if s_items != d_items:
                # Replace target items to match source, preserving current selection by text if possible
                current_text = s.currentText()
                d.clear()
                d.addItems(s_items)
                idx = s_items.index(current_text) if current_text in s_items else s.currentIndex()
                d.setCurrentIndex(idx)
            else:
                d.setCurrentIndex(s.currentIndex())

            link.connect(s, s.currentIndexChanged, lambda idx, tgt=d: tgt.setCurrentIndex(idx), "currentIndexChanged")

        # QFontComboBox
        for s, d in zip(src["QFontComboBox"], dst["QFontComboBox"]):
            d.setCurrentFont(s.currentFont())
            link.connect(s, s.currentFontChanged, lambda font, tgt=d: tgt.setCurrentFont(font), "currentFontChanged")

    def _set_enabled_for_page(self, page_map: Dict[str, List[Editable]], enabled: bool) -> None:
        """Enable/disable all editable widgets on a page."""
        for group in page_map.values():
            for w in group:
                w.setEnabled(enabled)

    # --------------------------
    # Checkbox Handlers
    # --------------------------
    @QtCore.pyqtSlot(bool)
    def _toggle_hover_inherit(self, checked: bool) -> None:
        if checked:
            # Mirror Base → Hover and lock Hover
            self._apply_mirror(self.editables_base, self.editables_hover, self._link_hover)
            self._set_enabled_for_page(self.editables_hover, False)
        else:
            # Unlock Hover and stop mirroring
            self._link_hover.clear()
            self._set_enabled_for_page(self.editables_hover, True)

    @QtCore.pyqtSlot(bool)
    def _toggle_click_inherit(self, checked: bool) -> None:
        if checked:
            # Mirror Base → Click and lock Click
            self._apply_mirror(self.editables_base, self.editables_click, self._link_click)
            self._set_enabled_for_page(self.editables_click, False)
        else:
            # Unlock Click and stop mirroring
            self._link_click.clear()
            self._set_enabled_for_page(self.editables_click, True)


def main() -> None:
    app = QApplication(sys.argv)
    # If the .ui is in the same folder, use the relative path; otherwise set the full path here.
    ui_path = "Base hover click tab.ui"
    dlg = StyleDialog(ui_path)
    dlg.setWindowTitle("Text Style (Base / Hover / Click)")
    dlg.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
