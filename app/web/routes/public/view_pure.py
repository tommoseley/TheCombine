"""
Pure data transformation functions extracted from view_routes.py.

No I/O, no DB, no logging. All functions are deterministic and testable in isolation.

WS-CRAP-006: Testability refactoring for CRAP score reduction.

NOTE: FragmentRenderer._resolve_fragment() (CC=9) was assessed for extraction.
The function is almost entirely I/O (component_service.list_all(), fragment_service.get_fragment()).
The only pure logic is cache lookup (2 lines) and web_binding field traversal (3 lines).
Extracting the web_binding traversal alone would not meaningfully reduce CRAP score.
Extraction is NOT viable -- documented per WS rules.

What IS extractable:
- _render_placeholder() is already pure (string assembly)
- Fragment binding resolution (extract web binding from component) is a small pure operation
"""

from typing import Any, Optional


def extract_web_fragment_id(component: Any) -> Optional[str]:
    """Extract fragment_id from a component's web view bindings.

    Given a component object (or dict), navigates:
        component.view_bindings -> "web" -> "fragment_id"

    Args:
        component: Object with view_bindings attribute/key, or None.

    Returns:
        The fragment_id string, or None if not found at any level.
    """
    if component is None:
        return None

    if hasattr(component, "view_bindings"):
        view_bindings = component.view_bindings or {}
    elif isinstance(component, dict):
        view_bindings = component.get("view_bindings") or {}
    else:
        return None

    web_binding = view_bindings.get("web", {})
    return web_binding.get("fragment_id")


def render_placeholder_html(title: str, details: list[str]) -> str:
    """Render a graceful degradation placeholder as HTML.

    Produces an amber-bordered warning box with a title and optional detail lines.

    Args:
        title: Main message to display.
        details: List of detail strings to show below the title.

    Returns:
        HTML string for the placeholder.
    """
    detail_html = "".join(
        f'<div class="text-xs text-gray-500">{d}</div>' for d in details
    )
    return (
        '<div class="border border-amber-300 bg-amber-50 rounded p-3 my-2">'
        f'<div class="text-sm font-medium text-amber-800">{title}</div>'
        f'{detail_html}'
        '</div>'
    )


def find_component_by_schema_id(components: list, schema_id: str) -> Optional[Any]:
    """Find a component in a list by matching schema_id.

    Args:
        components: List of component objects with schema_id attribute.
        schema_id: The schema_id to match.

    Returns:
        The matching component, or None.
    """
    for c in components:
        c_schema_id = getattr(c, "schema_id", None) or (
            c.get("schema_id") if isinstance(c, dict) else None
        )
        if c_schema_id == schema_id:
            return c
    return None
