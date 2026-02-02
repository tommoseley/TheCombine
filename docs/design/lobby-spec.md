# The Combine — Lobby Design Specification

## 1. Purpose

The Lobby is the sole logged-out experience for The Combine.

Its purpose is to:

- Orient first-time visitors
- Establish trust and seriousness
- Explain what happens when a user enters the system
- Invite authentication

The Lobby must not preview, simulate, or expose any production mechanics.

**Clarification:** All logged-out users (first-time or returning) are routed to the Lobby.

---

## 2. Design Principles

The Lobby is governed by the following principles:

**Separation of Worlds**
The Lobby is not part of the Production Line.
No production UI elements may appear.

**Orientation Over Demonstration**
The Lobby explains how the system works, not how to use it.

**Calm Authority**
No hype language, animations, or gimmicks.
Confidence comes from restraint.

**Single Primary Action**
All interaction funnels toward authentication.

**Irreversibility**
Once authenticated, the Lobby is no longer visible.

---

## 3. What the Lobby Is (and Is Not)

### 3.1 The Lobby Is

- A conceptual entry point
- A narrative explanation of The Combine
- A marketing-adjacent but product-owned surface
- Stateless and non-interactive (beyond navigation)

### 3.2 The Lobby Is Not

- A dashboard
- A read-only Production Line
- A sample project
- A document viewer
- A feature tour
- A prompt interface

---

## 4. Information Architecture

### 4.1 Global Header (Logged Out)

Persistent, full-width, fixed height

**Contents:**
- Brand mark (logo + wordmark)
- Tagline

**Example:**
```
THE COMBINE
Industrial AI for Knowledge Work
```

**Constraints:**
- No user controls
- No mode indicators
- No project context

### 4.2 Primary Content Area

The Lobby body consists of three vertical sections, centered and spaced generously.

#### Section 1: Identity & Value Proposition

**Goal:** Answer "What is this?"

**Content:**
- One declarative headline
- One supporting paragraph

**Example structure:**
```
Turn complex intent into governed, repeatable artifacts.
```

Supporting copy should emphasize:
- Discipline over speed
- Traceability over creativity
- Production over prompting

No feature lists.
No technical jargon.

#### Section 2: How It Works (Conceptual Flow)

**Goal:** Answer "What happens when I step inside?"

This is a conceptual sequence, not a UI walkthrough.

**Structure:**
1. User expresses intent
2. System assembles a production line
3. Documents move through quality gates
4. Approved outputs are stabilized and bound

**Constraints:**
- No screenshots
- No diagrams of the actual floor
- No node visuals
- No document names beyond generic terms

Language should match internal vocabulary:
- Production Line
- Stations
- Quality gates
- Artifacts

#### Section 3: Trust & Control Signals

**Goal:** Answer "Why should I trust this?"

**Content examples:**
- Outputs are auditable
- Decisions are traceable
- Nothing ships without validation
- Humans remain accountable

This section should be short and sober — no badges, no logos, no testimonials (yet).

---

## 5. Primary and Secondary Actions

### 5.1 Primary Action (Required)

A single, visually dominant call to action:

**"Sign in to start a Production Line"**

This button:
- Initiates authentication
- Is visually distinct
- Appears only once

### 5.2 Secondary Actions (Optional)

Subdued links:
- Learn More
- Pricing
- Documentation

**Constraints:**
- Visually secondary
- No competing colors
- No modal takeovers

### 5.3 "Learn More" Behavior

"Learn More" navigates to a separate information page while remaining logged out.

**What Not to Do:**

- Don't place "Learn More" near the primary CTA
- Don't style it as a button
- Don't animate it
- Don't let it explain "how to use the system"

If someone clicks "Learn More", they're saying: *"Convince me."*

The Lobby already says: *"This is serious."*

---

## 6. Footer

Minimal and quiet.

**Allowed:**
- Copyright
- Legal links (Terms, Privacy)

**Not allowed:**
- Navigation
- Status
- Versioning
- System metadata

---

## 7. Visual Design Constraints

- No canvas
- No zoom controls
- No minimap
- No node metaphors
- No animations beyond subtle hover states
- Palette matches the system but at lower contrast

The Lobby should feel like:

> The quiet space before heavy machinery.

---

## 8. Authentication Transition

### 8.1 Transition Requirement

Upon successful authentication:
- Lobby is dismissed entirely
- User is routed directly to the Production Line
- No back navigation to Lobby

This transition should feel decisive, not playful.

**Optional (later):**
- Brief fade or hard cut
- No loading metaphors

---

## 9. Analytics & Measurement (Optional but Recommended)

**Track:**
- Lobby views
- Sign-in conversions
- Time spent before authentication
- Exit points

**Do not track:**
- Scroll depth obsessively
- Micro-interactions

---

## 10. Explicit Non-Goals

The Lobby will not:

- Teach users how to operate the system
- Allow experimentation
- Show sample outputs
- Allow partial access
- Function as a demo

All of that happens inside the factory.

---

## 11. Success Criteria

The Lobby is successful if:

- First-time users understand what kind of system this is
- No user is confused about whether they are "already inside"
- Authentication feels like crossing a threshold
- The Production Line feels heavier, more serious by contrast
