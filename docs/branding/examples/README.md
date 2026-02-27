# Examples -- Screenshot Capture Protocol

## Purpose

This directory holds reference screenshots of approved UI patterns and design mocks. Screenshots are captured from the running SPA, not mockups.

---

## Contents

| File | Description |
|------|-------------|
| `floor-constitution-mock.html` | **SUPERSEDED** -- Design comparison mock from 2026-02-24. Shows Floor rendered per the old UI Constitution v2.0 specs (neutral surfaces, violet accent, Inter font). The industrial 3-theme implementation was chosen instead. Kept for historical reference only. **Do not use as a reference for current styling.** |

---

## Required Screenshots (TODO)

Capture these from the running SPA at 1440x900 viewport:

### Production Floor
1. `floor-industrial.png` -- Industrial theme, project loaded, mix of artifact states
2. `floor-light.png` -- Light theme, same project
3. `floor-blueprint.png` -- Blueprint theme, same project
4. `floor-active-node.png` -- Node with active glow + station dots pulsing
5. `floor-question-tray.png` -- Node expanded with QuestionTray sidecar

### Document Nodes
6. `node-stabilized.png` -- Green border, "View Document" button
7. `node-in-progress.png` -- Amber border, station dots, glow effect
8. `node-ready.png` -- Cyan/blue border, "Start Production" button
9. `node-blocked.png` -- Red border, "Waiting for" text
10. `node-wp-badges.png` -- Work Package node showing WS/dep/Mode B badges

### Sidecars
11. `sidecar-document-view.png` -- Full document sidecar with bridge line
12. `sidecar-render-model.png` -- RenderModel viewer with block components
13. `sidecar-summary-block.png` -- SummaryBlock with border-left accent
14. `sidecar-risks-block.png` -- RisksBlock with severity colors

### Sidebar
15. `sidebar-project-tree.png` -- Project list with status dots

---

## Naming Convention

```
{component}-{theme}-{variant}.png
```

Examples:
- `floor-industrial-active-glow.png`
- `node-light-stabilized.png`
- `sidecar-blueprint-questions.png`

---

## How to Capture

1. Run the SPA locally: `cd spa && npm run dev`
2. Navigate to the relevant view
3. Set browser viewport to 1440x900 (DevTools device toolbar)
4. Select the target theme via the theme cycle button
5. Capture via browser screenshot or OS tool
6. Commit to this directory
