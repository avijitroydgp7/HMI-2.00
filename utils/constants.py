# utils/constants.py
# A central place for all constant values used throughout the application.

# --- MIME Types ---
MIME_TYPE_SCREEN_ID = 'application/x-screen-id'

# --- Clipboard Content Types ---
CLIPBOARD_TYPE_HMI_OBJECTS = 'hmi_objects'
CLIPBOARD_TYPE_TAG = 'tag'
CLIPBOARD_TYPE_TAG_DATABASE = 'tag_database'
CLIPBOARD_TYPE_SCREEN = 'screen'

# --- Tool Names ---
TOOL_SELECT = 'select'
TOOL_BUTTON = 'button'
TOOL_TEXT = 'text'
TOOL_LINE = 'line'
TOOL_FREEFORM = 'freeform'
TOOL_RECT = 'rect'
TOOL_POLYGON = 'polygon'
TOOL_CIRCLE = 'circle'
TOOL_ARC = 'arc'
TOOL_SECTOR = 'sector'
TOOL_TABLE = 'table'
TOOL_SCALE = 'scale'
TOOL_IMAGE = 'image'
TOOL_DXF = 'dxf'
TOOL_PATH_EDIT = 'path_edit'
# --- Project Tree Item Types ---
PROJECT_TREE_ITEM_PROJECT_INFO = 'project_info'
PROJECT_TREE_ITEM_SYSTEM = 'system'
PROJECT_TREE_ITEM_SCREENS = 'screens'
PROJECT_TREE_ITEM_TAGS_ROOT = 'tags_root'
# Root node for comment tables in the Project tree
PROJECT_TREE_ITEM_COMMENT_ROOT = 'comment_root'
# Individual comment table/group node in the Project tree
PROJECT_TREE_ITEM_COMMENT_GROUP = 'comment_group'