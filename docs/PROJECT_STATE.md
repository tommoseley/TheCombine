# PROJECT_STATE.md

Last Updated: 2026-01-16

## Current Status

**Phase:** Document Interaction Workflow implementation
**Test Suite:** 1,294 tests passing
**Deployment:** Production on AWS ECS Fargate (thecombine.ai:8000)
**Dev Environment:** Linux/WSL (~/dev/TheCombine)

## Recent Work

### 2026-01-16: Linux Migration + ADR-039 Document Interaction Workflows

**Linux/WSL Development Environment Migration**
- Moved from `/mnt/c/dev/The Combine` to `~/dev/TheCombine` (native Linux filesystem)
- Python 3.11 venv configured
- PostgreSQL connectivity to Windows host (172.24.0.1)
- SSH keys configured for GitHub
- `.env` loading fixed in `database.py`
- CLAUDE.md updated for Linux paths and commands
- Windows copy deleted; single source of truth established

**ADR-039: Document Interaction Workflow Model (Draft)**
- Establishes document-scoped workflows as first-class concept
- Documents own their clarification/generation/QA/remediation loops
- Project workflows invoke document workflows and react only to terminal outcomes
- Terminal outcomes: `stabilized`, `blocked`, `abandoned`
- Orthogonal to ADR-036 lifecycle states (workflow execution vs artifact admissibility)
- Integrates with ADR-035 (durable threads), ADR-038 (workflow plans)

**ADR-025 Amendment**
- Clarified compatibility with ADR-039
- Intake Gate = governance boundary (policy/semantics)
- Document Interaction Workflow = execution model
- Dual outcome recording: governance vocabulary + execution vocabulary
- Gate outcome is authoritative; workflow terminal outcome mapped deterministically

## Active Work Items

**WS-INTAKE-WORKFLOW-001** (pending acceptance)
- Reference Concierge Intake Document Workflow Plan
- First implementation of ADR-039 pattern

## Architecture Snapshot

- **10 implementation phases complete** (ADR-034 document composition)
- **Document-centric model** with render manifests and canonical components
- **ADR-039** establishes document interaction workflows
- **ADR-025/039 alignment** governance boundary + execution model layering
- **Three-tier testing** (Tier-1 in-memory, Tier-2 spy, Tier-3 deferred)

## Commits (2026-01-16)

- `6588772` Linux/WSL development environment migration
- `fb4db8e` ADR-039: Document Interaction Workflow Model (Draft)
- `69ecfdf` ADR-025: Amendment for ADR-039 compatibility

## Known Issues

None.

## Next Logical Work

- Accept WS-INTAKE-WORKFLOW-001
- Implement reference Concierge Intake Document Workflow Plan
