# Design Principles

## Source Documents

- [Design Manifesto](../archive/the-combine-design-manifesto.md) -- foundational philosophy
- [UX Reference](../project/THE_COMBINE_UX_REFERENCE.md) -- interaction patterns and mental model
- [Branding Instructions](../branding_instructions.md) -- header hierarchy and factory metaphor

---

## Core Identity: Calm Authority

The Combine is a knowledge factory, not a content app. When users open it, their shoulders should drop. The interface communicates competence through restraint, not excitement through novelty.

If users notice the interface more than their work, the design has failed.

---

## The Industrial Metaphor

The Combine uses a manufacturing metaphor throughout its visual language and terminology:

| Concept | Metaphor | UI Surface |
|---------|----------|------------|
| The Combine | The factory | System identity (Tier 1 header) |
| Production Line | The assembly line | Mode header + canvas |
| Project | The workpiece | Left rail sidebar |
| Documents | Artifacts that emerge | Node cards on canvas |
| Stations | Processing steps | Station dots on nodes |

This metaphor is not decorative. It structures the entire user experience: projects move through production lines, documents are produced at stations, and quality gates determine when artifacts are stabilized.

---

## The Seven Principles

### 1. Color as Information

Color conveys state, never decoration. The four artifact states (Stabilized, In Progress, Ready, Blocked) each have a dedicated color that is consistent across all three themes. If a color cannot be named as a state, it does not belong in the UI.

### 2. Three Themes, One Truth

Industrial (default), Light, and Blueprint themes offer visual variety while preserving identical semantics. All status meanings, hierarchy, and interactions survive theme switching. A design that only works in one theme is defective.

### 3. Structured Negative Space

Dense information requires space to be legible. Panels use consistent padding (12-16px), nodes maintain clear separation, and the canvas provides breathing room. Density is a feature; clutter is a bug.

### 4. State Over Decoration

Animated glows, pulsing dots, and station progress lines all communicate state -- they are never cosmetic. Active nodes glow amber because they need attention. Station dots pulse because they await input. Every visual effect maps to a system truth.

### 5. Boring Buttons Are Good Buttons

Button labels use explicit verbs: View Document, Start Production, Answer Questions. Labels answer "what happens when I click this?" No conversational tone. No personality. Button color matches the artifact state it acts upon.

### 6. Consistency Builds Trust

The same action always appears in the same place. The same colors always mean the same thing. The same layout structure across all node types. Predictability is the feature.

### 7. Spatial Over Temporal

Three-region structure: left sidebar (project hierarchy), center canvas (production floor), right sidecars (document content, question trays). Users always know where they are and what they are viewing. Content is arranged spatially, not as a chat stream.

---

## Design Review Litmus Tests

Every UI change must pass all five:

1. Does it read correctly in all three themes?
2. Does it make sense without color (structure + text alone)?
3. Does it reduce cognitive load, not increase it?
4. Does it help the user make a safer decision?
5. Is it reinforcing truth, not aesthetics?

A single "no" blocks the change.

---

## What We Never Do

- Gradients
- AI personality avatars
- Marketing language in the production interface
- Thin fonts or pure white backgrounds
- Surprises in interaction patterns
- Clever animations unrelated to state
- Color-only status indicators (must have text backup)
- Colored background fills for semantic sections (use border-left instead in content blocks)

---

## Success Metrics

- Can a director scan the canvas and understand project status in 3 seconds?
- Can a PM work for 4 hours without eye strain?
- Does the tool feel like serious industrial software, not a demo?

If yes to all three, the design succeeds.
