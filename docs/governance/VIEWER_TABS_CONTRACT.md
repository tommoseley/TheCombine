# Viewer Tabs Contract v1.0

> **Frozen**: This contract governs how tabs are discovered and rendered.

## Philosophy

Tabs are **data-driven**, not hardcoded enums. The UI dynamically generates tabs based on `viewer_tab` configuration in document definitions.

## Tab Discovery Rules

1. **Source of Truth**: `document_definitions.sections[].viewer_tab`
2. **Dynamic Generation**: Tabs appear only if sections exist for them
3. **No Hardcoding**: Template code never contains tab name literals

## Tab Configuration Schema

```json
{
  "sections": [
    {
      "section_id": "overview",
      "viewer_tab": "Overview",
      "display_order": 1
    },
    {
      "section_id": "details",
      "viewer_tab": "Details",
      "display_order": 2
    }
  ]
}
```

## Tab Rendering Rules

| Condition | Behavior |
|-----------|----------|
| Section exists for tab | Tab appears in navigation |
| No sections for tab | Tab is hidden |
| Single tab only | Tab bar hidden, content shown directly |
| Tab has no content | Tab appears but shows empty state |

## Tab Ordering

1. Tabs ordered by minimum `display_order` of their sections
2. Ties broken alphabetically by tab name
3. "Overview" always first if present (convention, not enforced)

## Invariants

1. Tab names are case-sensitive strings
2. Tab visibility is computed at render time, never cached
3. Adding a tab requires only docdef change, no code
4. Removing all sections for a tab hides it automatically

## Anti-Patterns (Avoid)

1. **Hardcoded tab arrays in templates** - Use data lookup
2. **Tab visibility logic in routes** - Compute in RenderModelBuilder
3. **Tab names as magic strings in multiple files** - Single source in docdef

## Governance Boundary

| Change | Requires WS/ADR? |
|--------|------------------|
| Add new tab to docdef | No |
| Change tab ordering | No |
| Add tab-level styling | No |
| Change tab discovery algorithm | Yes |
| Add tab-level permissions | Yes |

---

_Frozen: 2026-01-12 (WS-DOCUMENT-SYSTEM-CLEANUP Phase 9)_