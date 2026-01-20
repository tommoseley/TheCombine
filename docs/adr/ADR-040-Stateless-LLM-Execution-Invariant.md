# ADR-040 - Stateless LLM Execution Invariant

**Status:** Accepted
**Date:** 2026-01-17
**Decision Type:** Architectural / Governance
**Supersedes:** None

**Related ADRs:**
- ADR-010 - LLM Execution Logging (Complete)
- ADR-035 - Durable LLM Threaded Queue (Draft)
- ADR-039 - Document Interaction Workflow Model (Accepted)

---

## Context

The Combine uses LLMs to generate documents, conduct intake conversations, and perform quality assurance. Early implementations followed chat-like patterns where conversation history was accumulated and replayed to the LLM on each turn.

On 2026-01-17, a production bug was discovered where the workflow engine loaded conversation history from a thread ledger and passed it to the LLM. This caused **context contamination**: old conversations from previous sessions polluted new workflow executions, causing the LLM to "remember" information it should not have known.

The contamination manifested as:
- The Concierge providing information not present in its governed prompt
- Cross-session bleed where user A's context appeared in user B's session
- The LLM confabulating explanations for knowledge it claimed came from its "system prompt"

Initial analysis suggested disabling all conversation history loading. However, this was too crude — multi-turn intake requires *some* continuity. The deeper insight is:

**Raw transcripts carry contamination even within the same execution** — tone leakage, accidental capability claims, "as I said earlier" references, and role confusion. Replaying transcripts means debugging drift forever.

The correct solution: **Continuity comes from structured state, not transcripts.**

---

## Decision

**All LLM execution in The Combine MUST be stateless with respect to conversation transcripts.**

**Continuity MUST be expressed as structured context state, not raw conversation history.**

Each LLM invocation receives:
1. The canonical role prompt (if applicable)
2. The task- or node-specific prompt
3. The current user input (single turn only)
4. **Structured context state** (governed data derived from prior turns)

Each LLM invocation does NOT receive:
- Prior conversation history (even from same execution)
- Previous assistant responses
- Accumulated user messages
- Raw conversational transcripts

---

## Architectural Invariants

### 1. No Transcript Replay

The LLM never receives prior conversation turns. This applies:
- ❌ Across different executions (cross-session)
- ❌ Within the same execution (same-session)

**MUST NOT:**
- Send `conversation_history` arrays to LLMs
- Replay assistant messages from prior turns
- Rebuild conversation from `node_history.metadata`

**MUST:**
- Construct each prompt with only current-turn user input
- Provide continuity via structured `context_state`

### 2. Context State Is Memory

Workflows that require continuity (e.g., multi-turn intake) use a **context_state** object:

```json
{
  "intake_summary": "User wants to build a mobile app for...",
  "known_constraints": ["must use React Native", "3 month timeline"],
  "open_gaps": ["target users unclear", "budget not discussed"],
  "questions_asked": ["initial_intent", "platform_preference"],
  "answers": {
    "initial_intent": "mobile app for tracking...",
    "platform_preference": "cross-platform"
  },
  "ready_to_proceed": false
}
```

This is:
- Structured, not prose
- Governed (schema-validatable)
- Deterministic (same state → same behavior)
- Auditable (state transitions are explicit)

### 3. Node History Is Audit, Not Memory

`DocumentWorkflowState.node_history` stores execution records for audit:
- `user_input_hash` or `user_input_preview`
- `assistant_output_hash`
- `outcome`, `timing`, `model_ids`

Node history is **NOT** used for rehydrating LLM context. It exists for:
- ADR-010 compliant audit trails
- Debugging and replay analysis
- User-facing conversation display

### 4. Transcripts Are Write-Only

Conversation transcripts MAY be stored for:
- Audit (ADR-010)
- User review
- QA analysis

Conversation transcripts MUST NOT be:
- Loaded and passed to LLMs
- Used to reconstruct state
- Treated as input to any LLM invocation

---

## Implementation

### DocumentWorkflowState

Add field:

```python
context_state: Dict[str, Any] = field(default_factory=dict)
```

### Execution Loop

After every node execution:
1. Node returns `NodeResult` with optional `context_state_delta`
2. Merge `context_state_delta` into `state.context_state`
3. Persist state

### _build_context()

```python
return DocumentWorkflowContext(
    document_id=state.document_id,
    document_type=state.document_type,
    context_state=state.context_state,  # <-- structured memory
    conversation_history=[],             # <-- always empty
    extra=extra,
)
```

### Concierge Prompt

The Concierge prompt consumes `context_state` explicitly:

```
## Known Facts
{{context_state.intake_summary}}

## Constraints Established
{{context_state.known_constraints}}

## Open Gaps (do not re-ask)
{{context_state.open_gaps}}

## Questions Already Asked
{{context_state.questions_asked}}
```

This gives the Concierge continuity without transcript replay.

---

## Consequences

### Positive

- **Isolation**: No cross-session or within-session transcript bleed
- **Predictability**: Same context_state → same LLM behavior
- **Auditability**: State transitions are explicit and inspectable
- **Governance**: context_state can be schema-validated
- **No drift**: No "as I said earlier" or accidental capability claims

### Negative

- **Design effort**: Concierge must be designed to produce/consume context_state
- **Prompt complexity**: Prompts must explicitly render context_state
- **State management**: context_state_delta must be carefully defined

### Neutral

- Thread infrastructure remains useful for audit and UI
- Existing logging (ADR-010) is unaffected
- node_history continues to serve audit purposes

---

## Compliance

### Detection

If you see any of the following, STOP and raise a violation:
- `conversation_history` being populated from any source
- Arrays of `{"role": "user/assistant", "content": ...}` being built
- `load_conversation_history()` being called
- `node_history` being used to reconstruct conversation for LLM input

### Correct Pattern

```python
# CORRECT: Structured state
context_state = state.context_state
prompt = f"Known facts: {context_state.get('intake_summary', 'None yet')}"

# WRONG: Transcript replay
for msg in state.node_history:
    messages.append({"role": msg.role, "content": msg.content})
```

---

## References

- Session Log 2026-01-17: Original bug discovery and architectural refinement
- ADR-010: LLM Execution Logging (audit infrastructure)
- ADR-035: Durable LLM Threaded Queue (thread design)
- ADR-039: Document Interaction Workflow Model (workflow execution)

---

## Changelog

| Date | Change |
|------|--------|
| 2026-01-17 | ADR created following production contamination bug |
| 2026-01-17 | Refined: structured context_state, not just "no history" |
