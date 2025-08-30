# Property Editor Architecture

This package contains the main `PropertyEditor` and per-tool editor helpers.

- `__init__.py`: hosts the `PropertyEditor` widget and schema wiring.
- `factory.py`: returns a tool-specific adapter with two callables per tool:
  - `build(host) -> QWidget`: constructs the editor widget bound to the host.
  - `update_fields(widget, props) -> None`: updates existing widgets from props.
- `<tool>_editor.py`: one module per tool (e.g., `line_editor.py`).

Adding a new editor
- Create `components/property_editor/<tool>_editor.py` with `build` and `update_fields`.
- Register it inside `components/property_editor/factory.py#get_editor`.
- Ensure the tool’s default properties are merged in `PropertyEditor._init_schemas`.

Notes
- Editors call back into `PropertyEditor` via the passed `host` to use the
  editing guard and command history. This keeps command emission consistent.
- Editors must assign `objectName` on inputs so `update_fields` can find them.
