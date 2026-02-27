# Color Palette

## Source Files

- [themes.css](../../spa/src/styles/themes.css) -- all CSS custom properties
- [constants.js](../../spa/src/utils/constants.js) -- edge colors per theme
- [DocumentNode.jsx](../../spa/src/components/DocumentNode.jsx) -- artifact state model

---

## Theme System

The Combine uses three themes applied via CSS class on the root element. Theme selection persists in `localStorage` via the `useTheme` hook.

| Theme | Class | Default | Character |
|-------|-------|---------|-----------|
| **Industrial** | `.theme-industrial` | Yes | Dark factory floor -- deep navy canvas, amber accents, glow effects |
| **Light** | `.theme-light` | No | Clean workspace -- off-white canvas, blue accents, subtle shadows |
| **Blueprint** | `.theme-blueprint` | No | Technical drawing -- deep blue canvas, white/cyan accents |

Themes are NOT light/dark mode. They are distinct visual identities that share the same semantic color system.

---

## Surface Colors

| Variable | Industrial | Light | Blueprint | Purpose |
|----------|-----------|-------|-----------|---------|
| `--bg-canvas` | `#0b1120` | `#f8fafc` | `#1e3a5f` | Page background |
| `--bg-node` | `#1e293b` | `#ffffff` | `#234b73` | Card/node background |
| `--bg-panel` | `rgba(11,17,32,0.95)` | `rgba(255,255,255,0.95)` | `rgba(30,58,95,0.95)` | Overlay panels |
| `--bg-button` | `#334155` | `#f1f5f9` | `#2d5a87` | Button background |
| `--bg-input` | `#1e293b` | `#f8fafc` | `#1e3a5f` | Input field background |
| `--bg-selected` | `#334155` | `#e2e8f0` | `#2d5a87` | Selected item highlight |
| `--bg-sidecar` | `#1e293b` | `#ffffff` | `#e8f4fc` | Sidecar container |

---

## Text Colors

| Variable | Industrial | Light | Blueprint | Purpose |
|----------|-----------|-------|-----------|---------|
| `--text-primary` | `#f8fafc` | `#1e293b` | `#e8f4fc` | Headings, primary content |
| `--text-secondary` | `#e2e8f0` | `#475569` | `#c8e4f0` | Body text, descriptions |
| `--text-muted` | `#cbd5e1` | `#64748b` | `#a8d4f0` | Labels, captions |
| `--text-dim` | `#94a3b8` | `#94a3b8` | `#7cb8e0` | Least-emphasis text |
| `--text-input` | `#f8fafc` | `#1e293b` | `#e8f4fc` | Input field text |
| `--text-sidecar` | `#f8fafc` | `#1e293b` | `#1e3a5f` | Sidecar body text |
| `--text-sidecar-muted` | `#cbd5e1` | `#64748b` | `#3d6a8f` | Sidecar secondary text |

---

## Border Colors

| Variable | Industrial | Light | Blueprint | Purpose |
|----------|-----------|-------|-----------|---------|
| `--border-node` | `#475569` | `#e2e8f0` | `#4a90c2` | Card/node borders |
| `--border-panel` | `#334155` | `#e2e8f0` | `#3d7ab3` | Panel borders |
| `--border-input` | `#475569` | `#cbd5e1` | `#4a90c2` | Input field borders |

---

## Artifact State Colors

The four-state model is the foundation of all status visualization. These colors are used for node borders, status dots, station progress, edge lines, and action buttons.

| State | Background | Text (Industrial) | Text (Light) | Meaning |
|-------|-----------|-------------------|--------------|---------|
| **Stabilized** | `#10b981` | `#6ee7b7` | `#059669` | Complete, immutable, trusted |
| **In Progress** | `#F6AD55` | `#fcd34d` | `#dd8a2e` | Active work, needs attention |
| **Ready** | `#00E5FF` (dark) / `#1e40af` (light) | `#67f0ff` | `#1e3a8a` | Gates passed, awaiting action |
| **Blocked** | `#ef4444` | `#fca5a5` | `#dc2626` | Cannot proceed |
| **Queued** | `#4A5568` | `#94a3b8` | `#64748b` | Waiting, inactive |

CSS variables follow the pattern `--state-{name}-bg`, `--state-{name}-text`, `--state-{name}-edge`.

---

## Node Header Colors

Document and Work Package nodes have distinct header treatments:

| Type | Variable | Industrial | Light | Blueprint |
|------|----------|-----------|-------|-----------|
| **Document bg** | `--header-bg-doc` | `rgba(16,185,129,0.15)` | `rgba(16,185,129,0.08)` | `rgba(255,255,255,0.1)` |
| **Document border** | `--header-border-doc` | `rgba(16,185,129,0.4)` | `rgba(16,185,129,0.25)` | `rgba(255,255,255,0.3)` |
| **Document text** | `--header-text-doc` | `#34d399` | `#059669` | `#ffffff` |
| **Work Package bg** | `--header-bg-wp` | `rgba(245,158,11,0.15)` | `rgba(99,102,241,0.08)` | `rgba(255,255,255,0.1)` |
| **Work Package border** | `--header-border-wp` | `rgba(245,158,11,0.4)` | `rgba(99,102,241,0.25)` | `rgba(255,255,255,0.3)` |
| **Work Package text** | `--header-text-wp` | `#fbbf24` | `#4f46e5` | `#ffffff` |

---

## Edge Colors

Edges connecting nodes on the canvas use state-derived colors:

| State | Industrial | Light | Blueprint |
|-------|-----------|-------|-----------|
| Stabilized | `#10b981` | `#10b981` | `#10b981` |
| In Progress | `#f59e0b` | `#6366f1` | `#fbbf24` |
| Ready | `#eab308` | `#eab308` | `#eab308` |
| Blocked | `#ef4444` | `#ef4444` | `#ef4444` |

Source: `EDGE_COLORS` in `spa/src/utils/constants.js`

---

## Accent & Action Colors

| Variable | Industrial | Light | Blueprint | Purpose |
|----------|-----------|-------|-----------|---------|
| `--action-primary` | `#f59e0b` | `#3b82f6` | `#fbbf24` | Primary action color |
| `--action-success` | `#6ee7b7` | `#059669` | `#059669` | Success actions |
| `--action-warning` | `#fcd34d` | `#d97706` | `#d97706` | Warning actions |

---

## Glow Effects

Glow effects are reserved for active state communication. They are NOT decorative.

| Variable | Industrial | Light | Blueprint | When Used |
|----------|-----------|-------|-----------|-----------|
| `--glow-active` | `0 0 20px 8px rgba(246,173,85,0.4)` | `0 4px 12px -2px rgba(246,173,85,0.25)` | `0 0 15px 5px rgba(246,173,85,0.4)` | Node in active production |
| `--glow-station` | `0 0 10px 5px rgba(246,173,85,0.5)` | `0 0 6px 3px rgba(246,173,85,0.3)` | `0 0 8px 4px rgba(246,173,85,0.5)` | Station dot pulsing |

---

## Decorative Dots

Used for visual accents in specific UI elements:

| Variable | Industrial | Light | Blueprint |
|----------|-----------|-------|-----------|
| `--dot-green` | `#34d399` | `#059669` | `#34d399` |
| `--dot-blue` | `#60a5fa` | `#3b82f6` | `#93c5fd` |
| `--dot-purple` | `#a78bfa` | `#8b5cf6` | `#c4b5fd` |

---

## Sidecar Content Colors

Block components inside sidecars (SummaryBlock, RisksBlock, StringListBlock) currently use hardcoded light-mode hex values in inline styles. They render correctly in the light sidecar context across all themes because the sidecar background is always light or neutral.

Key hardcoded values in block components:
- Primary text: `#374151` (gray-700)
- Background: `#f8fafc` (slate-50)
- Border accents: `#6366f1` (indigo), `#ef4444` (red), `#f59e0b` (amber)
