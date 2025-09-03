from __future__ import annotations

def percent_to_value(pct: float | int, base: float) -> int:
    """Convert a percentage ``pct`` to an absolute value based on ``base``."""
    try:
        return int(float(pct) * base / 100.0)
    except Exception:
        return 0

def value_to_percent(value: float | int, base: float) -> float:
    """Convert an absolute ``value`` to a percentage of ``base``."""
    if not base:
        return 0.0
    try:
        return float(value) / float(base) * 100.0
    except Exception:
        return 0.0
