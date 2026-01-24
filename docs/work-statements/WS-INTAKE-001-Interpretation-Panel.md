
---

## Completion Note (2026-01-22)

**This Work Statement is COMPLETE.**

All phases implemented:
- Phase 1: Data Model ✓ (`app/domain/workflow/interpretation.py`)
- Phase 2: Backend ✓ (field update endpoint, confidence calculation)
- Phase 3: Frontend ✓ (interpretation panel, field editing, lock button)
- Phase 4: Integration ✓ (end-to-end flow, project creation)

**Acceptance Criteria Met:**
- [x] User can complete intake with phased flow (describe → clarify → review)
- [x] Interpretation panel shows all extracted fields
- [x] User edits lock fields from modification
- [x] Confidence calculated from required fields
- [x] Missing fields clearly indicated
- [x] Initialize button disabled until 100% confidence
- [x] Project created with correct provenance

**Implementation Divergence:**
- Confidence display removed from UI (binary: locked or not)
- "Lock & Write Concierge Intake" replaces "Initialize Project Discovery"
- Interpretation panel remains visible during generation (stacked, not replaced)

---
# WS-INTAKE-001: Intake Interpretation Panel

| | |
|---|---|
| **Work Statement** | WS-INTAKE-001 |
| **Title** | Intake Interpretation Panel with Single-Writer Locking |
| **Design Doc** | docs/design/intake-interpretation-panel.md |
| **Status** | **COMPLETE** |
| **Expected Scope** | Multi-commit (Implementation Plan) |
| **Created** | 2026-01-20 |

---

## Objective

Implement a structured interpretation panel for the Intake workflow that:
1. Shows extracted assumptions in a "Review & Lock" checkpoint
2. Allows direct field editing without chat
3. Uses single-writer locking to prevent race conditions
4. Gates Project Discovery initialization on required field completion

---

## Scope

### In Scope

1. **Phase 1: Data Model** (Single commit)
   - Add interpretation schema to `context_state`
   - Create field definition seed data
   - Add confidence calculation utility

2. **Phase 2: Backend** (Single commit)
   - Update Concierge generation prompt for structured output
   - Add field update endpoint with lock checking
   - Add confidence recalculation on field change

3. **Phase 3: Frontend** (Single commit)
   - Build interpretation panel component
   - Implement field editing UI
   - Add phase-based panel visibility
   - Wire "Initialize Project Discovery" button

4. **Phase 4: Integration** (Single commit)
   - End-to-end flow testing
   - Transition from intake → project creation
   - Deprecate real-time extraction board

### Out of Scope

- Unlock mechanism (defer to v2 if needed)
- Optional rationale capture
- Multi-tenant field definitions
- Mobile-specific layouts

---

## Preconditions

- [ ] Design document reviewed and accepted
- [ ] ADR-039 workflow execution model in place
- [ ] ADR-040 context state management in place
- [ ] Current intake workflow operational

---

## Phase 1: Data Model

### Step 1.1: Define Interpretation Field Schema

Create `seed/schemas/intake_interpretation.json`:

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "type": "object",
  "properties": {
    "interpretation": {
      "type": "object",
      "additionalProperties": {
        "type": "object",
        "properties": {
          "value": {},
          "source": { "enum": ["llm", "user", "default"] },
          "locked": { "type": "boolean" },
          "updated_at": { "type": "string", "format": "date-time" }
        },
        "required": ["value", "source", "locked", "updated_at"]
      }
    },
    "confidence": { "type": "number", "minimum": 0, "maximum": 1 },
    "missing_fields": { "type": "array", "items": { "type": "string" } },
    "phase": { "enum": ["describe", "clarify", "review"] }
  }
}
```

### Step 1.2: Create Field Definitions Seed

Create `seed/reference_data/intake_fields.json`:

```json
{
  "fields": [
    { "key": "project_name", "label": "Project Name", "type": "string", "required": true },
    { "key": "project_type", "label": "Project Type", "type": "enum", "options": ["product", "service", "research", "internal"], "required": true },
    { "key": "primary_goal", "label": "Primary Goal", "type": "text", "required": true },
    { "key": "key_stakeholders", "label": "Key Stakeholders", "type": "array", "required": true },
    { "key": "potential_risks", "label": "Potential Risks", "type": "array", "required": false }
  ]
}
```

### Step 1.3: Add Confidence Utility

Create `app/domain/workflow/interpretation.py`:

```python
"""
Interpretation field management for Intake workflow.
Single-writer locking and confidence calculation.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


def calculate_confidence(interpretation: Dict, field_definitions: List[Dict]) -> float:
    """Calculate confidence as ratio of filled required fields."""
    required_keys = [f["key"] for f in field_definitions if f.get("required")]
    if not required_keys:
        return 1.0
    
    filled = sum(
        1 for key in required_keys
        if key in interpretation and interpretation[key].get("value")
    )
    return filled / len(required_keys)


def get_missing_fields(interpretation: Dict, field_definitions: List[Dict]) -> List[str]:
    """Return list of required fields that are empty."""
    required_keys = [f["key"] for f in field_definitions if f.get("required")]
    return [
        key for key in required_keys
        if key not in interpretation or not interpretation[key].get("value")
    ]


def update_field(
    interpretation: Dict,
    key: str,
    value: Any,
    source: str = "llm"
) -> bool:
    """
    Update an interpretation field, respecting locks.
    
    Returns True if update was applied, False if field was locked.
    """
    existing = interpretation.get(key, {})
    
    # CRITICAL: Never overwrite locked fields (unless source is user)
    if existing.get("locked") and source != "user":
        return False
    
    interpretation[key] = {
        "value": value,
        "source": source,
        "locked": source == "user",  # User edits auto-lock
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    return True
```

**Verification**: Unit tests for confidence calculation and lock behavior.

---

## Phase 2: Backend

### Step 2.1: Update Generation Prompt

Modify `seed/prompts/tasks/Intake Document Generation v1.0.txt` to output structured interpretation:

```
OUTPUT FORMAT:
{
  "interpretation": {
    "project_name": "...",
    "project_type": "...",
    "primary_goal": "...",
    "key_stakeholders": [...],
    "potential_risks": [...]
  },
  "clarifying_question": "..." or null,
  "phase": "describe" | "clarify" | "review"
}
```

### Step 2.2: Add Field Update Endpoint

Create endpoint in `app/web/routes/public/intake_workflow_routes.py`:

```python
@router.patch("/intake/interpretation/{field_key}")
async def update_interpretation_field(
    field_key: str,
    value: Any = Body(...),
    execution_id: str = Query(...),
    db: AsyncSession = Depends(get_db)
):
    """Update a single interpretation field (user edit, auto-locks)."""
    # Load execution
    # Update field with source="user"
    # Recalculate confidence
    # Save state
    # Return updated interpretation
```

### Step 2.3: Integrate with Concierge

Update `intake_generation_handler.py` to:
1. Check locked fields before LLM update
2. Recalculate confidence after each turn
3. Set phase based on confidence threshold

**Verification**: Integration test for field locking behavior.

---

## Phase 3: Frontend

### Step 3.1: Create Interpretation Panel Component

Create `app/web/templates/public/components/_interpretation_panel.html`:

- Header: "// WORKING ASSUMPTIONS"
- Field cards with edit buttons
- Visual states: inferred, verified, missing, locked
- Confidence indicator
- "Initialize Project Discovery" button (disabled until 100%)

### Step 3.2: Add Field Editing

- Click edit → inline input or dropdown
- On save → PATCH to backend
- Update UI with locked state

### Step 3.3: Phase-Based Visibility

- `describe`: Panel collapsed
- `clarify`: Panel collapsed, expandable
- `review`: Panel expanded, primary

### Step 3.4: Wire Initialize Button

- Check confidence = 1.0
- Call project creation endpoint
- Redirect to new project

**Verification**: Manual testing of edit flow and phase transitions.

---

## Phase 4: Integration

### Step 4.1: End-to-End Test

Create `tests/e2e/test_intake_interpretation.py`:
1. Submit project description
2. Verify interpretation populated
3. Edit a field (verify lock)
4. Verify Concierge doesn't overwrite locked field
5. Fill missing fields
6. Initialize Project Discovery
7. Verify project created with correct data

### Step 4.2: Deprecate Extraction Board

- Remove real-time extraction board code
- Remove associated endpoints
- Update templates

### Step 4.3: Update Documentation

- Update user-facing docs
- Update AI.md if needed

---

## Prohibited Actions

- Do NOT create a live-updating extraction dashboard
- Do NOT allow Concierge to overwrite locked fields
- Do NOT proceed to Project Discovery with missing required fields
- Do NOT store rationale text (defer to v2)
- Do NOT implement unlock mechanism (defer to v2)

---

## Acceptance Criteria

1. [ ] User can complete intake with phased flow (describe → clarify → review)
2. [ ] Interpretation panel shows all extracted fields
3. [ ] User edits lock fields from Concierge modification
4. [ ] Confidence calculated from required fields
5. [ ] Missing fields clearly indicated
6. [ ] Initialize button disabled until 100% confidence
7. [ ] Project created with correct provenance (source: llm vs user)
8. [ ] All existing intake tests pass
9. [ ] New tests cover lock behavior

---

## Estimated Effort

| Phase | Estimate |
|-------|----------|
| Phase 1: Data Model | 2 hours |
| Phase 2: Backend | 4 hours |
| Phase 3: Frontend | 6 hours |
| Phase 4: Integration | 3 hours |
| **Total** | **15 hours** |

---

## References

- Design: `docs/design/intake-interpretation-panel.md`
- ADR-039: Workflow Execution Model
- ADR-040: Context State Management
- ADR-037: Document Contracts