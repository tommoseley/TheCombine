# The Combine — MVP Roadmap

**Date:** 2026-01-02  
**Status:** Approved  
**Target:** 3-4 weeks

---

## Strategic Position

The Combine is a **governed execution engine**, not an AI assistant.

- Intelligence is constrained by structure
- UX is a projection of state, not a conversation
- Documents are primary; conversations are transient

This roadmap builds the engine before the experience.

---

## Foundation (What We Have)

### Accepted ADRs (Governance Spine)

| ADR | Title |
|-----|-------|
| 011 | Document Ownership Model |
| 012 | Interaction Model (v1.1) |
| 024 | Clarification Question Protocol |
| 027 | Workflow Definition & Governance |

### Implemented

| ADR | Title |
|-----|-------|
| 007 | Sidebar Document Status |
| 008 | Multi-Provider OAuth |
| 009 | Project Audit |
| 010 | LLM Execution Logging |

### Existing Seed Artifacts

- 7 role prompts
- 8 task prompts
- 2 schemas (clarification_question_set, intake_gate_result)
- Implementation Model (ADR-027)

---

## Phase 0: Schema & Validation (1-2 days)

**Goal:** Fail-fast validation before any execution exists

| Task | Deliverable |
|------|-------------|
| Create workflow schema | `seed/schemas/workflow.v1.json` |
| Implement WorkflowValidator | `app/domain/workflow/validator.py` |
| Validate ownership DAG | ADR-011 §3 |
| Validate reference rules | ADR-011 §5 |
| Validate scope consistency | Child ≤ Parent |

**Exit Criteria:**

- ✅ Can load and validate a workflow definition
- ✅ Can reject invalid workflow with actionable errors

**Validation must catch:**
- Cyclic ownership
- Invalid scope references
- Illegal sibling references
- Missing document types
- Malformed iteration blocks

---

## Phase 1: Step Executor (3-5 days)

**Goal:** Single step executes per ADR-012

| Task | Deliverable |
|------|-------------|
| Implement StepExecutor | `app/domain/workflow/step_executor.py` |
| Clarification gate | ADR-024 schema, questions-only mode |
| QA gate | Pass/fail evaluation |
| Remediation loop | Bounded retry with findings |
| State machine | pending → executing → completed/failed |

### QA Gate Constraints (MVP)

QA is **mechanical only**:

- Schema validation
- Structural rules
- Required field presence
- No domain intelligence
- No probabilistic judgments

Intelligence creep is prohibited.

**Exit Criteria:**

- ✅ Can execute Discovery step end-to-end
- ✅ Clarification gate enforces questions-only
- ✅ QA gate passes/fails based on schema
- ✅ Remediation loop bounded and logged

---

## Phase 2: Workflow Executor (2-3 days)

**Goal:** Multi-step workflow with iteration

| Task | Deliverable |
|------|-------------|
| Implement WorkflowExecutor | `app/domain/workflow/executor.py` |
| WorkflowContext | Scope-aware document storage |
| Iteration blocks | `iterate_over` for epics/stories |
| State persistence | Resume from paused step |
| Acceptance gate | Human approval flow |

### Acceptance Gate Scope (MVP)

Minimal implementation:

- Boolean accept/reject
- Comment field
- No versioning
- No attribution (defer to ADR-021)

**Exit Criteria:**

- ✅ Can run Discovery → Epic Backlog → Architecture
- ✅ Iteration works for multiple epics
- ✅ Can pause and resume at acceptance
- ✅ State survives restart

---

## Phase 3: First Workflow (2-3 days)

**Goal:** Software Product Development workflow end-to-end

| Task | Deliverable |
|------|-------------|
| Create workflow definition | `seed/workflows/software_product_development.v1.json` |
| Verify task prompts | Align with step declarations |
| Wire to handlers | Replace mentor-centric handlers |
| Test iteration | Multiple epics → multiple stories |

**This phase is wiring, not inventing.**

**Exit Criteria:**

- ✅ Discovery → Epic Backlog → Architecture → Epic Architecture → Story Backlog
- ✅ Per-epic iteration works
- ✅ Per-story iteration works
- ✅ All outputs logged per ADR-010

---

## Phase 4: Intake Integration (2-3 days)

**Goal:** Concierge gates project entry

| Task | Deliverable |
|------|-------------|
| Accept ADR-025, ADR-026 | Governance approval |
| Implement Concierge Intake | Pre-workflow gate |
| Intake → Workflow routing | Qualification triggers workflow |
| Project creation | Intake artifact seeds project |

**Intake is qualification, not discovery.**

**Exit Criteria:**

- ✅ User starts from blank
- ✅ Concierge qualifies or rejects
- ✅ Qualified intake creates project
- ✅ Workflow begins automatically

---

## Phase 5: UI Alignment (3-5 days)

**Goal:** Document-centric interface

| Task | Deliverable |
|------|-------------|
| Update project view | Workflow progress, not mentor chat |
| Document cards | Status per ADR-007 |
| Acceptance UI | Accept/reject with comment |
| Clarification UI | Question/answer flow |
| Step state display | Show pause points |

### UI Design Constraints

**Non-negotiable:**

- No chat-first UI
- No "mentor" framing
- Documents are primary
- Conversations are transient
- State is visible, not hidden

**Exit Criteria:**

- ✅ User sees documents, not threads
- ✅ Workflow state is visible
- ✅ Can accept/reject from UI
- ✅ Can answer clarifications from UI

---

## Phase 6: Hardening (2-3 days)

**Goal:** Production-ready MVP

| Task | Deliverable |
|------|-------------|
| Error handling | Explicit failures surface |
| Logging completeness | ADR-009/010 compliance |
| Replay capability | Replay from logged inputs |
| Edge cases | Empty backlogs, QA exhaustion, abandonment |

**Exit Criteria:**

- ✅ No silent failures
- ✅ Full audit trail
- ✅ Can replay any step
- ✅ Graceful handling of edge cases

---

## Timeline Summary

| Phase | Duration | Cumulative |
|-------|----------|------------|
| 0: Schema & Validation | 1-2 days | 1-2 days |
| 1: Step Executor | 3-5 days | 4-7 days |
| 2: Workflow Executor | 2-3 days | 6-10 days |
| 3: First Workflow | 2-3 days | 8-13 days |
| 4: Intake Integration | 2-3 days | 10-16 days |
| 5: UI Alignment | 3-5 days | 13-21 days |
| 6: Hardening | 2-3 days | 15-24 days |

**Estimated MVP: 3-4 weeks**

---

## Critical Path

```
workflow.v1.json schema
         │
         ▼
   WorkflowValidator
         │
         ▼
    StepExecutor (ADR-012)
         │
         ▼
   WorkflowExecutor
         │
         ▼
software_product_development.v1.json
         │
         ▼
    Intake (025/026)
         │
         ▼
       UI Update
         │
         ▼
       MVP ✓
```

---

## Explicit Deferrals (Post-MVP)

| Feature | ADR | Rationale |
|---------|-----|-----------|
| Reference document upload | 028 | Users can copy/paste for MVP |
| Contextual condensing | 029 | Manual selection for MVP |
| Trust certification | 017-019 | All prompts treated as certified |
| Failure analytics | 020 | Logging exists; analysis deferred |
| Human decision capture | 021 | Accept/reject exists; attribution deferred |
| Regulatory export | 023 | Logs exist; export format deferred |

---

## Discipline Constraints

### Engine Overreach Warning

The biggest risk is trying to be clever too early.

**Do NOT:**

- Sneak condensing into StepExecutor
- Add workflow branching logic
- Let handlers introspect workflow state
- Add "one small convenience"

**The roadmap works because it's boringly mechanical at first.**

### Smell Test

If something feels like:

> "We just need one small convenience…"

That's usually scope creep. Stop and ask: "Is this MVP or MVP+1?"

---

## Success Criteria

MVP is complete when:

1. A user can start from nothing
2. Concierge qualifies the project
3. Workflow executes Discovery → Epics → Architecture → Stories
4. Each step has clarification, QA, and acceptance
5. All state is visible in a document-centric UI
6. Everything is logged and replayable

**This proves the thesis: governed execution, not conversational AI.**
