# Branding Implementation Instructions

## Overview

Implement a two-tier header system based on authentication state.

## Tier 1 — Global Identity Header

### Logged Out (Lobby) — 64px height
```
┌────────────────────────────────────────────────────────┐
│ [C] THE COMBINE                                        │
│     Industrial AI for Knowledge Work                   │
└────────────────────────────────────────────────────────┘
     [Login]  [Learn More]  [Pricing]
```

- Full-width, fixed position
- Show tagline ("Industrial AI for Knowledge Work")
- No utility icons
- Marketing/landing page actions below or integrated

### Logged In (Floor) — 48px height
```
┌────────────────────────────────────────────────────────┐
│ [C] THE COMBINE                              [?] [👤]  │
└────────────────────────────────────────────────────────┘
```

- Full-width, fixed position
- NO tagline (user knows where they are)
- Utility icons right: Help [?], User menu [👤]
- Static, calm, never changes

## Tier 2 — Mode Header (Logged In Only)

```
┌────────────────────────────────────────────────────────┐
│ Production Line        [ Blueprint ▼ ]   [ ⊞ ] [ + - ] │
└────────────────────────────────────────────────────────┘
```

- Directly below Tier 1
- Boxed or subtly elevated (current styling is fine)
- Interactive: theme switcher, zoom controls, status
- This is the "control panel" for the current mode

## Left Rail — Projects (Unchanged)

Keep current implementation:
- Project list only (no documents)
- Status dots (amber = active, green = stabilized, gray = queued)
- "+ New Project" button at bottom
- Emphasize: project name + code
- De-emphasize: timestamps

## Implementation Notes

### Logo Asset
The "C" logo is available at:
- `/mnt/user-data/outputs/combine_logo_clean.png` (512px, dark bg)
- `/mnt/user-data/outputs/combine_icon_256.png` (256px, dark bg)

For header use, you'll want a smaller version (~28-32px). The logo is white lines on transparent/dark, works on dark headers.

### Existing Code Reference

The prototype at `docs/prototypes/subway-map-v6/index.html` has:
- CSS theme variables (lines 15-225)
- "Production Line" mode header in Floor component (lines 1070-1085)
- ProjectTree component (lines 848-917)

### Color Values (from prototype)

```css
/* Industrial theme - use for headers */
--bg-canvas: #0b1120;      /* Deep navy - good for Tier 1 */
--bg-panel: #0f172a;       /* Slightly lighter - good for Tier 2 */
--border-panel: #1e293b;   /* Border color */
--text-primary: #f1f5f9;   /* White text */
--text-muted: #94a3b8;     /* Gray text (tagline) */
```

### Hierarchy Reminder

```
THE COMBINE          = The factory (system identity)
Production Line      = The assembly line (mode/view)
Project              = The workpiece (job on the line)
Documents            = Artifacts that emerge (not navigation)
```

Tier 1 is the factory sign bolted to the building.
Tier 2 is the machine control panel.
Left rail is the job queue.

### Authentication Check

Use existing auth state to determine which header to show:
- `isAuthenticated` or equivalent from auth context
- Logged out → 64px header with tagline, no utility icons
- Logged in → 48px header, no tagline, utility icons

### State Legend

Consider moving state legend (Stabilized/Active/Queued dots) from floor canvas to bottom of left rail sidebar. This frees canvas space and keeps floor metadata anchored to navigation.
