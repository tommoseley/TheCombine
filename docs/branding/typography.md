# Typography

## Source Files

- [themes.css](../../spa/src/styles/themes.css) line 190 -- font-family declaration
- [DocumentNode.jsx](../../spa/src/components/DocumentNode.jsx) -- node card type hierarchy
- [DocumentViewer.jsx](../../spa/src/components/DocumentViewer.jsx) -- sidecar document rendering
- [StringListBlock.jsx](../../spa/src/components/blocks/StringListBlock.jsx) -- content block typography

---

## Font Stack

### Body Text
```css
font-family: system-ui, -apple-system, sans-serif;
```

System fonts are the intentional choice. They render natively on every platform, load instantly, and feel like serious infrastructure software rather than a styled web app.

### Monospace (IDs, codes, technical content)
```css
font-family: monospace;
```

Used for project codes, document IDs, serial numbers, and technical identifiers.

### Serif (Document titles in sidecar)
```css
font-family: Georgia, serif;
```

Used sparingly for document title emphasis in the sidecar full-document view.

---

## Type Scale

Sizes are extracted from the implemented components. The scale is compact -- designed for information-dense canvas views where many nodes must be visible simultaneously.

### Display & Titles

| Element | Size | Weight | Context | Source |
|---------|------|--------|---------|--------|
| RenderModel title | 24px | 700 | Full document view | RenderModelViewer.jsx |
| Sidecar document title | 20px | 700 | Document header (Georgia serif) | DocumentViewer.jsx |
| Production Line title | 18px | 700 | Floor panel header | Floor.jsx |
| Section title | 15px | 700 | Sidecar section headers | DocumentViewer.jsx |
| Project name | 14px | 600 | Floor project info panel | Floor.jsx |
| RenderModel subtitle | 14px | 400 | Document metadata | RenderModelViewer.jsx |

### Labels & UI Text

| Element | Size | Weight | Transform | Tracking | Source |
|---------|------|--------|-----------|----------|--------|
| Block section title | 12px | 600 | uppercase | 0.05em | StringListBlock.jsx |
| Field label | 10px | 700 | uppercase | 0.08em | DocumentViewer.jsx |
| Node type label | 8px | 700 | uppercase | wider | DocumentNode.jsx |
| Node name | 10px | 500 | none | none | DocumentNode.jsx |

### Body Text

| Element | Size | Weight | Line Height | Source |
|---------|------|--------|-------------|--------|
| List item | 14px | 400 | 1.6 | StringListBlock.jsx |
| Paragraph | 12px | 400 | 1.5 | DocumentViewer.jsx |
| Node description | 9px | 400 | default | DocumentNode.jsx |
| Secondary text | 11px | 400 | default | DocumentViewer.jsx |

### Small & Compact

| Element | Size | Weight | Source |
|---------|------|--------|--------|
| State label | 10px | 600 | DocumentNode.jsx |
| Badges | 8-10px | 600 | DocumentNode.jsx |
| Station dot labels | 7px | 400-500 | StationDots.jsx |
| Canvas instructions | 10px | 400 | Floor.jsx |
| Mono IDs | 11px | 400 | DocumentViewer.jsx |

---

## Typographic Rules

### Hierarchy Through Weight and Size

Typography hierarchy is established through font size and weight, not color. Color reinforces but does not create hierarchy.

- **700 (Bold)**: Titles, primary headings
- **600 (Semi-bold)**: Section headers, state labels, field labels
- **500 (Medium)**: Active states, emphasized items
- **400 (Regular)**: Body text, descriptions, default weight

### Uppercase Labels

All categorical labels (DOCUMENT, WORK PACKAGE, STATE, field names) use uppercase with letter-spacing:

```css
text-transform: uppercase;
letter-spacing: 0.05em - 0.08em;
font-weight: 500 - 700;
font-size: 8px - 12px;
```

This creates a visual distinction between data labels and data values without relying on color.

### Line Height

- **1.6**: Body text, list items -- maximum readability
- **1.5**: Labels, secondary text
- **default (~1.2)**: Compact UI elements (badges, station labels)

### Monospace for Identifiers

Project codes (`PRJ-001`), document IDs, and serial numbers always use monospace to visually distinguish machine-generated identifiers from human-readable text.

---

## Mixing CSS Approaches

The SPA uses two styling approaches for typography:

1. **Tailwind utility classes** in JSX: `text-xs`, `text-sm`, `text-lg`, `font-bold`, `font-semibold`, `tracking-wide`, `font-mono`
2. **Inline styles** for dynamic/theme-aware values: `style={{ fontSize: 12, fontWeight: 600, color: 'var(--text-primary)' }}`

Both are acceptable. Tailwind classes are preferred for static sizing; inline styles are required when referencing CSS custom properties for theme-aware colors.
