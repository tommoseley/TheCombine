"""
Markdown block renderer (WS-RENDER-001).

Converts document content + IA definitions into presentation-grade Markdown.
Pure function — no DB, no side effects, deterministic output.

Reuses IA bind definitions from combine-config package.yaml.
Each render_as type maps to a Markdown output pattern.
"""
from __future__ import annotations

from typing import Any, Dict, List, Optional


def render_document_to_markdown(
    content: Dict[str, Any],
    ia: Dict[str, Any],
) -> str:
    """
    Render document content to Markdown using IA section definitions.

    Args:
        content: Document content dict (canonical JSON body).
        ia: Information architecture dict from package.yaml.
             Expected shape: {"version": 2, "sections": [...]}

    Returns:
        Markdown string.
    """
    sections = ia.get("sections", [])
    parts: List[str] = []

    for section in sections:
        section_md = _render_section(content, section)
        if section_md:
            parts.append(section_md)

    return "\n\n".join(parts) + "\n" if parts else ""


def _render_section(content: Dict[str, Any], section: Dict[str, Any]) -> Optional[str]:
    """Render a single IA section. Returns None if all binds produce no output."""
    label = section.get("label", "")
    binds = section.get("binds", [])

    bind_outputs: List[str] = []
    for bind in binds:
        bind_md = _render_bind(content, bind)
        if bind_md:
            bind_outputs.append(bind_md)

    if not bind_outputs:
        return None

    header = f"## {label}" if label else ""
    body = "\n\n".join(bind_outputs)
    return f"{header}\n\n{body}" if header else body


def _render_bind(content: Dict[str, Any], bind: Dict[str, Any]) -> Optional[str]:
    """Render a single IA bind. Dispatches to the appropriate block renderer."""
    path = bind.get("path", "")
    render_as = bind.get("render_as", "paragraph")

    # Resolve the field value from content
    value = _resolve_path(content, path)
    if value is None:
        return None

    renderer = _BLOCK_RENDERERS.get(render_as)
    if renderer:
        return renderer(value, bind)
    return None


def _resolve_path(content: Dict[str, Any], path: str) -> Any:
    """Resolve a dot-separated or simple path in the content dict."""
    if not path:
        return None
    # Support simple keys (most common case)
    if "." not in path:
        return content.get(path)
    # Support dot-separated paths
    parts = path.split(".")
    current = content
    for part in parts:
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


# ---------------------------------------------------------------------------
# Block renderers — one per render_as type
# ---------------------------------------------------------------------------

def _render_paragraph(value: Any, bind: Dict[str, Any]) -> Optional[str]:
    """Render a scalar value as a text block."""
    if not value or not isinstance(value, str):
        return None
    return value


def _render_list(value: Any, bind: Dict[str, Any]) -> Optional[str]:
    """Render an array of strings as an unordered bullet list."""
    if not isinstance(value, list) or len(value) == 0:
        return None
    lines = [f"- {_str(item)}" for item in value]
    return "\n".join(lines)


def _render_ordered_list(value: Any, bind: Dict[str, Any]) -> Optional[str]:
    """Render an array as a numbered list."""
    if not isinstance(value, list) or len(value) == 0:
        return None
    lines = [f"{i}. {_str(item)}" for i, item in enumerate(value, 1)]
    return "\n".join(lines)


def _render_table(value: Any, bind: Dict[str, Any]) -> Optional[str]:
    """Render an array of objects as a GFM table."""
    if not isinstance(value, list) or len(value) == 0:
        return None

    columns = bind.get("columns", [])
    if not columns:
        return None

    headers = [col.get("label", col.get("field", "")) for col in columns]
    fields = [col.get("field", "") for col in columns]

    # Header row
    header_row = "| " + " | ".join(headers) + " |"
    # Separator row
    sep_row = "| " + " | ".join("---" for _ in columns) + " |"
    # Data rows
    data_rows = []
    for item in value:
        if not isinstance(item, dict):
            continue
        cells = [_escape_pipe(_str(item.get(f, "—"))) for f in fields]
        data_rows.append("| " + " | ".join(cells) + " |")

    if not data_rows:
        return None

    return "\n".join([header_row, sep_row] + data_rows)


def _render_key_value_pairs(value: Any, bind: Dict[str, Any]) -> Optional[str]:
    """Render an object as key-value pairs."""
    if not isinstance(value, dict) or len(value) == 0:
        return None
    lines = [f"**{key}:** {_str(val)}" for key, val in value.items()]
    return "\n\n".join(lines)


def _render_nested_object(value: Any, bind: Dict[str, Any]) -> Optional[str]:
    """Render an object with explicitly declared sub-fields."""
    if not isinstance(value, dict):
        return None

    fields = bind.get("fields", [])
    if not fields:
        return None

    parts: List[str] = []
    for field_def in fields:
        field_path = field_def.get("path", "")
        field_render_as = field_def.get("render_as", "paragraph")
        field_value = value.get(field_path)
        if field_value is None:
            continue

        # Recurse: render the sub-field using the appropriate renderer
        sub_bind = {**field_def, "render_as": field_render_as}
        renderer = _BLOCK_RENDERERS.get(field_render_as)
        if renderer:
            sub_md = renderer(field_value, sub_bind)
            if sub_md:
                parts.append(sub_md)

    return "\n\n".join(parts) if parts else None


def _render_card_list(value: Any, bind: Dict[str, Any]) -> Optional[str]:
    """Render an array of objects as titled cards with sub-field rendering."""
    if not isinstance(value, list) or len(value) == 0:
        return None

    card_def = bind.get("card", {})
    title_field = card_def.get("title", "title")
    card_fields = card_def.get("fields", [])

    cards: List[str] = []
    for item in value:
        if not isinstance(item, dict):
            continue

        title = _str(item.get(title_field, "Untitled"))
        card_parts = [f"### {title}"]

        for field_def in card_fields:
            field_path = field_def.get("path", "")
            field_render_as = field_def.get("render_as", "paragraph")
            field_value = item.get(field_path)
            if field_value is None:
                continue

            sub_bind = {**field_def, "render_as": field_render_as}
            renderer = _BLOCK_RENDERERS.get(field_render_as)
            if renderer:
                sub_md = renderer(field_value, sub_bind)
                if sub_md:
                    card_parts.append(sub_md)

        if len(card_parts) > 1:  # More than just the title
            cards.append("\n\n".join(card_parts))

    return "\n\n".join(cards) if cards else None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _str(value: Any) -> str:
    """Coerce a value to string."""
    if value is None:
        return "—"
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, str):
        return value
    return str(value)


def _escape_pipe(text: str) -> str:
    """Escape pipe characters inside table cells."""
    return text.replace("|", "\\|")


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

_BLOCK_RENDERERS = {
    "paragraph": _render_paragraph,
    "list": _render_list,
    "ordered-list": _render_ordered_list,
    "table": _render_table,
    "key-value-pairs": _render_key_value_pairs,
    "nested-object": _render_nested_object,
    "card-list": _render_card_list,
}
