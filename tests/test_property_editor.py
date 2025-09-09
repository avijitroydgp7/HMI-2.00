import os
import copy
from PyQt6.QtWidgets import QApplication

import sys
from pathlib import Path

# Ensure repository root on path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from components.property_editor import PropertyEditor
from services import screen_data_service
from services.command_history_service import command_history_service
from tools import button as button_tool

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
app = QApplication([])

def setup_screen():
    screen_service = screen_data_service.screen_service
    screen_service.clear_all()
    screen_id = screen_service._perform_add_screen({"name": "test", "children": []})
    inst = {
        "instance_id": "btn1",
        "tool_type": "button",
        "position": {"x": 5, "y": 5},
        "properties": button_tool.get_default_properties(),
    }
    screen_service._perform_add_child(screen_id, copy.deepcopy(inst))
    return screen_id, inst

def test_geometry_edits_emit_commands():
    screen_id, inst = setup_screen()
    editor = PropertyEditor()
    editor.set_current_object(screen_id, copy.deepcopy(inst))

    command_history_service.clear()
    editor._pos_x_spin.setValue(10)
    stored = screen_data_service.screen_service.get_child_instance(screen_id, "btn1")
    assert stored["position"]["x"] == 10
    assert command_history_service.can_undo()

    command_history_service.clear()
    editor._width_spin.setValue(150)
    stored = screen_data_service.screen_service.get_child_instance(screen_id, "btn1")
    assert stored["properties"]["size"]["width"] == 150
    assert command_history_service.can_undo()
