# Data-Driven UX Contract v1.0

> **Frozen**: The "Tuning Guide" for UX configuration without code changes.

## Philosophy

> **"Tune the UX without touching code. If it's presentation, it's data."**

Every visual decision that varies by document type, section, or state should be expressible in data. This enables rapid iteration, A/B testing, and non-engineer UX tuning.

## Data-Driven UX Elements

### 1. Primary Actions (CTAs)

**Location**: `document_types.primary_action`

```json
{
  "primary_action": {
    "label": "Begin Research",
    "icon": "compass",
    "variant": "primary",
    "tooltip": "Start the discovery process",
    "confirmation": null
  }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `label` | Yes | Button text (e.g., "Generate", "Synthesize", "Begin Research") |
| `icon` | No | Lucide icon name |
| `variant` | No | `primary`, `secondary`, `ghost` |
| `tooltip` | No | Hover text |
| `confirmation` | No | Confirmation dialog text (if set) |

**Default**: If not specified, uses `"Generate {document_name}"`

### 2. Status Badges

**Location**: `document_types.status_badges`

```json
{
  "status_badges": {
    "missing": { "icon": "file-plus", "color": "gray" },
    "generating": { "icon": "loader-2", "color": "blue", "animate": "spin" },
    "partial": { "icon": "file-clock", "color": "yellow" },
    "complete": { "icon": "file-check", "color": "green" },
    "stale": { "icon": "alert-triangle", "color": "amber" }
  }
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `icon` | Yes | Lucide icon name |
| `color` | Yes | Tailwind color name (gray, blue, green, amber, etc.) |
| `animate` | No | CSS animation (`spin`, `pulse`) |

### 3. Display Variants

**Location**: `document_definitions.sections[].display_variant`

```json
{
  "sections": [{
    "section_id": "story_list",
    "display_variant": "compact"
  }]
}
```

| Variant | Description |
|---------|-------------|
| `default` | Standard rendering |
| `compact` | Reduced spacing, smaller text |
| `expanded` | Full details, more whitespace |
| `card` | Card-style with shadows |
| `table` | Tabular layout |
| `minimal` | Icon + title only |

**CSS Class**: `fragment-{variant}` (e.g., `fragment-compact`)

## Resolution Order

1. **Direct override** (highest priority)
2. **Document type configuration** (from database)
3. **System defaults** (hardcoded fallbacks)

## Default Values

| Element | Default |
|---------|---------|
| CTA label | "Generate" |
| CTA icon | Document type icon |
| CTA variant | `primary` |
| Badge (missing) | `file-plus` / gray |
| Badge (generating) | `loader-2` / blue / spin |
| Badge (partial) | `file-clock` / yellow |
| Badge (complete) | `file-check` / green |
| Badge (stale) | `alert-triangle` / amber |
| Display variant | `default` |

## How to Change UX Elements

### Example: Change "Generate" to "Synthesize" for Epic Backlog

```sql
UPDATE document_types 
SET primary_action = '{"label": "Synthesize Epics", "icon": "layers", "variant": "primary"}'
WHERE doc_type_id = 'epic_backlog';
```

### Example: Change Stale Badge to Red

```sql
UPDATE document_types 
SET status_badges = jsonb_set(
  COALESCE(status_badges, '{}'),
  '{stale}',
  '{"icon": "alert-circle", "color": "red"}'
)
WHERE doc_type_id = 'project_discovery';
```

## Governance Boundary

| Change | Requires WS/ADR? |
|--------|------------------|
| Change CTA label/icon/color | No |
| Change badge icon/color | No |
| Change display variant | No |
| Add new CTA variant type | Yes |
| Add new display variant | Yes |
| Add new badge animation | Yes |

## Anti-Patterns (Avoid)

1. **Hardcoded icon names in templates** - Use data lookup
2. **CSS classes embedded in routes** - Use variant system
3. **Conditional rendering based on doc_type_id** - Use visibility rules
4. **Button text in HTML** - Use primary_action config

---

_Frozen: 2026-01-12 (WS-DOCUMENT-SYSTEM-CLEANUP Phase 9)_