# GOV-SEC-T0-002 -- Tier-0 Secrets Handling and Ingress Control Policy

**Status:** Active
**Scope:** All HTTP ingress, PGC workflow nodes, stabilization, rendering, and logging subsystems

---

## 1. Purpose

This policy establishes deterministic, multi-layer controls designed to prevent persistence of credential material within The Combine.

The system is designed to:

- Prevent secret solicitation
- Detect secret ingress
- Block workflow execution
- Redact prior to persistence
- Audit detection events

No claim of infallibility is made.

---

## 2. Definitions

### 2.1 Secret

A Secret is any value that:

- Grants authentication or authorization
- Enables service/API access
- Is intended for storage in a secret manager
- Contains credential material within structured formats

Examples (non-exhaustive):

- API keys
- Passwords
- OAuth tokens
- Bearer tokens
- Private keys
- Access key pairs
- Credential-bearing connection strings

Allowed metadata:

- Secret provider
- Secret identifier/path
- Secret name
- Storage mechanism

Secret metadata is permitted. Secret values are not.

---

## 3. Tier-0 Rules

### 3.1 Prohibited

The system MUST NOT:

- Request secret values
- Persist secret values
- Render secret values into HTML or PDF
- Store secret values in logs
- Store secret values in workflow artifacts

### 3.2 Permitted

PGC may request only:

- Whether a secret is required
- Which provider will manage it
- The identifier/path
- Lifecycle ownership
- Runtime resolution intent

All secret-related questions must concern management intent only.

---

## 4. Detection and Enforcement Model

### 4.1 Dual Gate Architecture (Mandatory)

Secrets screening shall occur at:

1. **HTTP Ingress Boundary**
2. **Orchestrator Tier-0 Governance Boundary**

Both gates must invoke the same canonical detector implementation.

---

## 5. Canonical Secret Detector

There shall be one authoritative detector module:

`combine-config/governance/secrets/detector.v1`

This module must be versioned and auditable.

### 5.1 Detection Hierarchy

**Primary trigger:**

- High entropy string detection (threshold >= configured value)
- Minimum length threshold
- Character distribution analysis

**Secondary accelerators:**

- Known credential patterns (AWS AKIA, PEM headers, etc.)

No vendor-enumeration reliance.

---

## 6. HTTP Ingress Gate

### 6.1 Execution

At HTTP ingress:

- Run canonical detector on raw request body
- Execute before any logging persistence

### 6.2 If Secret Detected

System must:

- Reject request (HTTP 422)
- Not create workflow instance
- Not persist request body
- Log only redacted event: `[REDACTED_SECRET_DETECTED]`

Permitted log metadata:

- Request ID
- Detector version
- Entropy score
- Detection classification

Secret value must never be written.

---

## 7. Orchestrator Tier-0 Gate

### 7.1 Execution Points

Detector must run on:

- PGC user answers
- Generated artifacts before stabilization
- Render inputs (detail_html, pdf)
- Replay or connector payloads

### 7.2 If Secret Detected

System must:

- Issue HARD_STOP
- Abort node execution
- Roll back transaction
- Prevent persistence
- Emit structured governance event
- Allow resumable correction

---

## 8. HARD_STOP Definition

HARD_STOP results in:

- Immediate termination of current workflow node
- Transaction rollback
- No stabilization
- No rendering
- No artifact persistence
- Redacted logging only
- Structured error response
- No human intervention required

---

## 9. Logging Precedence (ADR-010 Alignment)

If a conflict exists between logging requirements and secret protection:

**Tier-0 Secret Protection takes precedence.**

Secret-bearing payloads must be redacted prior to persistence.

Logging may record:

- Detection metadata
- Governance event
- Redacted placeholder

Logging may not store secret material.

---

## 10. Tier-0 Injection Requirement (PGC)

All PGC task and QA prompts must include the injected clause defined in Section 11.

Clause must be injected automatically and be non-removable.

---

## 11. Canonical Injected Clauses

Location:

- `combine-config/governance/tier0/pgc_secrets_clause.v1.txt`
- `combine-config/governance/tier0/pgc_secrets_clause_qa.v1.txt`

### 11.1 PGC Task Clause (Exact Text)

```
[[TIER0_PGC_SECRETS_CLAUSE_V1]]

Tier-0 Governance Rule: Secrets Handling

You MUST NOT request, collect, validate, echo, or persist any credential or secret value.

A secret includes (but is not limited to):
- API keys
- Passwords
- OAuth tokens
- Bearer tokens
- Private keys
- Access key pairs
- Credential-bearing connection strings

You MAY ask how secrets should be managed, including:
- Whether a secret is required
- Which provider will manage it
- The secret identifier or storage path
- Whether runtime resolution should occur

All secret-related questions must concern management intent only.

If a user provides a secret value:
- Do not repeat it
- Do not store it
- Instruct the user to use a supported secret manager
- Continue safely without persisting the value
```

### 11.2 PGC QA Clause (Exact Text)

```
[[TIER0_PGC_SECRETS_CLAUSE_V1]]

Tier-0 Governance Rule: Secrets Validation

You MUST verify that:
- No PGC question requests a secret value
- No artifact contains credential material
- No secret fragments appear in output

If secret solicitation is detected:
- Mark as HARD_STOP violation
- Explain violation clearly

If secret material appears in user input:
- Mark as invalid
- Require use of secret manager
```

---

## 12. Authority

This policy:

- Cannot be overridden by package.yaml
- Cannot be modified via Workbench triad editing
- Is governed as Tier-0 Combine infrastructure

---

_End of GOV-SEC-T0-002_
