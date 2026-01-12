# Document System Cleanup & Governance Alignment

## Canonical Charter v3 (Consolidated)

| | |
|---|---|
| **Status** | Accepted |
| **Effective** | 2026-01-12 |
| **Implementation** | See `document-cleanup-plan.md` |
| **Governance Analysis** | See `adr-amendment-analysis.md` |

---

## Executive Intent

This plan transitions The Combine's document system from a fast-moving prototype into a durable, explainable, production-grade platform by eliminating three systemic failure modes:

1. **Config Drift** (code vs DB)
2. **Schema Drift** (latest schema vs historical documents)
3. **Route Drift** (implicit, duplicated, deprecated paths)

It does so without slowing iteration, by:

- Making UX tunable via data (not code)
- Preserving backward compatibility via schema hashes
- Enforcing determinism via golden renders
- Keeping governance focused on mechanics, not presentation

---

## 1. Architectural North Star (Frozen)

### 1.1 RenderModelV1 Is the Hourglass Waist

All document rendering flows through RenderModelV1.

**Viewers never depend on:**
- docdefs
- schemas
- prompt logic

**Builders never depend on UI.**

**Fragments never infer semantics.**

```
LLM Output
   ↓
Validation + Projection
   ↓
Stored Document
   ↓
RenderModelBuilder
   ↓
RenderModelV1  ← sole rendering contract
   ↓
Fragments → HTML
```

**Invariant:** LLM output is never rendered directly.

---

## 2. What We're Fixing (The Three Drifts)

### 2.1 Config Drift (Highest Priority)

**Problem:** Hardcoded `DOCUMENT_CONFIG` shadows the database → ghost bugs.

**Fix (Phase 1):**
- Move `view_docdef_prefix` into `document_types`
- DB becomes the only source of truth
- Code no longer contains fallback config

**Outcome:** You can change how a document renders without a deploy.

### 2.2 Schema Drift (Critical Missing Piece)

**Problem:** Schemas evolve; old documents silently break.

**Fix (Phase 2):**
- Every stored document persists `schema_bundle_sha256`
- Viewer resolves schemas by hash, never by "latest"

**New Rule (Frozen):**

> **If the schema changed, the document did not.**

This enables:
- Viewing historical documents safely
- Refactoring schemas without fear
- Deterministic replay

### 2.3 Route Drift

**Problem:** Multiple overlapping routes with implicit behavior.

**Fix (Phases 5 & 7):**
- Single canonical READ route
- All old routes:
  - Redirect
  - Emit `Warning: 299 Deprecated`
  - Logged for monitoring

**No silent removals. Ever.**

---

## 3. Document Lifecycle (New, Frozen)

Documents are stateful.

```
missing → generating → partial → complete → stale
                ↑                              |
                +——————— regenerate ———————————+
```

| State | Renderable | Meaning |
|-------|------------|---------|
| `missing` | ❌ | No document exists |
| `generating` | ✅ | Skeleton + progress |
| `partial` | ✅ | Some sections done |
| `complete` | ✅ | Fully built |
| `stale` | ✅ | Outdated but viewable |

**Invariants:**
- Partial documents are valid
- Stale documents are viewable
- Staleness only propagates downstream

This resolves async UX + boredom cleanly.

---

## 4. Projection Is First-Class (Not a Hack)

**Key Insight:** Summary documents must intentionally lose information.

| Document | Stores | Links To |
|----------|--------|----------|
| EpicBacklog | Epic summaries | EpicArchitecture |
| StoryBacklog | Story summaries | StoryDetail |
| StoryDetail | Full BA output | — |

**Rule:** Projection is explicit, deliberate, and governed.

This fixes:
- Overloaded views
- Leaking BA detail everywhere
- Async generation complexity

---

## 5. Viewer Tabs (Rewritten & Frozen)

### Core Principle

> **Tabs are configuration, not architecture.**

You may:
- Add tabs
- Rename tabs
- Reorder tabs
- Move sections between tabs

…without a WS, ADR, or code change.

### 5.1 How Tabs Are Defined (Data-Driven)

At the section level:

```json
"viewer_tab": {
  "id": "epics",
  "label": "Epics",
  "order": 20
}
```

### 5.2 Discovery Rules (Viewer Behavior)

1. Scan all sections
2. Collect unique `viewer_tab.id`
3. Sort by `order` (default = 100)
4. Render dynamically

**No registry. No whitelist. No enum.**

### 5.3 Default Tab Logic

1. If `default_viewer_tab` exists → use it
2. Else → first tab by order
3. If no tabs → no tabs UI

### 5.4 Empty Tab Suppression

Tabs with zero sections are not rendered.

This enables:
- Optional tabs
- Conditional tabs
- Progressive disclosure

### 5.5 Governance Boundary (Explicit)

| Change | Requires WS / ADR |
|--------|-------------------|
| Add / rename / reorder tab | ❌ No |
| Move section between tabs | ❌ No |
| Change tab discovery mechanics | ✅ Yes |
| Add tab-specific behavior | ✅ Yes |

---

## 6. Data-Driven UX (Strategic Advantage)

### Philosophy

> **If it's presentation, it's data.**

### Tunable Without Code

- CTAs
- Badges
- Display variants
- Collapse rules
- Visibility rules
- Metadata display

### Example

```json
"primary_action": {
  "label": "Generate Epic Stories",
  "icon": "sparkles",
  "variant": "primary"
}
```

This is how you get rules-based UX without governance fatigue.

---

## 7. Golden Trace Renders (Non-Negotiable)

### Why

You're changing the engine while driving.

### Rule

- RenderModel snapshots are checked into Git
- Structural changes fail tests
- Humans must review diffs

**This is your seatbelt during refactors.**

---

## 8. Breaking-Change Safety Policy (Added)

### Schema Evolution Rule

- New schema = new semver
- Old documents keep old hash
- Viewer uses persisted hash

### Deployment Safety

- Legacy templates behind feature flag
- Flip env var to rollback in seconds
- No redeploy required

---

## 9. Routing Contract (Clarified)

### READ (View Only)
```
GET /projects/{project_id}/documents/{doc_type_id}
```

### COMMAND (Mutating)
```
POST /api/commands/{domain}/{action}
→ returns task_id
```

### SSE (Preferred)
```
GET /api/commands/.../stream
```

**Polling is deprecated. SSE is canonical.**

---

## 10. Implementation Phases (Quick Reference)

| Phase | Goal | Drift Addressed |
|-------|------|-----------------|
| 1 | Config → DB only | Config |
| 2 | Schema hash persistence | Schema |
| 3 | Document lifecycle states | — |
| 4 | Staleness propagation | — |
| 5 | Route deprecation with warnings | Route |
| 6 | Legacy template feature flag | — |
| 7 | Command route normalization | Route |
| 8 | Debug routes to dev-only | — |
| 9 | Data-driven UX (optional) | — |

See `document-cleanup-plan.md` for detailed steps, tests, and rollback procedures.

---

## 11. Governance Impact Summary

### Superseded

- **WS-DOCUMENT-VIEWER-TABS** (enum-based tabs)

### Amended

- **ADR-031** (schema hash persistence)
- **ADR-033** (RenderModel includes state)
- **ADR-034-A/B** (data-driven UX fields)

### New

- **ADR-036**: Document Lifecycle & Staleness

### Unchanged

- Shape semantics
- Fragment contracts
- Summary view contracts

---

## 12. What This Unlocks

- **React migration becomes mechanical** (RenderModel is stable)
- **User-authored documents become safe** (schema versioning)
- **Concurrent generation scales** (partial state + staleness)
- **New document types require no code** (data-driven composition)
- **The system becomes explainable** to new engineers

---

## Final Verdict

This plan:

- Aligns architecture, UX, and async reality
- Separates governance from iteration
- Makes React migration mechanical, not risky
- Supports user-authored documents safely
- Turns The Combine from clever → durable

**Most importantly:**

> You are no longer building "documents."
> **You are building a document system.**
