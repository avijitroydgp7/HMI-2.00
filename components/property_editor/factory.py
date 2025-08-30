"""Factory for tool-specific property editors.

Each editor module provides two functions:
- build(host: PropertyEditor) -> QWidget
- update_fields(widget: QWidget, props: dict) -> None

This factory exposes a simple adapter with both callables.
"""

from dataclasses import dataclass
from typing import Callable, Optional
from PyQt6.QtWidgets import QWidget
from utils import constants


@dataclass
class EditorAdapter:
    build: Callable[[object], QWidget]
    update_fields: Callable[[QWidget, dict], None]


def get_editor(tool_type) -> Optional[EditorAdapter]:
    """Return an adapter for the given ToolType, or None if unknown.

    Import is lazy to avoid circular imports.
    """
    if tool_type == constants.ToolType.BUTTON:
        from . import button_editor as m

        return EditorAdapter(build=m.build, update_fields=m.update_fields)
    if tool_type == constants.ToolType.LINE:
        from . import line_editor as m

        return EditorAdapter(build=m.build, update_fields=m.update_fields)
    if tool_type == constants.ToolType.TEXT:
        from . import text_editor as m

        return EditorAdapter(build=m.build, update_fields=m.update_fields)
    if tool_type == constants.ToolType.POLYGON:
        from . import polygon_editor as m

        return EditorAdapter(build=m.build, update_fields=m.update_fields)
    if tool_type == constants.ToolType.IMAGE:
        from . import image_editor as m

        return EditorAdapter(build=m.build, update_fields=m.update_fields)
    if tool_type == constants.ToolType.SCALE:
        from . import scale_editor as m

        return EditorAdapter(build=m.build, update_fields=m.update_fields)
    return None

