# CLAUDE.md Bootstrap - The Combine

## Purpose

The Combine is a document-centric Industrial AI system that applies manufacturing principles to knowledge work. It uses specialized AI stations (PM, BA, Developer, QA, Technical Architect) with explicit quality gates, document-based state management, and systematic validation to produce high-quality artifacts.

This file is the **primary entry point for AI collaborators**.

---

## Project Root

**Filesystem path:** `C:\Dev\The Combine\`

All relative paths in this document are from this root. When using tools to read files:
- `docs/PROJECT_STATE.md` -> `C:\Dev\The Combine\docs\PROJECT_STATE.md`
- `docs/session_logs/` -> `C:\Dev\The Combine\docs\session_logs\`
- `app/` -> `C:\Dev\The Combine\app\`

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

1. **Follow Work Statements exactly**: Execute steps in order; do not skip, reorder, or merge
2. **Stop on ambiguity**: If a step is unclear, STOP and escalate rather than infer
3. **Respect prohibited actions**: Each Work Statement defines what is NOT permitted
4. **Verify before proceeding**: Complete verification for each step before moving to the next

---

## Execution Constraints (Read First)

The following constraints apply to all work on this project:

- **All file-writing commands MUST be provided or performed in PowerShell syntax.**
  - Do not use bash, sh, or Unix-style commands.
  - Do not assume a Unix-like environment.
  
- **HTML Encoding Compliance Check (Mandatory)**
  - Before recognizing any HTML file as ready for delivery, verify:
    1. No BOM (Byte Order Mark) at file start
    2. No non-ASCII characters (all chars must be 0x00-0x7F)
    3. No corrupted UTF-8 sequences (e.g., multi-byte chars displaying as garbage)
  - If issues found, fix by stripping non-ASCII and writing with UTF8 no-BOM encoding
  - Batch fix script available at: ops/scripts/fix_html_encoding.ps1

- **The human operator executes all tests.**
  - Do NOT run tests automatically.
  - Do NOT simulate test execution.
  - When tests are needed, provide instructions only.

- **The human operator performs Git Operations**
  - The AI MUST NOT perform Git commits.
  - The AI MAY propose commit messages and describe what should be committed.
  - The user performs all Git commits.

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

## Governing ADRs (Active)

| ADR | Status | Summary |
|-----|--------|---------|
| ADR-009 |  Complete | Project Audit - all state changes explicit and traceable |
| ADR-010 |  Complete | LLM Execution Logging - inputs, outputs, replay capability |
| ADR-011 |  In Progress | Project/Epic organization (draft exists) |

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

```powershell
# Run locally
.\run.ps1

# Run tests
python -m pytest tests/ -v

# Update Route53 after deploy
.\ops\aws\fixip.ps1

# Regenerate seed manifest
# (script TBD - currently manual)
```

---

_Last reviewed: 2026-01-06_