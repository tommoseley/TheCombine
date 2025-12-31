# The Combine — Design Constitution & Design Tokens (v1.0)

**Status:** Active  
**Last Updated:** 2025-12-14  

This document translates *The Combine Design Manifesto* into enforceable design standards.  
Each token functions as a UI architectural decision record (ADR): what we decided, why, and what we explicitly do not allow.

These tokens govern all visual and interaction design for The Combine.

---

## 1. Quiet Palette

**Definition**  
A restrained, neutral color system where color exists to convey meaning and hierarchy, not personality or decoration.

**Usage Rules**  
- Use off-white or very light gray backgrounds to reduce eye strain.  
- Use near-black or charcoal for primary text; muted gray for secondary text.  
- Use **one** primary accent color (restrained blue) for primary actions and selection states.  
- Status colors (green / amber / red) are reserved strictly for state and outcome.  
- Large surfaces remain neutral; color is applied sparingly and intentionally.

**Rationale**  
A quiet palette lowers cognitive load and supports long sessions of focused work.  
In The Combine, color is informational infrastructure, not visual styling. When color is rare, it becomes trustworthy.

**When *Not* to Use It**  
- Do not use bright or saturated colors to “add energy.”  
- Do not introduce secondary accent palettes per feature.  
- Do not use color purely for aesthetics or brand expression inside the application.

---

## 2. Anchored Panels

**Definition**  
A stable, spatial layout where core regions of the interface occupy consistent, predictable positions on screen.

**Usage Rules**  
- Left panel: navigation and hierarchy (projects, epics, artifacts).  
- Center panel: the primary workspace and current artifact.  
- Right panel: contextual activity, validation, and history.  
- Panels may collapse or expand, but never float, overlap, or relocate.  
- On smaller screens, panels may **stack or collapse**, but their **roles must remain unchanged**.  
- Critical actions appear in consistent locations across all artifacts.

**Rationale**  
Spatial consistency builds muscle memory. Users should know *where* to look without thinking.  
Anchored panels turn the interface into a mental map rather than a sequence of screens.

**When *Not* to Use It**  
- Do not introduce floating tool palettes or draggable panes.  
- Do not change panel roles per screen or workflow.  
- Do not center critical navigation or status in transient modals.

---

## 3. Structured Negative Space

**Definition**  
Intentional, rule-based spacing used to group information, establish hierarchy, and maintain legibility under high information density.

**Usage Rules**  
- Use generous internal padding within panels (approximately 24–32px).  
- Use consistent vertical spacing between sections (minimum ~32px).  
- Use line height that favors readability (around 1.6 for body text).  
- Use spacing—not boxes or heavy borders—as the primary grouping mechanism.

**Rationale**  
The Combine is dense by necessity. Negative space is what makes that density usable.  
Structured space allows users to scan, orient, and reason without fatigue.

**When *Not* to Use It**  
- Do not compress spacing to “fit more on the screen.”  
- Do not rely on visual clutter (lines, boxes, shadows) instead of spacing.  
- Do not create vast empty canvases that hide useful density.

---

## 4. Status Color Meaning

**Definition**  
A strict, limited color vocabulary used exclusively to communicate system and workflow state.

**Usage Rules**  
- Green: complete, validated, or safe.  
- Amber: needs attention, review, or input.  
- Red: error, blocked, or failed.  
- Blue: in progress or actively running.  
- Status color is always paired with text or iconography for accessibility.  
- The same status color always means the same thing everywhere.

**Rationale**  
Executives and PMs scan for state, not decoration.  
When status colors are consistent and rare, users can assess risk and progress in seconds.

**When *Not* to Use It**  
- Do not use status colors for emphasis, branding, or decoration.  
- Do not invent new status colors for edge cases.  
- Do not overload a single color with multiple meanings.

---

## 5. Boring Buttons

**Definition**  
Buttons that are visually restrained, clearly labeled, and optimized for predictability over delight.

**Usage Rules**  
- Use simple shapes, minimal elevation, and restrained contrast.  
- Button labels use explicit verbs: *Generate, Review, Approve, Advance*.  
- Labels must clearly indicate what will happen when clicked, including cost or impact when relevant.  
- Primary, secondary, and tertiary buttons are visually distinct but not dramatic.

**Rationale**  
Buttons represent commitment. In an enterprise tool, confidence comes from clarity, not excitement.  
“Boring” buttons reduce hesitation and prevent accidental actions.

**When *Not* to Use It**  
- Do not use playful language, jokes, or conversational phrasing.  
- Do not animate buttons to attract attention.  
- Do not restyle buttons per feature or workflow.

---

## 6. Dense but Legible

**Definition**  
A design stance that accepts high information density while enforcing strict rules for readability, hierarchy, and endurance.

**Usage Rules**  
- Prefer multiple clearly separated sections over a single scrolling mass.  
- Use typography hierarchy (size, weight) instead of color or decoration.  
- Ensure body text remains readable for multi-hour sessions (minimum ~15px).  
- Optimize for scanning: headings, summaries, and status should surface first.

**Rationale**  
The Combine handles complex, multi-layered work.  
Hiding information reduces trust; presenting it poorly causes fatigue.

**When *Not* to Use It**  
- Do not simplify by removing necessary information.  
- Do not trade readability for compactness.  
- Do not collapse complexity into long prose or chat-style transcripts.

---

## Governance & Deviation Policy

These tokens are **defaults, not suggestions**.

Any deviation must demonstrate a measurable improvement in **clarity**, **reduced friction**, or **user trust**.  
Proposed deviations require written justification and explicit approval by the **Design Lead or Product Lead**.

Flexibility that undermines consistency is a defect.

---

*The Combine is enterprise infrastructure. Design accordingly.*
