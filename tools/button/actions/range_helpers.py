"""Helper utilities for range-based validation and data type normalization."""

from typing import Optional, Tuple

class DataTypeMapper:
    """Centralized data type mapping to ensure consistency across dialogs."""

    TYPE_MAPPING = {
        "INT": "INT16",
        "DINT": "INT32",
        "REAL": "REAL",
        "BOOL": "BOOL",
    }

    @classmethod
    def normalize_type(cls, data_type: str) -> str:
        """Convert an internal data type to its standardized form."""
        return cls.TYPE_MAPPING.get(data_type, data_type)

    @classmethod
    def are_types_compatible(cls, type1: str, type2: str) -> bool:
        """Check if two data types are compatible after normalization."""
        return cls.normalize_type(type1) == cls.normalize_type(type2)

def validate_range_section(
    op1_selector,
    operator: str,
    op2_selector,
    lower_selector,
    upper_selector,
    prefix: str = "Range Trigger",
) -> Tuple[bool, Optional[str]]:
    """Validate range configuration and ensure type compatibility.

    Parameters
    ----------
    op1_selector, op2_selector, lower_selector, upper_selector : TagSelector
        Widgets providing tag data with ``get_data`` and ``current_tag_data``.
    operator : str
        The selected comparison operator.
    prefix : str
        Prefix used in any generated error message.
    """

    error_msg = None
    if not op1_selector.get_data():
        error_msg = f"{prefix}: Operand 1 must be specified."
    elif operator in ["between", "outside"]:
        if not lower_selector.get_data():
            error_msg = f"{prefix}: Lower Bound must be specified."
        elif not upper_selector.get_data():
            error_msg = f"{prefix}: Upper Bound must be specified."
    else:
        if not op2_selector.get_data():
            error_msg = f"{prefix}: Operand 2 must be specified."

    if error_msg:
        return False, error_msg

    op1_type = op1_selector.current_tag_data.get("data_type") if op1_selector.current_tag_data else None
    if op1_type:
        op1_type = DataTypeMapper.normalize_type(op1_type)
        if operator in ["between", "outside"]:
            lower_type = lower_selector.current_tag_data.get("data_type") if lower_selector.current_tag_data else None
            if lower_type and not DataTypeMapper.are_types_compatible(lower_type, op1_type):
                return False, "Data type must match Operand 1."
            upper_type = upper_selector.current_tag_data.get("data_type") if upper_selector.current_tag_data else None
            if upper_type and not DataTypeMapper.are_types_compatible(upper_type, op1_type):
                return False, "Data type must match Operand 1."
        else:
            op2_type = op2_selector.current_tag_data.get("data_type") if op2_selector.current_tag_data else None
            if op2_type and not DataTypeMapper.are_types_compatible(op2_type, op1_type):
                return False, "Data type must match Operand 1."

    return True, None

