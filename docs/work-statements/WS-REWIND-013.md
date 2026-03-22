# WS-REWIND-013 — QA Rejection of Stale Artifacts

**Status:** Draft
**Parent WP:** WP-REWIND-003
**Governing ADR:** ADR-063

## Objective

Explicitly fail QA evaluation and promotion when input artifacts are stale, per ADR-063 Section 13.5.

## Scope

### In Scope
- QA gate checks document status before evaluation
- QA rejects stale inputs with deterministic error
- Promotion endpoints check document status
- Error response includes: artifact ID, current status, reason for rejection

### Out of Scope
- QA logic changes (only adding status check)
- UI error display (WS-REWIND-015)

## Procedure

### Step 1: Add status check to QA gate
- In QA node execution (app/domain/workflow/nodes/qa.py), before running evaluation:
  - Check that the document being evaluated has status == 'current'
  - If not, return QA failure with reason: "artifact invalidated due to upstream rewind"

### Step 2: Add status check to promotion
- In promotion endpoints, verify source document is current before allowing promotion
- Return 400 with structured error if document is stale or superseded

### Step 3: Structured error response
- Error includes: document_id, document_type, current_status, rejection_reason
- Consistent format across QA and promotion checks

### Step 4: Write tests
- Test: QA passes when document is current
- Test: QA rejects when document is stale
- Test: QA rejects when document is superseded
- Test: promotion rejects stale document
- Test: error response includes all required fields

## Verification Criteria
- QA gate rejects stale artifact inputs
- Promotion rejects stale artifact inputs
- Error messages are structured and include document identity
- No stale artifact can pass QA or be promoted
- Tests pass

## Allowed Paths
- app/domain/workflow/nodes/qa.py
- app/api/v1/routers/ (promotion endpoints)
- tests/tier1/test_qa_stale_rejection.py

## Prohibited Actions
- Do not modify QA evaluation logic (only add pre-check)
- Do not automatically fix stale status
- Do not silently skip stale documents
