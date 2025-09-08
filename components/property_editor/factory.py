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
import importlib


@dataclass
class EditorAdapter:
    build: Callable[[object], QWidget]
    update_fields: Callable[[QWidget, dict], None]


_EDITOR_DISPATCH = {
    constants.ToolType.BUTTON: ".button_editor",
}


def get_editor(tool_type) -> Optional[EditorAdapter]:
    """Return an adapter for the given ToolType, or None if unknown.

    Uses a dispatch table and imports lazily to avoid circular imports and
    reduce repetition.
    """
    module_suffix = _EDITOR_DISPATCH.get(tool_type)
    if not module_suffix:
        return None
    # Import module lazily using relative import based on current package
    module = importlib.import_module(f"{__package__}{module_suffix}")
    return EditorAdapter(build=module.build, update_fields=module.update_fields)
