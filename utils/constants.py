"""
Central constants and enums used across the application.

- Introduces `ToolType` enum to replace scattered string identifiers.
- Provides helpers to convert to/from strings for serialization.
"""

from enum import Enum
from typing import Optional, Union

# --- MIME Types ---
MIME_TYPE_SCREEN_ID = 'application/x-screen-id'

# --- Clipboard Content Types ---
CLIPBOARD_TYPE_HMI_OBJECTS = 'hmi_objects'
CLIPBOARD_TYPE_TAG = 'tag'
CLIPBOARD_TYPE_TAG_DATABASE = 'tag_database'
CLIPBOARD_TYPE_SCREEN = 'screen'
CLIPBOARD_TYPE_COMMENT_GROUP = 'comment_group'


class ToolType(str, Enum):
    """Enumeration of all design/runtime tool identifiers.

    Subclasses ``str`` so values behave like strings for Qt/JSON,
    while giving type-safety and autocomplete throughout the codebase.
    """
    SELECT = 'select'
    PATH_EDIT = 'path_edit'

    BUTTON = 'button'
    TEXT = 'text'
    LINE = 'line'
    FREEFORM = 'freeform'
    RECT = 'rect'
    POLYGON = 'polygon'
    CIRCLE = 'circle'
    ARC = 'arc'
    SECTOR = 'sector'
    TABLE = 'table'
    SCALE = 'scale'
    IMAGE = 'image'
    DXF = 'dxf'


# Helper alias type used in signatures
ToolLike = Union[ToolType, str]


def tool_type_to_str(tool: Optional[ToolLike]) -> str:
    """Return the string identifier for a tool enum or string input.

    - For ``ToolType`` values, returns the underlying ``value``.
    - For strings, returns the string as-is.
    - For ``None``, returns an empty string.
    """
    if tool is None:
        return ''
    if isinstance(tool, ToolType):
        return tool.value
    return str(tool)


def tool_type_from_str(value: Optional[ToolLike]) -> Optional[ToolType]:
    """Parse a tool type from a string or return the enum unchanged.

    Returns ``None`` if the input is falsy or doesn't match any known tool.
    """
    if not value:
        return None
    if isinstance(value, ToolType):
        return value
    try:
        return ToolType(str(value))
    except ValueError:
        return None


# --- Project Tree Item Types ---
PROJECT_TREE_ITEM_PROJECT_INFO = 'project_info'
PROJECT_TREE_ITEM_SYSTEM = 'system'
PROJECT_TREE_ITEM_SCREENS = 'screens'
PROJECT_TREE_ITEM_TAGS_ROOT = 'tags_root'
# Root node for comment tables in the Project tree
PROJECT_TREE_ITEM_COMMENT_ROOT = 'comment_root'
# Individual comment table/group node in the Project tree
PROJECT_TREE_ITEM_COMMENT_GROUP = 'comment_group'
