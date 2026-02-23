# CLAUDE.md Bootstrap - The Combine

## Purpose

The Combine is a document-centric Industrial AI system that applies manufacturing principles to knowledge work. It uses specialized AI stations (PM, BA, Developer, QA, Technical Architect) with explicit quality gates, document-based state management, and systematic validation to produce high-quality artifacts.

This file is the **primary entry point for AI collaborators**.

---

## Project Root

**Filesystem path:** `~/dev/TheCombine/` (Linux/WSL)

All relative paths in this document are from this root. When using tools to read files:
- `docs/PROJECT_STATE.md` -> `~/dev/TheCombine/docs/PROJECT_STATE.md`
- `docs/session_logs/` -> `~/dev/TheCombine/docs/session_logs/`
- `app/` -> `~/dev/TheCombine/app/`

---

## Read Order

1. This file (`CLAUDE.md`) - in Project Knowledge
2. **Use the `view` tool** to read `docs/PROJECT_STATE.md` from the filesystem
3. **Review all policies** in `docs/policies/` - these are mandatory governance constraints
4. Optionally scan recent session logs in `docs/session_logs/` (filesystem)
5. Search Project Knowledge for ADRs as needed

**Important:** `PROJECT_STATE.md` and session logs live on the filesystem, not in Project Knowledge. Use tools to read them.

---

## Governing Policies (Mandatory)

The following policies are mandatory governance constraints. AI agents MUST read and comply with these policies.

| Policy | Purpose | Key Requirements |
|--------|---------|------------------|
| POL-WS-001 | Work Statement Standard | Defines structure and execution rules for all implementation work |
| POL-ADR-EXEC-001 | ADR Execution Authorization | 6-step process from ADR acceptance to execution |

### POL-ADR-EXEC-001 Bootstrap Requirements

Per POL-ADR-EXEC-001, AI agents MUST:

1. **Recognize ADR states**: Architectural status (Draft/Accepted/Deprecated/Superseded) is independent of execution state (null/authorized/active/complete)
2. **Assess scope**: Determine if work is single-commit or multi-commit
3. **Follow the appropriate path**:
   - **Single-commit:** Work Statement -> Acceptance -> Execute
   - **Multi-commit:** Implementation Plan -> Acceptance -> Work Statement(s) -> Acceptance -> Execute
4. **Declare scope explicitly**: The expected scope MUST be stated in the Work Statement or Implementation Plan
5. **Escalate if scope grows**: If single-commit work expands, STOP and draft an Implementation Plan
6. **Refuse unauthorized execution**: Do NOT begin execution without explicit Work Statement acceptance

**Key principle:** ADR acceptance does NOT authorize execution. Execution requires completing the appropriate authorization path.

### POL-WS-001 Bootstrap Requirements

Per POL-WS-001, AI agents MUST:

1. **Do No Harm audit first**: Before executing any WS, verify its assumptions about the codebase match reality. If assumptions are materially wrong, STOP and report mismatches before touching anything.
2. **Follow Work Statements exactly**: Execute steps in order; do not skip, reorder, or merge
3. **Stop on ambiguity**: If a step is unclear, STOP and escalate rather than infer
4. **Respect prohibited actions**: Each Work Statement defines what is NOT permitted
5. **Verify before proceeding**: Complete verification for each step before moving to the next

---

## Execution Constraints (Read First)

The following constraints apply to all work on this project:


- **HTML Encoding Compliance Check (Mandatory)**
  - Before recognizing any HTML file as ready for delivery, verify:
    1. No BOM (Byte Order Mark) at file start
    2. No non-ASCII characters (all chars must be 0x00-0x7F)
    3. No corrupted UTF-8 sequences (e.g., multi-byte chars displaying as garbage)
  - If issues found, fix by stripping non-ASCII and writing with UTF8 no-BOM encoding
  - Batch fix script available at: ops/scripts/fix_html_encoding.ps1

- **Regarding File not found errors**
  - You may encounter File not found errors for files that do in fact exist.
  - The human operator uses VS Code, which may hold file locks or have unsaved buffers that interfere with file access.
  - If a file access error occurs on a file that should exist, pause and ask Tom to close the file in VS Code, then retry the operation.

- **Reuse-First Rule**

  -Before creating anything new (file, module, schema, service, prompt):
    - Search the codebase and existing docs/ADRs.
    - Prefer extending or refactoring over creating.
    - Only create something new when reuse is not viable.

  -If you create something new, you must be able to justify why reuse was not appropriate.
  -Creating something new when a suitable existing artifact existed is a defect.

- **Stateless LLM Execution Invariant (ADR-040)**

  IMPORTANT: The Combine is NOT a chat system.

  When developing or modifying The Combine, you MUST treat all LLM execution as stateless with respect to conversation transcripts.

  **No transcript replay — even within the same execution.**

  Raw transcripts carry contamination: tone leakage, accidental capability claims, "as I said earlier" references, role confusion. Replaying transcripts means debugging drift forever.

  Each LLM invocation MUST receive:
  - The canonical role prompt
  - The task- or node-specific prompt
  - The current user input (single turn only)
  - **Structured context_state** (governed data derived from prior turns)

  Each LLM invocation MUST NOT receive:
  - Prior conversation history (even from same execution)
  - Previous assistant responses
  - Accumulated user messages
  - Raw conversational transcripts

  **Continuity comes from structured state, not transcripts.**

  If continuity is required, use `context_state` with structured fields:
  - `intake_summary`, `known_constraints[]`, `open_gaps[]`
  - `questions_asked[]` (IDs, not prose), `answers{}`
  - Never raw conversation text

  **node_history is for audit. context_state is for memory. Keep them separate.**

  **If you are about to load or replay conversation history, STOP — this is a violation.**

  _See ADR-040 and session log 2026-01-17._

- **No Black Boxes (ADR-049)**

  Every DCW (Document Creation Workflow) MUST be explicitly composed of gates, passes, and mechanical operations.

  **"Generate" is deprecated as a step abstraction — it hides too much.**

  DCWs are first-class workflows, not opaque steps inside POWs. If a step does something non-trivial, it must show its passes.

  Composition patterns:
  - **Full pattern**: PGC Gate (LLM → UI → MECH) → Generation (LLM) → QA Gate (LLM + remediation)
  - **QA-only pattern**: Generation (LLM) → QA Gate (LLM + remediation)
  - **Gate Profile pattern**: Multi-pass classification with internals

  **If you are about to create a DCW with opaque "Generate" steps, STOP — decompose into explicit gates.**

  _See ADR-049._

Violation of these constraints is considered a failure to follow project rules.

---

## Knowledge Layers

| Layer | Purpose | Location | Mutability |
|-------|---------|----------|------------|
| ADRs | Why decisions were made | Project Knowledge + `docs/adr/` | Append-only |
| Git history | What changed (code) | `.git` | Immutable |
| PROJECT_STATE.md | Current status snapshot | `docs/` (filesystem) | Updated per session |
| Session Summaries | How we got here | `docs/session_logs/` (filesystem) | Immutable after write |

These layers do not compete. Each serves a distinct purpose.

---

## Repository Structure

```
app/                    # Runtime application code (always deployed)
  api/                  # FastAPI routers, services, models
  auth/                 # Authentication (OAuth, session management)
  core/                 # Configuration, database, shared utilities
  domain/               # Domain models, repositories, services
  web/                  # Web UI routes, templates, BFF layer
  llm/                  # LLM client and integration
  tasks/                # Background task infrastructure

alembic/                # Database migrations
  versions/             # Migration scripts

seed/                   # Governed inputs (optionally deployed)
  prompts/              # Role and task prompts (versioned, certified)
  question_packs/       # Concierge question templates
  reference_data/       # Static reference data
  schemas/              # JSON schemas for validation
  workflows/            # Workflow definitions

ops/                    # Operator tooling (never in runtime image)
  aws/                  # ECS, Route53, IAM scripts
  db/                   # Database seed/setup scripts
  scripts/              # Dev/debug utilities (including fix_html_encoding.ps1)
  testing/              # Test infrastructure scripts

docs/                   # Human documentation
  adr/                  # Architecture Decision Records
  policies/             # Governance policies (POL-*)
  work-statements/      # Work Statement documents (WS-*)
  implementation-plans/ # Multi-commit implementation plans
  session_logs/         # AI session summaries (YYYY-MM-DD.md)
  governance/           # Governance documentation
  archive/              # Superseded/historical docs
  project/              # Project-level documentation

tests/                  # Test suite (CI only)
  tier1/                # In-memory, no DB (fast unit tests)
  tier2/                # Spy repositories (wiring tests)
  unit/                 # Additional unit tests
  integration/          # Integration tests
  e2e/                  # End-to-end tests
  fixtures/             # Test fixtures and data

data/                   # Runtime data (gitignored)
  workflow_state/       # Workflow execution state

recycle/                # Deprecated code pending deletion
```

Key implications:
- Prompts live in `seed/prompts/` - they are **governed inputs**, not documentation
- Anything in `ops/` is operator-facing and never in the container
- Docker copies only `app/`, `alembic/`, `alembic.ini` (explicit, not blanket)
- ADRs go in `docs/adr/`, policies in `docs/policies/`, work statements in `docs/work-statements/`
- Session logs go in `docs/session_logs/` with format `YYYY-MM-DD.md`

---

## Deployment Reality (Current)

- **Compute**: AWS ECS Fargate (cluster: `the-combine-cluster`)
- **Networking**: Route 53 A record -> direct task public IP (no ALB)
- **DNS**: `thecombine.ai` (port 8000, HTTP only)
- **IP changes**: Handled via `ops/aws/fixip.ps1` after redeployment
- **CI/CD**: GitHub Actions -> ECR -> ECS task definition update -> Route 53 update
- **Secrets**: Anthropic API key in AWS Secrets Manager, injected at runtime
- **Database**: RDS PostgreSQL (publicly accessible for dev)

No blue/green. No canary. IP changes on every deploy.

---

## Testing Strategy (Current)

- **Tier-1**: In-memory repositories, no DB, pure business logic verification
- **Tier-2**: Spy repositories for call contract verification (wiring tests)
- **Tier-3**: Real PostgreSQL - **deferred** (requires test DB infrastructure)

Tier-3 tests are not currently required. Do not suggest SQLite as a substitute.

---

## Execution Model (Concrete)

All work operates on **documents**. The flow:

1. Document type configuration defines inputs, handler, role/task
2. Handler assembles inputs from dependent documents
3. Role prompt + Task prompt loaded from certified seed
4. LLM execution logged per ADR-010 (inputs, outputs, tokens, timing)
5. Handler parses response, persists document
6. Output is replayable via `/api/admin/llm-runs/{id}/replay`

Handlers:
- Own input assembly, prompt selection, LLM invocation, output persistence
- Do **not** infer missing inputs - they fail explicitly

---

## Seed Governance

`seed/` contains governed inputs. Prompts are:
- **Versioned** (filename includes version)
- **Certified** (auditor prompts validate structure)
- **Hashed** (`seed/manifest.json` contains SHA-256 checksums)
- **Logged** (prompt content recorded on every LLM execution per ADR-010)

Prompts are **not edited casually**. Changes require:
1. Explicit intent
2. Version bump
3. Re-certification
4. Manifest regeneration

---

## Bug-First Testing Rule (Mandatory)

When a runtime error, exception, or incorrect behavior is observed, the following sequence **MUST** be followed:

1. **Reproduce First**  
   A failing automated test **MUST** be written that reproduces the observed behavior.  
   The test must fail for the same reason the runtime behavior failed.

2. **Verify Failure**  
   The test **MUST** be executed and verified to fail before any code changes are made.

3. **Fix the Code**  
   Only after the failure is verified may code be modified to correct the issue.

4. **Verify Resolution**  
   The test **MUST** pass after the fix.  
   No fix is considered complete unless the reproducing test passes.

### Constraints

- Tests **MUST NOT** be written after the fix to prove correctness.
- Code **MUST NOT** be changed before a reproducing test exists.
- If a bug cannot be reliably reproduced in a test, the issue **MUST** be escalated rather than patched heuristically.

### Rationale

This rule ensures:

- The defect is understood before modification
- Fixes are causally linked to observed failures
- Regressions are prevented by construction
- Vibe-based fixes are explicitly disallowed

This rule is **non-negotiable** and applies to all runtime defects, including:

- Exceptions  
- Incorrect outputs  
- State corruption  
- Boundary condition failures

---


## Autonomous Bug Fixing

When a runtime error or incorrect behavior is encountered during WS execution:

- **Do not stop and ask for instructions.** Fix it.
- Follow the Bug-First Testing Rule (see above) autonomously — the same reproduce-first sequence applies.
- **Report what you fixed, not what you found.** Include the test name and root cause.

Escalate only when:

- The bug cannot be reproduced in a test
- The fix would require changes outside the WS `allowed_paths`
- The fix would violate a WS prohibition
- The root cause is ambiguous and multiple fixes are plausible

If the fix is non-trivial (architectural impact, touches multiple modules), write a remediation WS (see WS-DCW-003-RS001 for the pattern) and present it for acceptance before executing.

---

## Subagent Usage

Use subagents to parallelize work and keep the main context window clean.

### Parallel WS Execution

When a Work Package defines multiple independent Work Statements:

- Read the WP dependency chain to determine what can parallelize
- If two WSs have no dependency relationship AND non-overlapping `allowed_paths`, they are safe to run in parallel
- Spawn one subagent per independent WS
- **Mandatory:** Use `isolation: "worktree"` for parallel WS subagents to prevent git conflicts and silent overwrites

**Subagent responsibilities:**
- Run Do No Harm audit for its WS
- Execute all phases (failing tests -> implement -> verify)
- Report results (pass/fail, tests written, files changed, issues found)
- Do NOT modify files outside its WS `allowed_paths`

**Main agent responsibilities:**
- Determine parallelism from WP dependency chain
- Spawn subagents for independent WSs
- Wait for completion before spawning dependent WSs
- Run Tier 0 after all WSs complete
- Aggregate and report results

### Other Subagent Uses

Also use subagents for:

- **Research tasks**: Reading multiple files to assess impact before a Do No Harm audit
- **Parallel grep/audit**: Searching across different directory trees simultaneously
- **Test isolation**: Running different test suites in parallel
- **Impact analysis**: Assessing what a proposed change would affect

One task per subagent. Keep them focused.

---

## Metrics Reporting

The factory measures its own production line. Claude Code MUST report execution metrics at phase boundaries during WS execution.

### What to Report

**At WS start:**
- WS ID, start timestamp, parent WP ID

**At each phase boundary (tests written / implement / verify):**
- Phase name, duration, pass/fail
- Tests written count (for test phases)
- Files modified count (for implement phases)

**At WS completion:**
- Total duration (wall clock)
- Tests written, tests passing
- Bugs found and fixed autonomously (with test names)
- Files created / modified / deleted
- Rework cycles (how many times verification bounced back to implementation)
- LLM calls made, tokens consumed (input/output)

**On autonomous bug fix:**
- Bug description (one line)
- Root cause (one line)
- Test name
- Fix summary

### How to Report

POST metrics to the developer metrics endpoints when available:

```
POST /api/v1/metrics/ws-execution
POST /api/v1/metrics/bug-fix
```

If endpoints are not yet available, append metrics to the session log in a structured format:

```
## Execution Metrics - WS-DCW-001
- Duration: 23m 14s
- Tests written: 8
- Tests passing: 8/8
- Bugs fixed: 1 (empty initial_context in project_orchestrator)
- Files modified: 3
- Rework cycles: 0
- LLM calls: 12
- Tokens: 45,200 in / 18,400 out
```

### Why This Matters

These metrics feed:
- Quality dashboards for the operator
- Cost analysis per document type
- Continuous improvement (which WSs take longest, which have most rework)
- Customer-facing evidence that the factory works

---

## Planning Discipline

### Plan Before Executing

For any non-trivial task (3+ steps or architectural decisions):

- Enter plan mode before writing code
- Write the plan as a WS or remediation WS if one does not already exist
- Get acceptance before executing

If something goes wrong during execution, **STOP and re-plan**. Do not push through a failing approach. Re-planning means escalating to Tom, not silently changing strategy.

### Simplicity First

- Make every change as simple as possible
- Find root causes, not symptoms
- No temporary fixes. No "we'll clean this up later" without a tech debt entry.
- Changes should only touch what is necessary
- If a fix feels hacky, pause and find the elegant solution

### Verification Before Done

- Never mark a task complete without proving it works
- Run tests, check logs, demonstrate correctness
- The question is not "does this look right?" but "does Tier 0 pass?"

---
## Governing ADRs (Active)

| ADR | Status | Summary |
|-----|--------|---------|
| ADR-009 |  Complete | Project Audit - all state changes explicit and traceable |
| ADR-010 |  Complete | LLM Execution Logging - inputs, outputs, replay capability |
| ADR-011 |  In Progress | Project/Epic organization (draft exists) |
| ADR-045 |  Accepted | System Ontology - Primitives (Prompt Fragment, Schema), Composites (Role, Task, DCW, POW), Configuration Taxonomy |

### ADR-045 Taxonomy Reference

**Primitives** (authorable and governable in isolation):
- **Prompt Fragment**: Shapes behavior (role prompts, task prompts, QA prompts, PGC context)
- **Schema**: Defines acceptability (JSON Schema for output validation)

**Ontological term** (vocabulary, not configuration):
- **Interaction Pass**: Names what a DCW node is -- the binding of prompt fragments + schema at execution time

**Composites** (assemble primitives for a purpose):
- **Role**: Identity + constraints (assembles prompt fragments)
- **Task**: Work unit within a DCW node (prompt fragment + schema reference)
- **DCW** (Document Creation Workflow): Graph of nodes producing one stabilized document
- **POW** (Project Orchestration Workflow): Sequence of steps, each invoking a DCW

**Core principle**: Prompt Fragments shape behavior; Schemas define acceptability; Interaction Passes bind and execute both.

ADR documents live in `docs/adr/` and Project Knowledge. Each has implementation reports.

---

## Project Knowledge vs Filesystem

| Content | Location | Why |
|---------|----------|-----|
| `CLAUDE.md` | Project Knowledge | Stable, immediate context |
| ADRs | Project Knowledge | Reference, searchable |
| `PROJECT_STATE.md` | Filesystem (`docs/`) | Volatile, Claude updates it |
| Session logs | Filesystem (`docs/session_logs/`) | Claude writes these |
| Code | Filesystem (`app/`, etc.) | Claude reads/writes |

**At session start:** Read PROJECT_STATE.md from filesystem using tools.
**At session close:** Update PROJECT_STATE.md and write session log to filesystem.

---



## Non-Negotiables

- Do not merge role logic into task prompts
- Do not invent workflow, ceremony, or process
- Do not assume undocumented context
- Do not suggest SQLite for testing
- Do not edit prompts without version bump
- Session summaries are logs - never edit after writing
- Discipline > convenience

---

## Session Management

### How to Start a New AI Session

Before any work:

1. Read `CLAUDE.md` (this file, in Project Knowledge)
2. **Use tools to read** `docs/PROJECT_STATE.md` from filesystem
3. Scan `docs/session_logs/` for recent context
4. Scan `docs/adr/` for architectural guidance and a future vision
5. Summarize back:
   - System purpose
   - Current state
   - Active constraints (ADRs)
   - Next logical work
6. Ask for confirmation before proceeding

### How to Close a Session

When the user says **"Prepare session close"** (or similar):

1. Write session summary to `docs/session_logs/YYYY-MM-DD.md` (filesystem)
   - Use fixed template (scope, decisions, implemented, commits, open threads, risks)
   - No prose, no reflection - facts only
   - Include git commits/PRs if applicable
2. Update `docs/PROJECT_STATE.md` (filesystem)
   - Current state
   - Handoff notes for next session
3. Pause and ask: **"Ready to close, or do you want to continue?"**

Session summaries are **immutable logs**. They capture "what happened- - not decisions (ADRs) or current state (PROJECT_STATE.md).

If multiple sessions occur on the same day, use suffix: `2026-01-02.md`, `2026-01-02-2.md`

---

## Backfilling Session Logs (For Previous Chats)

Use this prompt in old chat sessions to generate retroactive session logs:

---

**Instruction**

You are writing a Session Summary Log for this conversation.
This log is used to restore context in future AI sessions. Accuracy and restraint are more important than completeness.

**Hard Constraints (Non-Negotiable)**

1. **No Invention**
   - Do NOT infer decisions, implementations, or intent.
   - If something was discussed but not explicitly decided or implemented, it must NOT appear under those sections.

2. **Explicit Uncertainty Handling**
   - If you are unsure whether an item qualifies, omit it.
   - Do NOT hedge or speculate.
   - Absence is preferred over incorrect inclusion.

3. **Factual Tone Only**
   - No reflection, justification, or commentary.
   - No "we learned", "this was important", or similar phrasing.
   - Use short, declarative bullets only.

4. **Scope Discipline**
   - "Decisions Made- = explicit agreements or resolutions.
   - "Implemented- = concrete artifacts created or modified.
   - "Discussed- items belong nowhere unless they resulted in a decision or implementation.

5. **No New Information**
   - Do NOT introduce new risks, interpretations, or connections.
   - Only capture what occurred in this session.

**Output Requirements**

- Use the date of the last interaction in this chat (not today) as `YYYY-MM-DD`
- Output only a single markdown document
- Filename format: `docs/session_logs/YYYY-MM-DD.md`
- Follow the template exactly
- Do not add, remove, or rename sections
- If a section has no valid entries, write `- None`

**Template (Must Be Used Verbatim)**

```
# Session Summary - YYYY-MM-DD

## Scope
- 

## Decisions Made
- 

## Implemented
- 

## Updated or Created
- 

## Commits / PRs
- 

## Open Threads
- 

## Known Risks / Drift Warnings
- 
```

**Final Instruction**

Write the session summary now.
If you cannot confidently populate a section, leave it as `- None`.

---

## Quick Commands

```bash
# Run locally
cd ~/dev/TheCombine && source venv/bin/activate
python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000

# Run tests
python -m pytest tests/ -v

# Tier 0 verification (ADR-050) — mandatory baseline for all work
ops/scripts/tier0.sh                            # pytest + lint + typecheck
ops/scripts/tier0.sh --frontend                 # force SPA build (auto-detects spa/ changes)
ops/scripts/tier0.sh --scope app/ tests/        # also validate file scope

# Tier 0 in WS mode (WS-TIER0-SCOPE-001) — mandatory for Work Statement execution
# After completing a WS, run with --ws and --scope from the WS's allowed_paths[]:
ops/scripts/tier0.sh --ws --scope ops/scripts/ tests/infrastructure/ docs/policies/ CLAUDE.md
# If Tier 0 is run in WS mode without --scope, it will FAIL by design.

# Regenerate seed manifest
# (script TBD - currently manual)
```

---

## Remote DEV/TEST Databases (WP-AWS-DB-001)

DEV and TEST databases run on AWS RDS (`combine-devtest` instance, Postgres 18.1).
Credentials are in AWS Secrets Manager — never hardcoded.

### Connect to DEV

```bash
# Print DATABASE_URL for DEV (retrieves creds from Secrets Manager)
ops/scripts/db_connect.sh dev

# Verify connectivity
ops/scripts/db_connect.sh dev --check

# Open interactive psql session
ops/scripts/db_connect.sh dev --psql

# Run app against DEV
export DATABASE_URL=$(ops/scripts/db_connect.sh dev)
export ENVIRONMENT=dev_aws
python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Connect to TEST

```bash
# Same commands, replace 'dev' with 'test'
ops/scripts/db_connect.sh test
ops/scripts/db_connect.sh test --check
ops/scripts/db_connect.sh test --psql

# Run app against TEST
export DATABASE_URL=$(ops/scripts/db_connect.sh test)
export ENVIRONMENT=test_aws
python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Migrate

```bash
ops/scripts/db_migrate.sh dev          # Migrate DEV (bootstraps if empty)
ops/scripts/db_migrate.sh test         # Migrate TEST
ops/scripts/db_migrate.sh dev --seed   # Migrate + seed DEV
```

### Destructive Actions (Guardrails)

All destructive operations require `CONFIRM_ENV=<target>` to prevent accidents:

```bash
# Reset DEV database (drops all tables, re-bootstraps)
CONFIRM_ENV=dev ops/scripts/db_reset.sh dev

# Reset TEST database
CONFIRM_ENV=test ops/scripts/db_reset.sh test

# Wrong confirmation → blocked
CONFIRM_ENV=test ops/scripts/db_reset.sh dev   # ERROR: mismatch
ops/scripts/db_reset.sh dev                     # ERROR: CONFIRM_ENV required
```

In CI, destructive actions are blocked unless `ALLOW_DESTRUCTIVE_IN_CI=1` is set.

### Connection Recovery

If database connections fail:

1. **Check your IP**: `curl -s https://checkip.amazonaws.com` — if it changed, update the security group
2. **Check RDS status**: `aws rds describe-db-instances --db-instance-identifier combine-devtest --query 'DBInstances[0].DBInstanceStatus'`
3. **Check credentials**: `aws secretsmanager get-secret-value --secret-id the-combine/db-dev --query SecretString --output text` — verify the secret exists and has a DATABASE_URL
4. **Check security group**: `aws ec2 describe-security-groups --group-ids sg-0edb6a93c034f7e38 --query 'SecurityGroups[0].IpPermissions'` — verify your IP is in the ingress rules
5. **Update IP in security group**: Remove old rule, add new one with current IP

---

_Last reviewed: 2026-02-19_

