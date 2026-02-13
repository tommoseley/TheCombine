"""
Interpretation field management for Intake workflow.

Implements single-writer locking and confidence calculation for the
Review & Lock checkpoint before project creation.

Design doc: docs/design/intake-interpretation-panel.md
Work statement: WS-INTAKE-001
"""

from datetime import datetime, timezone
from typing import Any, Dict, List

# Required fields for v1 - all must be filled to initialize project
REQUIRED_FIELDS = ["project_name", "project_type", "problem_statement"]


def calculate_confidence(interpretation: Dict[str, Dict]) -> float:
    """Calculate confidence as ratio of filled required fields.
    
    Args:
        interpretation: Dict of field_key -> {value, source, locked, updated_at}
    
    Returns:
        Float between 0.0 and 1.0
    """
    if not REQUIRED_FIELDS:
        return 1.0
    
    filled = sum(
        1 for key in REQUIRED_FIELDS
        if key in interpretation and interpretation[key].get("value")
    )
    return filled / len(REQUIRED_FIELDS)


def get_missing_fields(interpretation: Dict[str, Dict]) -> List[str]:
    """Return list of required fields that are empty.
    
    Args:
        interpretation: Dict of field_key -> {value, source, locked, updated_at}
    
    Returns:
        List of field keys that are missing or empty
    """
    return [
        key for key in REQUIRED_FIELDS
        if key not in interpretation or not interpretation[key].get("value")
    ]


def create_field(value: Any, source: str = "llm") -> Dict[str, Any]:
    """Create an interpretation field with metadata.
    
    Args:
        value: The field value
        source: One of "llm" (extracted), "user" (edited), "default" (fallback)
    
    Returns:
        Field dict with value, source, locked, updated_at
    """
    return {
        "value": value,
        "source": source,
        "locked": source == "user",  # User edits are auto-locked
        "updated_at": datetime.now(timezone.utc).isoformat()
    }


def update_field(
    interpretation: Dict[str, Dict],
    key: str,
    value: Any,
    source: str = "llm"
) -> bool:
    """Update an interpretation field, respecting locks.
    
    Single-writer rule: Locked fields can only be updated by source="user".
    
    Args:
        interpretation: Dict of field_key -> {value, source, locked, updated_at}
        key: Field key to update
        value: New value
        source: Source of update ("llm", "user", "default")
    
    Returns:
        True if update was applied, False if field was locked
    """
    existing = interpretation.get(key, {})
    
    # Never overwrite locked fields unless source is user
    if existing.get("locked") and source != "user":
        return False
    
    interpretation[key] = create_field(value, source)
    return True


def can_initialize(interpretation: Dict[str, Dict]) -> bool:
    """Check if interpretation has all required fields filled.
    
    Args:
        interpretation: Dict of field_key -> {value, source, locked, updated_at}
    
    Returns:
        True if confidence is 1.0 (all required fields filled)
    """
    return calculate_confidence(interpretation) >= 1.0