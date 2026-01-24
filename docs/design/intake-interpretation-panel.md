# Intake Interpretation Panel Design

## Status: Draft
## Author: Tom Moseley / AI Collaboration
## Date: 2026-01-20

---

## 1. Problem Statement

The current Intake system uses a pure chat interface. While simple, it has limitations:

1. **Opacity**: Users cannot see what the system has understood until the conversation ends
2. **Correction Friction**: Fixing misunderstandings requires chat ("No, that's wrong")
3. **No Verification Step**: Users proceed without confirming key assumptions

The proposed solution adds a structured interpretation panel with explicit user verification.

---

## 2. Design Principles

### 2.1 Single-Writer Ownership

**Rule**: The Concierge owns a field until the user interacts with it.

Each interpreted field is stored as:

```json
{
  "project_name": {
    "value": "WarmPulse",
    "source": "llm",
    "locked": false,
    "updated_at": "2026-01-20T14:30:00Z"
  }
}
```

| Field | Type | Description |
|-------|------|-------------|
| `value` | any | The interpreted or user-provided value |
| `source` | enum | `"llm"`, `"user"`, `"default"` |
| `locked` | boolean | If true, Concierge cannot modify this field |
| `updated_at` | datetime | Last modification timestamp |

**Behavior**:
- When user edits a field: `source` → `"user"`, `locked` → `true`
- Concierge MUST check `locked` before updating any field
- Locked fields are visually distinguished (user badge, different styling)

### 2.2 Gated Transition (Not Live Dashboard)

The interpretation panel is NOT a real-time extraction display. It follows a reveal-then-verify pattern:

```
┌─────────────────────────────────────────────────────────────┐
│  PHASE 1: DESCRIBE                                          │
│  - User writes freeform project description                 │
│  - Panel is collapsed/hidden                                │
│  - Concierge processes silently                             │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 2: CLARIFY (Optional, 0-1 questions)                 │
│  - Only if critical metadata cannot be inferred             │
│  - Single high-value question, not interrogation            │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│  PHASE 3: REVIEW & LOCK                                     │
│  - Panel reveals with "Working Assumptions" header          │
│  - User reviews 3-5 key fields                              │
│  - User can edit any field (locks it)                       │
│  - "Initialize Project Discovery" enabled when ready        │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Deterministic Confidence

Confidence is NOT a mystical LLM score. It is calculated from required metadata:

```
confidence = filled_required_fields / total_required_fields
```

**Required Fields for Intake**:
- `project_name` (string, non-empty)
- `project_type` (enum: product, service, research, internal)
- `primary_goal` (string, non-empty)
- `key_stakeholders` (array, at least 1)

**Threshold**: 1.0 (all required fields must be filled)

**UI Behavior**:
- If confidence < 1.0: Show "Missing: [field_name]" indicators
- User can fill missing fields manually to reach threshold
- "Initialize Project Discovery" button disabled until threshold met

---

## 3. Data Model Integration

### 3.1 Context State Schema

The `context_state` field in `workflow_executions` adopts this structure:

```json
{
  "interpretation": {
    "project_name": { "value": "...", "source": "llm", "locked": false, "updated_at": "..." },
    "project_type": { "value": "...", "source": "user", "locked": true, "updated_at": "..." },
    "primary_goal": { "value": "...", "source": "llm", "locked": false, "updated_at": "..." },
    "key_stakeholders": { "value": [...], "source": "llm", "locked": false, "updated_at": "..." },
    "potential_risks": { "value": [...], "source": "llm", "locked": false, "updated_at": "..." }
  },
  "confidence": 0.75,
  "missing_fields": ["key_stakeholders"],
  "phase": "review"
}
```

### 3.2 Field Definitions

Defined in seed data (not hardcoded):

```json
{
  "intake_fields": [
    {
      "key": "project_name",
      "label": "Project Name",
      "type": "string",
      "required": true,
      "editable": true
    },
    {
      "key": "project_type",
      "label": "Project Type",
      "type": "enum",
      "options": ["product", "service", "research", "internal"],
      "required": true,
      "editable": true
    },
    {
      "key": "primary_goal",
      "label": "Primary Goal",
      "type": "text",
      "required": true,
      "editable": true
    },
    {
      "key": "key_stakeholders",
      "label": "Key Stakeholders",
      "type": "array",
      "required": true,
      "editable": true
    },
    {
      "key": "potential_risks",
      "label": "Potential Risks",
      "type": "array",
      "required": false,
      "editable": true
    }
  ]
}
```

---

## 4. UI Components

### 4.1 Interpretation Panel (Right Pane)

```
┌──────────────────────────────────────┐
│  // WORKING ASSUMPTIONS              │
│  ──────────────────────────────────  │
│                                      │
│  Project Name                        │
│  ┌────────────────────────────────┐  │
│  │ WarmPulse              [✎ Edit]│  │
│  └────────────────────────────────┘  │
│                                      │
│  Project Type                        │
│  ┌────────────────────────────────┐  │
│  │ Product           [✓ Verified] │  │  ← User edited, now locked
│  └────────────────────────────────┘  │
│                                      │
│  Primary Goal                        │
│  ┌────────────────────────────────┐  │
│  │ ⚠ Missing - Click to add       │  │  ← Required but empty
│  └────────────────────────────────┘  │
│                                      │
│  Key Stakeholders                    │
│  ┌────────────────────────────────┐  │
│  │ • Alex (Tech Lead)    [✎ Edit] │  │
│  │ • Sarah (Product Owner)        │  │
│  └────────────────────────────────┘  │
│                                      │
│  ──────────────────────────────────  │
│  Confidence: 75% (1 field missing)   │
│                                      │
│  ┌────────────────────────────────┐  │
│  │  INITIALIZE PROJECT DISCOVERY  │  │  ← Disabled until 100%
│  └────────────────────────────────┘  │
└──────────────────────────────────────┘
```

### 4.2 Visual States

| State | Styling | Icon |
|-------|---------|------|
| LLM-inferred | Default background | ✎ (pencil) |
| User-verified | Light green tint | ✓ (checkmark) |
| Missing required | Yellow/warning tint | ⚠ (warning) |
| Locked (user-edited) | Subtle border | 🔒 (lock) |

### 4.3 Panel Visibility by Phase

| Phase | Panel State |
|-------|-------------|
| `describe` | Collapsed or hidden |
| `clarify` | Collapsed, expandable |
| `review` | Expanded, primary focus |

---

## 5. Concierge Integration

### 5.1 Field Update Protocol

The Concierge (LLM) MUST follow this protocol when updating interpretation:

```python
def update_interpretation_field(context_state, field_key, new_value):
    interpretation = context_state.get("interpretation", {})
    field = interpretation.get(field_key, {})
    
    # CRITICAL: Never overwrite locked fields
    if field.get("locked", False):
        return  # Skip silently
    
    # Update the field
    interpretation[field_key] = {
        "value": new_value,
        "source": "llm",
        "locked": False,
        "updated_at": datetime.utcnow().isoformat()
    }
    
    context_state["interpretation"] = interpretation
    recalculate_confidence(context_state)
```

### 5.2 Generation Prompt Update

The Intake Generation prompt must be updated to:
1. Output structured interpretation fields
2. Respect locked field indicators in context
3. Not re-explain fields the user has already verified

---

## 6. Transition to Project Discovery

When user clicks "Initialize Project Discovery":

1. Create `intake_document` with:
   - All interpretation fields
   - Provenance metadata (source, locked, timestamps)
   - Original user input preserved

2. Create `Project` record with:
   - `project_id` generated from project_name
   - `name` from interpretation
   - `owner_id` from current user

3. Workflow transitions to `end_stabilized` with:
   - `gate_outcome`: "qualified"
   - `terminal_outcome`: "stabilized"

4. User redirected to new project's Discovery document

---

## 7. Migration Path

### 7.1 Current State
- Intake uses chat-only interface
- Real-time extraction board (experimental)
- No structured verification step

### 7.2 Target State
- Phased flow: Describe → Clarify → Review
- Interpretation panel with single-writer locking
- Deterministic confidence gate

### 7.3 Implementation Order
1. Add interpretation schema to context_state
2. Update Concierge to populate interpretation fields
3. Build Review panel UI component
4. Add field editing endpoints
5. Implement confidence calculation
6. Add "Initialize Project Discovery" flow
7. Remove/deprecate real-time extraction board

---

## 8. Open Questions

1. **Unlock mechanism?** - Should users be able to "unlock" a field to let the Concierge re-infer it? (Recommendation: No for v1, add if needed)

2. **Optional rationale?** - Should user edits allow an optional 1-sentence rationale? (Recommendation: No for v1, provenance via source/timestamp is sufficient)

3. **Field ordering?** - Should field display order be fixed or dynamic based on confidence? (Recommendation: Fixed order, clearer mental model)

---

## 9. Success Metrics

- **Reduced correction chat turns**: Target < 0.5 corrections per intake
- **Faster intake completion**: Target < 3 minutes average
- **Higher user verification rate**: Target > 90% users review before proceeding

---

## References

- ADR-037: Document Contracts and Quality Gates
- ADR-039: Workflow Execution Model
- ADR-040: Context State Management