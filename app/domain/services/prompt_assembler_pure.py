"""
Pure data transformation functions extracted from PromptAssembler.

These functions contain NO I/O, NO database access, NO logging.
They are deterministic, testable transformations of in-memory data.

Extracted as part of WS-CRAP-005: Testability Refactoring.
"""

import hashlib
import json
from typing import List, Dict, Any


# ---------------------------------------------------------------------------
# collect_ordered_component_ids  (from assemble() step 2)
# ---------------------------------------------------------------------------

def collect_ordered_component_ids(
    sections: List[Dict[str, Any]],
) -> List[str]:
    """
    Collect unique component IDs from sections, preserving section order.

    Sections are sorted by their 'order' field first, then component_ids
    are collected in that order with deduplication (first occurrence wins).

    Args:
        sections: List of section config dicts with optional 'component_id'
            and 'order' fields

    Returns:
        Ordered list of unique component IDs
    """
    sorted_sections = sorted(sections, key=lambda s: s.get("order", 0))

    seen: set[str] = set()
    result: list[str] = []
    for section in sorted_sections:
        comp_id = section.get("component_id")
        if comp_id and comp_id not in seen:
            seen.add(comp_id)
            result.append(comp_id)
    return result


# ---------------------------------------------------------------------------
# dedupe_bullets  (from assemble() step 4)
# ---------------------------------------------------------------------------

def dedupe_bullets(
    components_guidance: List[Dict[str, Any]],
) -> List[str]:
    """
    Concatenate generation_guidance bullets from components.

    Preserves component order and bullet order within each component.
    Deduplicates exact duplicates, keeping the first occurrence.

    Args:
        components_guidance: List of component generation_guidance dicts.
            Each dict has optional 'bullets' key with a list of strings.

    Returns:
        Ordered list of unique bullet strings
    """
    all_bullets: list[str] = []
    seen: set[str] = set()

    for guidance in components_guidance:
        bullets = guidance.get("bullets", [])
        for bullet in bullets:
            if bullet not in seen:
                seen.add(bullet)
                all_bullets.append(bullet)

    return all_bullets


# ---------------------------------------------------------------------------
# compute_bundle_sha256  (from assemble() step 6)
# ---------------------------------------------------------------------------

def compute_bundle_sha256(schema_bundle: Dict[str, Any]) -> str:
    """
    Compute SHA256 hash of a schema bundle.

    Uses sorted keys and compact separators for deterministic serialization.

    Args:
        schema_bundle: Schema bundle dict

    Returns:
        Hash string in format "sha256:<hex>"
    """
    bundle_json = json.dumps(schema_bundle, sort_keys=True, separators=(",", ":"))
    return f"sha256:{hashlib.sha256(bundle_json.encode()).hexdigest()}"


# ---------------------------------------------------------------------------
# format_prompt_text  (from PromptAssembler.format_prompt_text)
# ---------------------------------------------------------------------------

def format_prompt_text(
    header: Dict[str, Any],
    component_bullets: List[str],
    component_ids: List[str],
    bundle_sha256: str,
) -> str:
    """
    Format assembled prompt data as LLM-ready text.

    Creates a structured prompt with:
    - Role context from header
    - Constraints from header
    - Generation bullets from components
    - Schema information

    Args:
        header: Dict with optional 'role' and 'constraints' keys
        component_bullets: List of bullet strings
        component_ids: List of component ID strings
        bundle_sha256: Schema bundle hash string

    Returns:
        Formatted prompt string
    """
    lines: list[str] = []

    # Role
    role = header.get("role", "")
    if role:
        lines.append(role)
        lines.append("")

    # Constraints
    constraints = header.get("constraints", [])
    if constraints:
        lines.append("## Constraints")
        for constraint in constraints:
            lines.append(f"- {constraint}")
        lines.append("")

    # Generation guidance bullets
    if component_bullets:
        lines.append("## Generation Guidelines")
        for bullet in component_bullets:
            lines.append(f"- {bullet}")
        lines.append("")

    # Schema reference
    lines.append("## Schema Bundle")
    lines.append(f"SHA256: {bundle_sha256}")
    lines.append(f"Components: {', '.join(component_ids)}")

    return "\n".join(lines)
