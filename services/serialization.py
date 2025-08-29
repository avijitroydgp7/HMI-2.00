"""
Shared project serialization/deserialization utilities.

These wrap the existing services so both the Designer and Runtime
Simulator use the exact same code paths and JSON schema when
loading/saving projects.
"""

from __future__ import annotations

from typing import Dict, Any

from .project_service import project_service
from .screen_data_service import screen_service
from .tag_data_service import tag_data_service
from .comment_data_service import comment_data_service


def load_from_file(file_path: str) -> Dict[str, Any]:
    """Load a project into services state and return the combined dict.

    Raises the same exceptions as the underlying loader on failure.
    """
    project_service.load_project(file_path)
    return get_current_project()


def save_to_file(file_path: str) -> bool:
    """Save the current services state as a project file."""
    return bool(project_service.save_project(file_path))


def get_current_project() -> Dict[str, Any]:
    """Return the current in-memory project as a JSON-serializable dict."""
    return {
        "project_info": project_service.get_project_info(),
        **screen_service.serialize_for_project(),
        **tag_data_service.serialize_for_project(),
        **comment_data_service.serialize_for_project(),
    }

