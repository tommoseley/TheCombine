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

## Skills

Operational procedures are organized as on-demand Claude Code Skills. Each loads automatically when its trigger context matches.

| Skill | When to Use |
|-------|------------|
| `ws-execution` | Executing Work Statements, Do No Harm audits, phase management |
| `autonomous-bug-fix` | Runtime errors, exceptions, bug-first testing rule |
| `subagent-dispatch` | Parallel WS execution, spawning subagents |
| `metrics-reporting` | Reporting WS execution metrics at phase boundaries |
| `session-management` | Starting/closing sessions, writing session logs |
| `config-governance` | Seed/prompt changes, ADR-040 stateless LLM, ADR-049 no black boxes |
| `ia-validation` | Authoring/reviewing IA in package.yaml, render_as rules |
| `ia-golden-tests` | Running/debugging IA golden contract tests |
| `tier0-verification` | Running tier0.sh, interpreting results, WS scope mode |
| `combine-governance` | ADR execution auth, WS/WP structure, ADR-045 taxonomy |

Skills live in `.claude/skills/<name>/SKILL.md`. See `.claude/skills/README.md` for full catalog.

---

## Governing Policies (Always-On Summaries)

- **POL-WS-001**: Work Statements define all implementation work. Follow steps in order. Stop on ambiguity.
  *(See: `.claude/skills/ws-execution/SKILL.md`)*

- **POL-ADR-EXEC-001**: ADR acceptance does NOT authorize execution. Follow the 6-step authorization path.
  *(See: `.claude/skills/combine-governance/SKILL.md`)*

---

## Execution Constraints (Always-On)

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
  - Before creating anything new (file, module, schema, service, prompt): search the codebase and existing docs/ADRs. Prefer extending or refactoring over creating. Only create something new when reuse is not viable.
  - Creating something new when a suitable existing artifact existed is a defect.

- **Tier 0 is the bar**: No work is complete unless `ops/scripts/tier0.sh` returns zero.

- **combine-config is canonical**: Runtime configuration lives in `combine-config/`. Do not invent file paths or duplicate configuration outside it.

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

## Governing ADRs (Active)

| ADR | Status | Summary |
|-----|--------|---------|
| ADR-009 |  Complete | Project Audit - all state changes explicit and traceable |
| ADR-010 |  Complete | LLM Execution Logging - inputs, outputs, replay capability |
| ADR-011 |  In Progress | Project/Epic organization (draft exists) |
| ADR-045 |  Accepted | System Ontology - Primitives, Composites, Configuration Taxonomy |
| ADR-054 |  Accepted | Governed Information Architecture with HTML and PDF Targets |

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
ops/scripts/tier0.sh --ws --scope ops/scripts/ tests/infrastructure/ docs/policies/ CLAUDE.md

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

_Last reviewed: 2026-02-24_
