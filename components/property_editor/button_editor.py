from __future__ import annotations

import copy
from typing import Dict

from PyQt6.QtWidgets import QWidget

from services.command_history_service import command_history_service
from services.commands import UpdateChildPropertiesCommand

from tools import button as button_tool
from tools.button.button_properties_dialog import ButtonPropertiesWidget


def build(host) -> QWidget:
    """Build the button property editor using :class:`ButtonPropertiesWidget`."""

    widget = ButtonPropertiesWidget(host.current_properties)

    def _on_props_changed(new_props: Dict) -> None:
        guard = host._begin_edit()
        try:
            if new_props != host.current_properties:
                if host.current_object_id:
                    command = UpdateChildPropertiesCommand(
                        host.current_parent_id,
                        host.current_object_id,
                        new_props,
                        host.current_properties,
                    )
                    command_history_service.add_command(command)
                    guard.mark_changed()
                else:
                    button_tool.set_default_properties(new_props)
                host.current_properties = copy.deepcopy(new_props)
        finally:
            guard.end()

    widget.properties_changed.connect(_on_props_changed)
    return widget


def update_fields(editor: ButtonPropertiesWidget, props: dict) -> None:
    """Refresh the editor from ``props``."""

    editor.set_properties(props)

