# AI Bootstrap — The Combine

## Purpose

The Combine is a document-centric Industrial AI system that applies manufacturing principles to knowledge work. It uses specialized AI stations (PM, BA, Developer, QA, Technical Architect) with explicit quality gates, document-based state management, and systematic validation to produce high-quality artifacts.

This file is the **primary entry point for AI collaborators**.

---

## Read Order

1. This file (`AI.md`)
2. `docs/PROJECT_STATE.md`
3. Recent session logs in `docs/session_logs/` (most recent first)
4. Referenced ADRs as needed (in `docs/adr/`)

---

## Knowledge Layers

| Layer | Purpose | Location | Mutability |
|-------|---------|----------|------------|
| ADRs | Why decisions were made | `docs/adr/` | Append-only |
| Git history | What changed (code) | `.git` | Immutable |
| PROJECT_STATE.md | Current status snapshot | `docs/` | Updated per session |
| Session Summaries | How we got here | `docs/session_logs/` | Immutable after write |

These layers do not compete. Each serves a distinct purpose.

---

## Repository Structure (Four Buckets)

```
app/           # Runtime application code (always deployed)
seed/          # Governed inputs: prompts, reference data (optionally deployed)
ops/           # Operator tooling (never in runtime image)
  aws/         # ECS, Route53, IAM scripts
  db/          # Database seed/setup scripts
  scripts/     # Dev/debug utilities
docs/          # Human documentation, ADRs, session logs
tests/         # Test suite (CI only)
```

Key implications:
- Prompts live in `seed/prompts/` — they are **governed inputs**, not documentation
- Anything in `ops/` is operator-facing and never in the container
- Docker copies only `app/`, `alembic/`, `alembic.ini` (explicit, not blanket)

---

## Deployment Reality (Current)

- **Compute**: AWS ECS Fargate (cluster: `the-combine-cluster`)
- **Networking**: Route 53 A record → direct task public IP (no ALB)
- **DNS**: `thecombine.ai` (port 8000, HTTP only)
- **IP changes**: Handled via `ops/aws/fixip.ps1` after redeployment
- **CI/CD**: GitHub Actions → ECR → ECS task definition update → Route 53 update
- **Secrets**: Anthropic API key in AWS Secrets Manager, injected at runtime
- **Database**: RDS PostgreSQL (publicly accessible for dev)

No blue/green. No canary. IP changes on every deploy.

---

## Testing Strategy (Current)

- **Tier-1**: In-memory repositories, no DB, pure business logic verification
- **Tier-2**: Spy repositories for call contract verification (wiring tests)
- **Tier-3**: Real PostgreSQL — **deferred** (requires test DB infrastructure)

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
- Do **not** infer missing inputs — they fail explicitly

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

## Governing ADRs (Active)

| ADR | Status | Summary |
|-----|--------|---------|
| ADR-009 | ✅ Complete | Project Audit — all state changes explicit and traceable |
| ADR-010 | ✅ Complete | LLM Execution Logging — inputs, outputs, replay capability |
| ADR-011 | 🟡 In Progress | Project/Epic organization (draft exists) |

ADR documents live in `docs/adr/`. Each has implementation reports.

---

## Project Knowledge Available to AI

This Claude Project includes uploaded reference materials:
- Canonical architecture documents
- Active ADRs and implementation reports
- Design constitution and UX reference
- Coding standards

**Search project knowledge before assuming gaps.**

---

## Non-Negotiables

- Do not merge role logic into task prompts
- Do not invent workflow, ceremony, or process
- Do not assume undocumented context
- Do not suggest SQLite for testing
- Do not edit prompts without version bump
- Session summaries are logs — never edit after writing
- Discipline > convenience

---

## Session Management

### How to Start a New AI Session

Before any work:

1. Read `AI.md` completely
2. Read `docs/PROJECT_STATE.md`
3. Scan recent session logs in `docs/session_logs/`
4. Summarize back:
   - System purpose
   - Current state
   - Active constraints (ADRs)
   - Next logical work
5. Ask for confirmation before proceeding

### How to Close a Session

When the user says **"Prepare session close"** (or similar):

1. Write session summary to `docs/session_logs/YYYY-MM-DD.md`
   - Use fixed template (scope, decisions, implemented, commits, open threads, risks)
   - No prose, no reflection — facts only
   - Include git commits/PRs if applicable
2. Update `docs/PROJECT_STATE.md`
   - Current state
   - Handoff notes for next session
3. Pause and ask: **"Ready to close, or do you want to continue?"**

Session summaries are **immutable logs**. They capture "what happened" — not decisions (ADRs) or current state (PROJECT_STATE.md).

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
   - "Decisions Made" = explicit agreements or resolutions.
   - "Implemented" = concrete artifacts created or modified.
   - "Discussed" items belong nowhere unless they resulted in a decision or implementation.

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
# Session Summary — YYYY-MM-DD

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
# (script TBD — currently manual)
```

---

_Last reviewed: 2026-01-02_
