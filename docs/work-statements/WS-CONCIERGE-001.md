
---

## SUPERSEDED NOTICE (2026-01-22)

**This Work Statement has been superseded by the mechanical sufficiency implementation.**

### What Changed

The 6-phase wizard model (Phases A-F) with question packs and LLM-driven conversation was replaced by:

1. **Mechanical sufficiency check** - Intake is complete when required fields (audience, artifact_type) are extractable
2. **Pattern-based extraction** - Regex extraction, not LLM conversation
3. **Interpretation panel** - User reviews and locks fields via UI, not chat
4. **Auto-qualification** - No multi-turn question loops

### Why

Conversational intake at the boundary created:
- Infinite question loops (no hard completion criteria)
- Unclear "done" state
- Scope creep into Discovery territory

Intake should establish an intent boundary, not resolve ambiguity. Ambiguity resolution belongs in Discovery.

### Replacement Artifacts

- `app/domain/workflow/nodes/intake_gate.py` - Mechanical sufficiency implementation
- `app/domain/workflow/interpretation.py` - Field management and confidence
- `seed/workflows/concierge_intake.v1.json` - Simplified workflow plan
- ADR-025 Amendment (2026-01-22) - Artifact-based consent
- ADR-026 Amendment (2026-01-22) - Concierge as qualification function

### Preserved from Original

- Gate outcomes (qualified, not_ready, out_of_scope, redirect)
- No project creation without explicit consent
- Append-only event storage for audit
- ADR-010 LLM execution logging

---
# Work Statement: Concierge Project Ingestion (WS-CONCIERGE-001)

**Status:** **SUPERSEDED**  
**Created:** 2026-01-14  
**Author:** AI (Claude)  
**Scope:** Single-commit implementation  
**Related ADRs:** ADR-025, ADR-026  
**Related Contracts:** CONCIERGE_PROJECT_INGESTION_CONTRACT v1.0

---

## 1. Purpose

Implement Concierge Project Ingestion as the mandatory entry point for new work in The Combine, replacing the current "Initialize New Project" flow.

This work statement implements Use Case #1 from the Concierge specification: transitioning users from curiosity to governed work context through explicit consent gates.

---

## 2. Scope

**In Scope:**
- Database tables for concierge intake sessions and events
- Concierge service with state machine and LLM reflection
- API routes for /start and /concierge/* endpoints
- UI wizard templates (phases A-F)
- Data-driven question packs (JSON)
- Modification of Project Discovery handler to accept discovery_profile
- Location and replacement of existing "Initialize New Project" flow
- Integration with existing LLM logging (ADR-010)
- Basic tests for state machine, event ordering, and handoff validation

**Out of Scope:**
- ADR-035 (Durable LLM Threaded Queue) full implementation
- Anonymous session support (future)
- Session expiry cleanup job (future)
- Dynamic question generation via LLM (future)
- Multi-artifact routing (v1 always produces project_discovery)

---

## 3. Expected Outcome

After execution:
- User navigating to /start enters a guided 6-phase wizard
- User provides intent, confirms reflection, answers max 4 clarifying questions
- User explicitly consents to project creation
- System creates Project record and triggers Project Discovery generation
- All interactions stored as append-only events
- No project or document created without explicit consent
- Old "Initialize New Project" flow redirects to /start


## 4. Governing Constraints

**Contract Compliance:**
- All event types and payload schemas MUST match CONCIERGE_PROJECT_INGESTION_CONTRACT v1.0 section 8
- State machine MUST follow transitions defined in contract section 6
- Handoff contract MUST validate against schema in contract section 8.2.6
- Maximum 4 clarifying questions enforced per contract section 13

**Governance Alignment:**
- ADR-009: All state changes explicit and auditable via events
- ADR-010: LLM calls logged with inputs, outputs, timing
- POL-WS-001: Execute steps in order, stop on ambiguity

**Discovery Profile Mapping:**
- Intent classes map to profiles per contract section 10.3
- v1 profiles: general, integrate_systems, change_existing, unknown
- Other intent classes (explore_problem, plan_work, produce_output) map to general

---

## 5. Implementation Steps

### Step 1: Question Pack Foundation

**Objective:** Create data-driven question packs as JSON

**Actions:**
1.1. Create directory: seed/question_packs/
1.2. Create file: seed/question_packs/discovery_question_packs.json
1.3. Create file: seed/question_packs/schema.json (JSON Schema for validation)
1.4. Populate 4 question packs (general, integrate_systems, change_existing, unknown)
1.5. Each pack: 2-4 questions max, following contract section 8.2.3 schema

**Verification:**
- JSON validates against schema
- All required fields present (id, prompt, reason, answer_type, required)
- No pack exceeds 4 questions

**Prohibited:**
- Do NOT create new registry service
- Do NOT add to document_types.gating_rules
- Do NOT version questions yet (v1.0 is sufficient)

---

### Step 2: Database Migration

**Objective:** Create concierge_intake_session and concierge_intake_event tables

**Actions:**
2.1. Create migration: alembic/versions/YYYYMMDD_HHMMSS_add_concierge_intake_tables.py
2.2. Define concierge_intake_session table with fields per contract section 5.1
2.3. Define concierge_intake_event table with fields per contract section 5.1
2.4. Add indexes for performance

**Verification:**
- Run migration: alembic upgrade head
- Tables exist in database
- Constraints enforced (FK, NOT NULL, unique)

**Prohibited:**
- Do NOT make user_id nullable (auth required in v1)
- Do NOT add cleanup triggers (future)

---

### Step 3: Domain Models

**Objective:** Create SQLAlchemy and Pydantic models

**Actions:**
3.1. Create file: app/api/models/concierge_intake.py
3.2. Create file: app/domain/schemas/concierge_events.py
3.3. Implement enums and schemas per contract section 7 and 8

**Verification:**
- All enums match contract exactly
- All Pydantic schemas validate against contract JSON schemas
- Models import cleanly, no circular dependencies

**Prohibited:**
- Do NOT add fields not in contract
- Do NOT create helper enums outside contract


### Step 4: Concierge Service

**Objective:** Implement state machine and business logic

**Actions:**
4.1. Create file: app/domain/services/concierge_service.py
4.2. Implement ConciergeService class with methods for session lifecycle
4.3. Implement expiry check in get_session_with_events()
4.4. Integrate with existing LLM logging (ADR-010)

**Verification:**
- Service loads question packs without error
- State transitions enforce contract rules
- LLM calls appear in llm_execution_logs table
- Expiry check works (manual test with mock timestamp)

**Prohibited:**
- Do NOT implement session cleanup job
- Do NOT allow state transitions violating contract section 6.2
- Do NOT generate questions dynamically with LLM

---

### Step 5: LLM Reflection Prompt

**Objective:** Create task prompt for intent reflection

**Actions:**
5.1. Create file: seed/prompts/tasks/Concierge Intent Reflection v1.0.txt
5.2. Define prompt that produces IntentReflectionProposed JSON
5.3. Test with sample inputs

**Verification:**
- Prompt produces valid IntentReflectionProposed JSON
- Test with sample inputs (3-5 examples)
- Output validates against Pydantic schema

**Prohibited:**
- Do NOT ask LLM to generate clarifying questions
- Do NOT allow LLM to select discovery profile (service does mapping)

---

### Step 6: API Routes

**Objective:** Implement Concierge HTTP endpoints

**Actions:**
6.1. Create file: app/api/routers/concierge_routes.py
6.2. Implement routes: /start, /concierge/new, /concierge/{session_id}/*
6.3. Register router in app/api/main.py

**Verification:**
- All routes accessible via Swagger/OpenAPI docs
- POST routes enforce request schemas
- Session state transitions correctly through API calls
- Error responses include clear messages

**Prohibited:**
- Do NOT allow POST without valid session_id
- Do NOT skip state validation
- Do NOT create project before consent_accepted

---

### Step 7: UI Templates

**Objective:** Create HTMX-driven wizard interface

**Actions:**
7.1. Create directory: app/web/templates/concierge/
7.2. Create directory: app/web/templates/concierge/partials/
7.3. Create templates for phases A-F
7.4. Implement HTMX integration for phase transitions
7.5. Apply Tailwind styling with dark mode support

**Verification:**
- Navigate to /start, see orientation phase
- Submit intent, see reflection confirmation
- Answer questions, progress through phases
- Consent creates project, redirects to project view

**Prohibited:**
- Do NOT implement chat-style scrolling interface
- Do NOT use WebSockets (HTMX polling if needed)
- Do NOT skip consent gate visually


### Step 8: Modify Project Discovery Handler

**Objective:** Accept discovery_profile and handoff_context

**Actions:**
8.1. Modify: app/domain/handlers/project_discovery_handler.py
8.2. Update method signature to accept discovery_profile and handoff_context
8.3. Implement profile-based question pack loading
8.4. Incorporate handoff_context if provided
8.5. Update all callers of generate()

**Verification:**
- Handler accepts new parameters without error
- Existing callers still work (backward compatible via defaults)
- New Concierge flow passes handoff_context successfully
- Question packs load from JSON, not hardcoded

**Prohibited:**
- Do NOT add discovery_profile to document_types.gating_rules
- Do NOT create new registry for profiles

---

### Step 9: Locate and Replace Old Flow

**Objective:** Find existing "Initialize New Project" and redirect to /start

**Actions:**
9.1. Search for existing flow using ripgrep
9.2. Locate route and template
9.3. Modify GET route to redirect 302 to /start
9.4. Keep POST route for backward compatibility (hide from UI)
9.5. Update navigation/UI to use /start

**Verification:**
- Old URL redirects to new flow
- No UI elements directly call old POST endpoint
- New users only see Concierge flow

**Prohibited:**
- Do NOT delete old POST route immediately (may have dependencies)
- Do NOT leave parallel intake UX visible to users

---

### Step 10: Integration Tests

**Objective:** Verify end-to-end flow and contract compliance

**Actions:**
10.1. Create test file: tests/test_concierge_integration.py
10.2. Test state machine transitions, event ordering, handoff validation
10.3. Test LLM integration with mocks
10.4. Test question pack loading

**Verification:**
- All tests pass: pytest tests/test_concierge_integration.py -v
- Coverage >= 80% for concierge_service.py

**Prohibited:**
- Do NOT test UI rendering (manual QA acceptable for v1)
- Do NOT mock database (use real PostgreSQL test DB)

---

## 6. Verification Checklist

After all steps complete, verify:

- [ ] User navigating to /start sees orientation phase
- [ ] User submits intent, receives reflection confirmation
- [ ] User answers <= 4 clarifying questions
- [ ] Consent gate requires explicit button click
- [ ] Project + Discovery created after consent
- [ ] No project created if user abandons pre-consent
- [ ] All events stored in concierge_intake_event table
- [ ] Handoff contract validates against schema
- [ ] LLM calls logged in llm_execution_logs table
- [ ] Old "Initialize New Project" redirects to /start
- [ ] Tests pass: pytest tests/test_concierge_integration.py -v

---

## 7. Prohibited Actions

**Do NOT:**
- Create anonymous session support (auth required in v1)
- Implement session cleanup job (enforce expiry on read only)
- Generate questions dynamically with LLM (use JSON packs)
- Add discovery_profile to document_types.gating_rules (not yet)
- Create new registry service for profiles (static JSON only)
- Allow state transitions violating contract section 6.2
- Create project or document before consent_accepted
- Skip consent gate in any code path
- Modify question pack JSON after loading (read-only)
- Allow more than 4 clarifying questions per session

---

## 8. Open Questions / Escalation Points

**None identified.** All decisions made in contract review session.

If ambiguity arises:
- STOP execution at current step
- Document specific ambiguity
- Escalate to Tom for decision

---

## 9. Success Criteria

This work statement is complete when:

1. User can navigate to /start and complete full intake flow
2. Project + Discovery created only after explicit consent
3. All interactions stored as auditable events
4. Handoff contract validates against schema
5. Old flow redirects to new flow
6. Tests pass (state machine, events, handoff, integration)
7. Tom can QA the flow end-to-end without errors

---

## 10. Commit Strategy

**Single commit** expected (per "single-commit" scope).

Commit message:
`
feat: Implement Concierge Project Ingestion (WS-CONCIERGE-001)

- Add concierge_intake_session and concierge_intake_event tables
- Implement ConciergeService with state machine and LLM reflection
- Create data-driven question packs (JSON)
- Add /start and /concierge/* API routes
- Build HTMX-driven wizard UI (phases A-F)
- Modify ProjectDiscoveryHandler to accept discovery_profile
- Redirect old "Initialize New Project" flow to /start
- Add integration tests for state machine and handoff validation

Implements: CONCIERGE_PROJECT_INGESTION_CONTRACT v1.0
Related: ADR-025, ADR-026
`

---

**End of Work Statement**
