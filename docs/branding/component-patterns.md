# Component Patterns

## Source Files

- [DocumentNode.jsx](../../spa/src/components/DocumentNode.jsx) -- node cards, artifact states, badges
- [Floor.jsx](../../spa/src/components/Floor.jsx) -- canvas layout, panels, modals
- [DocumentViewer.jsx](../../spa/src/components/DocumentViewer.jsx) -- sidecar container
- [StationDots.jsx](../../spa/src/components/StationDots.jsx) -- station progress indicators
- [ProjectTree.jsx](../../spa/src/components/ProjectTree.jsx) -- sidebar with resize
- [QuestionTray.jsx](../../spa/src/components/QuestionTray.jsx) -- PGC question form
- [blocks/](../../spa/src/components/blocks/) -- content block components

---

## Layout Architecture

### Three-Region Structure

```
+------------------+--------------------------------------+
| ProjectTree      | Floor (ReactFlow Canvas)             |
| (left sidebar)   |                                      |
|                  |   +--------+                         |
| - project list   |   | Node 1 |--+                     |
| - status dots    |   +--------+  |  +-- Sidecar --+    |
| - + New Project  |               +->|  (tray or   |    |
|                  |   +--------+  |  |   viewer)   |    |
| resizable        |   | Node 2 |--+  +-------------+    |
| 180-400px        |   +--------+                         |
|                  |                                      |
+------------------+--------------------------------------+
```

- **Left**: ProjectTree sidebar (resizable 180-400px, collapsible to 48px)
- **Center**: ReactFlow canvas with document nodes, edges, panels
- **Right**: Sidecars (document viewer, question tray, WS child list)

### Two-Tier Header

- **Tier 1** (Global Identity): 64px logged-out / 48px logged-in, fixed, shows brand
- **Tier 2** (Mode Header): Theme switcher, zoom controls, production line status

---

## Document Node Card

The primary UI element. Each card represents a document type on the production floor.

### Structure

```
+-- border: 1px solid var(--state-{state}-bg) --------+
| HEADER: bg var(--header-bg-{type})                   |
|   "DOCUMENT" label (8px bold uppercase)              |
|   Document Name (10px medium)                        |
+------------------------------------------------------+
| BODY: bg var(--bg-node), padding 12px                |
|   [24px colored dot]  STATE LABEL (10px semi-bold)   |
|   Description text (9px muted)                       |
|   [Station Dots progress bar]                        |
|   [Action Button] -- colored per state               |
|   Waiting for: X (8px, if blocked)                   |
+------------------------------------------------------+
```

### Artifact State Model

Four states map all raw execution states to user-visible presentation:

| Artifact State | Raw States Mapped | Color | Dot Size |
|---------------|-------------------|-------|----------|
| **Stabilized** | produced, stabilized, ready, complete | Green (`--state-stabilized-bg`) | 24px (L1) / 18px (L2) |
| **In Progress** | in_production, active, queued, awaiting_operator | Amber (`--state-active-bg`) | 24px / 18px |
| **Ready** | ready_for_production, waiting, pending_acceptance | Cyan/Blue (`--state-ready-bg`) | 24px / 18px |
| **Blocked** | requirements_not_met, blocked, halted, failed | Red (`--state-blocked-bg`) | 24px / 18px |

### Node Types

- **L1 (Document)**: Header uses `--header-bg-doc` (emerald tint). Shows description, station dots, full action buttons.
- **L2 (Work Package)**: Header uses `--header-bg-wp` (amber/indigo tint). Shows WS progress badges (`3/7 WS`), dependency count, Mode B count.

### Sizing

- Node width: set by layout engine (typically 240-320px)
- Border radius: `rounded-lg` (8px)
- Header padding: `px-3 py-1.5` (12px / 6px)
- Body padding: `p-3` (12px)

---

## Station Dots

Progress indicator showing workflow station states within a node.

```
 o----o----o----o----o
PGC  ASM  STB  RND  QA
          ^
     (active, pulsing)
```

- **Gray line**: background track (`--state-queued-bg`)
- **Green segment**: completed stations (`--state-stabilized-bg`)
- **Amber segment**: progress to active station (`--state-active-bg`)
- **Dots**: 12px circles, colored by station state
- **Labels**: 7px below each dot
- **Active dot**: `station-active` class triggers pulse animation
- **Needs input**: `station-needs-input` class triggers expanding ring animation

---

## Panels

Overlay panels in the top-left corner of the canvas.

- Background: `var(--bg-panel)` with `backdrop-blur`
- Border: `1px solid var(--border-panel)`
- Border radius: `rounded-lg` (8px)
- Padding: `px-4 py-3` (16px / 12px)
- Stacked with `gap-2` (8px)

### Production Line Panel
Shows title, line state (Active/Stopped/Complete/Idle), reset layout button, theme cycle button.

### Project Info Panel
Shows project icon (36px, accent-colored), project code (monospace), project name, edit/archive/delete controls.

### Workflow Panel
Collapsible, shows workflow instance status.

---

## Sidecars

Content panels that appear to the right of an expanded node.

### Document Viewer (Fallback)
- Width: 520px (normal) / 900px (expanded)
- Min height: 600px / 900px
- Background: white
- Border radius: 2px (intentionally minimal -- technical aesthetic)
- Box shadow: `0 25px 50px -12px rgba(0,0,0,0.5)`
- Connected to node via emerald bridge line (3px) with terminal dot (10px)

### Question Tray
- Width: 400px (normal) / 560px (expanded)
- Slides in via `slideRight` animation (0.2s)
- Inputs use `--bg-input`, `--border-input`, `--text-input` variables
- Checkboxes/radios: `accent-amber-500`

### WS Child List
- Shows Work Statement children of a Work Package
- Same slide animation as Question Tray

---

## Buttons

### State Action Buttons
Colored to match the artifact state they act upon:

| State | Button Color | Label |
|-------|-------------|-------|
| Stabilized | `var(--state-stabilized-bg)` (green) | View Document |
| Ready | `var(--state-ready-bg)` (cyan/blue) | Start Production |
| In Progress (needs input) | `var(--state-active-bg)` (amber) | Answer Questions |

All: `px-2 py-1 rounded text-[9px] font-semibold`, white text, `hover:brightness-110`.

### Secondary Buttons
- Background: `var(--bg-button)` or transparent
- Text: `var(--text-muted)`
- Padding: `p-1.5` or `p-2`
- Hover: `hover:bg-white/10` or `hover:opacity-80`

### New Project Button
- Background: `#10b981` (emerald, fixed)
- Full width, `py-2.5 rounded-lg`
- White text

---

## Status Badges

Small metadata tags on Work Package nodes:

```css
padding: 2px 6px;    /* px-1.5 py-0.5 */
font-size: 8px;      /* text-[8px] */
font-weight: 600;    /* font-semibold */
text-transform: uppercase;
border-radius: 4px;  /* rounded */
background: rgba(X, X, X, 0.15);
```

Examples: `3/7 WS`, `2 deps`, `1 Mode B`

---

## Modals

### Delete Confirmation
- Overlay: `fixed inset-0 z-50 bg-black/50`
- Card: `var(--bg-panel)`, `1px solid var(--border-panel)`, `rounded-lg p-6 max-w-sm`
- Danger button: `bg-red-500 text-white hover:bg-red-600`

### Notification Toast
- Position: `fixed top-6 left-1/2 -translate-x-1/2 z-50`
- Background: `#f0fdf4` (success) or `#fef2f2` (error)
- Border: green or red tint
- Max width: 500px
- Entrance: `fadeIn 0.2s ease-out`

---

## Legend

Bottom-left panel showing the four artifact states:

```
STATE: [green dot] Stabilized  [cyan dot] Ready  [amber dot] In Progress  [red dot] Blocked
```

- Font: 10px, `var(--text-muted)`
- Dots: `w-3 h-3 rounded-full`, colored by state variable
- Panel: same `subway-panel` class as other panels

---

## Animations

All animations communicate state. None are decorative.

| Animation | Duration | Easing | Purpose |
|-----------|----------|--------|---------|
| `activeGlow` | 2s | ease-in-out, infinite | Node in active production (amber glow pulse) |
| `stationPulse` | 1.5s | ease-in-out, infinite | Active station dot (amber glow) |
| `amberBlink` | 1.5s | ease-in-out, infinite | Button opacity pulse (needs attention) |
| `needsInputPulse` | 1s | ease-in-out, infinite | Station dot expanding ring (awaiting user) |
| `edgeFlow` | 0.5s | linear, infinite | Animated edge stroke dash (data flowing) |
| `slideRight` | 0.2s | ease-out | Sidecar tray entrance |

Source: `spa/src/styles/themes.css` lines 204-228
