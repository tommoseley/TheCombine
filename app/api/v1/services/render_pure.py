"""Pure functions for document render model assembly -- WS-CRAP-002.

Extracted from app/api/v1/routers/projects.py to enable Tier-1 testing.
These functions perform data transformations with no I/O, no DB, no logging.
"""

import json
from typing import Any, Dict, List, Optional


def unwrap_raw_envelope(document_data: Any) -> Any:
    """Unwrap document content stored in raw envelope format.

    Some documents are stored as {"raw": true, "content": "```json\\n{...}\\n```"}
    instead of the direct JSON structure.  This unwraps to the inner dict when
    possible, falling back to the original data on parse failure.

    Returns:
        Unwrapped dict if parsing succeeds, else original document_data.
    """
    if not isinstance(document_data, dict):
        return document_data
    if not document_data.get("raw") or "content" not in document_data:
        return document_data

    raw_content = document_data["content"]
    if not isinstance(raw_content, str):
        return document_data

    cleaned = raw_content.strip()
    # Strip markdown code fences if present
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3].strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Try JSON repair for truncated LLM output
        repaired = repair_truncated_json(cleaned)
        if repaired is not None:
            return repaired
        return document_data


def normalize_document_keys(document_data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize LLM output keys to match docdef source pointers.

    LLM may produce alternate key names; docdef uses canonical forms.
    Mutates and returns document_data.
    """
    # data_models (LLM) -> data_model (docdef repeat_over)
    if "data_models" in document_data and "data_model" not in document_data:
        document_data["data_model"] = document_data["data_models"]
    # api_interfaces (LLM) -> interfaces (docdef repeat_over)
    if "api_interfaces" in document_data and "interfaces" not in document_data:
        document_data["interfaces"] = document_data["api_interfaces"]
    # risks (LLM schema) -> identified_risks (docdef source_pointer)
    if "risks" in document_data and "identified_risks" not in document_data:
        document_data["identified_risks"] = document_data["risks"]
    # quality_attributes: flatten object-of-arrays to array-of-objects
    qa = document_data.get("quality_attributes")
    if isinstance(qa, dict) and not isinstance(qa, list):
        flattened = []
        for category, items in qa.items():
            if isinstance(items, list):
                flattened.append({
                    "name": category.replace("_", " ").title(),
                    "acceptance_criteria": items,
                })
        if flattened:
            document_data["quality_attributes"] = flattened

    return document_data


def repair_truncated_json(text: str) -> Optional[Dict[str, Any]]:
    """Attempt to repair truncated JSON from LLM output.

    LLM outputs may be cut off mid-structure when hitting token limits.
    This tries to close any open brackets/braces to make the JSON parseable,
    so the RenderModel can at least display the sections that were completed.
    """
    # Track open delimiters (ignoring those inside strings)
    stack: List[str] = []
    in_string = False
    escape = False

    for ch in text:
        if escape:
            escape = False
            continue
        if ch == '\\' and in_string:
            escape = True
            continue
        if ch == '"' and not escape:
            in_string = not in_string
            continue
        if in_string:
            continue
        if ch in ('{', '['):
            stack.append(ch)
        elif ch == '}' and stack and stack[-1] == '{':
            stack.pop()
        elif ch == ']' and stack and stack[-1] == '[':
            stack.pop()

    if not stack:
        return None  # Nothing to repair or empty

    # Trim back to the last complete value (comma or colon boundary)
    trimmed = text.rstrip()
    # Remove trailing comma if present
    if trimmed.endswith(','):
        trimmed = trimmed[:-1]

    # Close open structures in reverse order
    closers = {'[': ']', '{': '}'}
    suffix = ''.join(closers.get(c, '') for c in reversed(stack))

    try:
        return json.loads(trimmed + suffix)
    except json.JSONDecodeError:
        # Try more aggressive trimming - remove last incomplete key-value
        lines = trimmed.rsplit('\n', 1)
        if len(lines) > 1:
            try:
                trimmed2 = lines[0].rstrip().rstrip(',')
                return json.loads(trimmed2 + suffix)
            except json.JSONDecodeError:
                pass
        return None


def resolve_display_title(
    document_title: Optional[str],
    document_data: Any,
) -> str:
    """Determine best display title for a document.

    Prefers document data fields over raw doc_type_id fallbacks.
    """
    display_title = document_title
    if not display_title or "_" in (display_title or ""):
        if isinstance(document_data, dict):
            display_title = (
                document_data.get("title")
                or (document_data.get("architecture_summary") or {}).get("title")
                or display_title
            )
        if display_title and "_" in display_title:
            display_title = display_title.replace("_", " ").replace(" Document", "").title()
    return display_title or ""
