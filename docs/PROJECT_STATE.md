# Project State — The Combine

_Last updated: 2026-01-02 by Claude_

This document captures the **current factual state** of the project.  
Updated at the end of each significant work session.

---

## Current Objective

ADR-011 implementation (project/epic organization) — awaiting draft from Tom.

---

## Implemented

- ✅ ADR-009 Project Audit — all state changes traceable
- ✅ ADR-010 LLM Execution Logging — full telemetry with replay (all 4 weeks complete)
- ✅ Repository restructured into four buckets (`app/`, `seed/`, `ops/`, `docs/`)
- ✅ Prompt certification framework (roles + tasks in `seed/prompts/`)
- ✅ `seed/manifest.json` with SHA-256 checksums
- ✅ GitHub Actions CI/CD: ECR → ECS Fargate → Route 53
- ✅ Anthropic API key in AWS Secrets Manager
- ✅ `.dockerignore` and explicit Dockerfile COPYs
- ✅ AI bootstrap system (`AI.md`, `PROJECT_STATE.md`, `docs/session_logs/`)
- ✅ Session close ritual documented
- ✅ Backfill prompt for old sessions in AI.md

---

## In Progress

- 🟡 ADR-011 Project/Epic organization (Tom has draft from ChatGPT)

---

## Next Likely Work

- 🔜 Review and implement ADR-011 when Tom shares draft
- 🔜 Review `recycle/` folder, then delete
- 🔜 Commit restructure changes and push to trigger CI/CD
- 🔜 Automated seed manifest regeneration script
- 🔜 ALB for stable endpoint (pending AWS permission)

---

## Active Constraints

- No role/task prompt boundary violations
- No implicit memory between tasks
- All LLM executions must be logged and replayable
- Prompts require version bump + certification for changes
- Tier-3 tests deferred until test DB infrastructure exists
- Session summaries are immutable logs

---

## Known Issues / Sharp Edges

- Route 53 points directly to task IP — changes on every deploy
- No HTTPS (HTTP on port 8000 only)
- Database publicly accessible (dev configuration)
- `recycle/` folder contains deleted files — review then delete
- Changes from today not yet committed to git

---

## Environments

| Environment | Stack | Status |
|-------------|-------|--------|
| Local dev | Python 3.12 + local Postgres | ✅ Working |
| CI | GitHub Actions + Postgres service | ✅ Working |
| Test | ECS Fargate + RDS | ✅ Deployed |
| Prod | Not deployed | — |

---

## Recent Changes

| Date | Change |
|------|--------|
| 2026-01-02 | AI bootstrap system complete |
| 2026-01-02 | Repository restructured: four-bucket model |
| 2026-01-02 | ADR-010 Week 4 complete — deployed to test |
| 2026-01-02 | Fixed `document_builder.py` emoji corruption |
| 2026-01-02 | GitHub Actions updated for ECS + Route 53 |
| 2026-01-01 | ADR-010 Week 3 complete — replay endpoint |
| 2026-01-01 | ADR-010 Week 2 complete — repository pattern |

---

## Session Logs

Session summaries live in `docs/session_logs/`. Most recent:
- `2026-01-02.md` — ADR-010 deployment, restructure, AI bootstrap system

---

## Notes for AI Collaborators

- Prefer asking clarifying questions over assuming intent
- Search project knowledge before assuming gaps
- Update this file when a session produces durable changes
- `recycle/` contains files marked for deletion — do not restore without asking
- Session summaries are immutable — never edit after writing

---

## Session Handoff

_Notes for the next session._

**Last session (2026-01-02):**
- Completed four-bucket restructure
- Created full AI bootstrap system (AI.md, PROJECT_STATE.md, session_logs/)
- Added backfill prompt to AI.md for retroactive session logs
- Test deployment working
- Tom has ADR-011 draft from ChatGPT — not yet shared with Claude

**Next session should:**
- Review ADR-011 when Tom shares it
- Review `recycle/` folder contents, then delete
- Commit all changes and push (validate Dockerfile in CI)
