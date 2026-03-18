"""Field content classifier — shared by WP and WS evaluators.

Classifies field values as ABSENT, EMPTY, WEAK, or MEANINGFUL
using deterministic heuristics (no LLM dependency).
"""

import re
from typing import Any


_PLACEHOLDERS = re.compile(
    r"^(tbd|t\.b\.d\.?|n/?a|none|todo|do the work|placeholder|pending|unknown)$",
    re.IGNORECASE,
)


def classify_field_content(
    value: Any,
    min_length: int = 10,
) -> str:
    """
    Classify a field value as ABSENT, EMPTY, WEAK, or MEANINGFUL.

    Args:
        value: The field value (str, list, or None)
        min_length: Minimum character length for string content to be meaningful

    Returns:
        One of: "ABSENT", "EMPTY", "WEAK", "MEANINGFUL"
    """
    if value is None:
        return "ABSENT"

    if isinstance(value, str):
        stripped = value.strip()
        if not stripped:
            return "EMPTY"
        if _PLACEHOLDERS.match(stripped):
            return "WEAK"
        if len(stripped) < min_length:
            return "WEAK"
        return "MEANINGFUL"

    if isinstance(value, list):
        if len(value) == 0:
            return "EMPTY"
        meaningful_items = 0
        for item in value:
            if isinstance(item, str):
                s = item.strip()
                if s and not _PLACEHOLDERS.match(s) and len(s) >= min_length:
                    meaningful_items += 1
            elif isinstance(item, dict):
                if item:
                    meaningful_items += 1
        if meaningful_items == 0:
            return "WEAK"
        return "MEANINGFUL"

    return "MEANINGFUL" if value else "EMPTY"
