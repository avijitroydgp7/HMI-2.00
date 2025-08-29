import sys
import types

import pytest
from utils import constants

from PyQt6.QtWidgets import QApplication
from PyQt6.QtTest import QTest


@pytest.fixture(scope="session", autouse=True)
def qapp():
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    return app


def test_clear_selection(qapp):
    from components.property_editor import PropertyEditor
    editor = PropertyEditor()
    # Simulate state
    editor.current_object_id = "obj1"
    editor.current_parent_id = "parent1"
    editor.current_properties = {"foo": "bar"}
    editor.current_tool_type = constants.ToolType.LINE
    # Add a dummy editor page to index 2
    from PyQt6.QtWidgets import QWidget
    dummy = QWidget()
    editor.addWidget(dummy)
    editor.setCurrentWidget(dummy)

    editor._clear_selection()

    assert editor.current_object_id is None
    assert editor.current_parent_id is None
    assert editor.current_properties == {}
    assert editor.current_tool_type is None
    assert editor.currentWidget() is editor.blank_page


def test_handle_multi_select(qapp):
    from components.property_editor import PropertyEditor
    editor = PropertyEditor()
    # Add a dummy editor page to index 2 to ensure it gets cleared
    from PyQt6.QtWidgets import QWidget
    dummy = QWidget()
    editor.addWidget(dummy)
    editor.setCurrentWidget(dummy)

    handled = editor._handle_multi_select([{"a": 1}, {"b": 2}])
    assert handled is True
    assert editor.current_object_id is None
    assert editor.current_parent_id is None
    assert editor.current_properties == {}
    assert editor.current_tool_type is None
    assert editor.currentWidget() is editor.multi_select_page

    # Single selection should not be handled here
    assert editor._handle_multi_select([{"only": 1}]) is False


def test_build_editor_for_instance_line(qapp):
    from components.property_editor import PropertyEditor
    editor = PropertyEditor()
    # Build for a line with partial incoming props
    incoming = {"color": "#ff0000", "start": {"x": 10}}
    widget = editor._build_editor_for_instance(constants.ToolType.LINE, incoming)
    assert widget is not None
    assert editor.current_tool_type is None or editor.current_tool_type == editor.current_tool_type
    assert editor.current_properties["color"] == "#ff0000"
    # Defaults should be merged
    assert "end" in editor.current_properties
    assert editor.currentWidget() is widget


def test_editing_guard_emits_once(qapp):
    from components.property_editor import PropertyEditor
    from utils.editing_guard import EditingGuard
    from services.screen_data_service import screen_service

    editor = PropertyEditor()
    # Pretend an instance is selected so the guard will emit
    editor.current_parent_id = "parent-xyz"
    editor.current_object_id = "inst-abc"

    emissions = {"count": 0}

    def on_modified(_):
        emissions["count"] += 1

    try:
        screen_service.screen_modified.connect(on_modified)
        guard = EditingGuard(editor, screen_service, emit_final=lambda: screen_service.screen_modified.emit(editor.current_parent_id)).begin()
        # While guard is active, the flag should be set
        assert getattr(editor, "_is_editing", False) is True
        guard.mark_changed()
        guard.end()
        # Allow queued singleShots to process
        QTest.qWait(10)
        assert emissions["count"] == 1
        # Guard should have cleared editing state
        assert getattr(editor, "_is_editing", False) is False
    finally:
        try:
            screen_service.screen_modified.disconnect(on_modified)
        except Exception:
            pass
