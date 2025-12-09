# PIPELINE-175C: Local Deployment & Bootstrap (PM Phase)

**Epic:** PIPELINE-175C  
**Type:** Infrastructure / Bootstrap  
**Priority:** CRITICAL  
**Estimated Effort:** 22 hours (3 days)  
**Token Budget:** 6,000 tokens (JSON-first approach)

---

## Epic Goal

Enable self-hosted execution of The Combine pipeline so it can develop itself autonomously, eliminating expensive web interface usage and enabling rapid iteration.

**Success Criteria:** Pipeline successfully executes a simple epic (e.g., "Add health check endpoint") via local API server, generating valid code, running tests, and storing artifacts.

---

## Context

**Current State:**
- ✅ PIPELINE-175A complete (database infrastructure)
- ✅ PIPELINE-175B complete (execution engine)
- ✅ 70/70 tests passing
- ❌ No local deployment capability
- ❌ Still using expensive web interface

**Problem:**
- Web interface token costs unsustainable (~160K tokens for 175B)
- Manual process, not scalable
- Can't iterate rapidly

**Opportunity:**
- All infrastructure exists (database + execution engine)
- Only need deployment scripts + first execution
- JSON-first approach reduces costs 77%

---

## Stories

### Story 1: Environment Setup Script

**As a** developer  
**I want** one-command environment setup  
**So that** I can quickly deploy the pipeline locally

**Acceptance Criteria:**
- Single command (`./setup.sh`) sets up complete environment
- Creates virtual environment
- Installs dependencies
- Initializes database (SQLite for local dev)
- Runs migrations
- Seeds role prompts and phase configurations
- Runs test suite to verify
- Exits with clear success/failure message

**Deliverables:**
- `setup.sh` - Bash script for Unix/Mac
- `setup.ps1` - PowerShell script for Windows
- `requirements.txt` - Python dependencies
- `scripts/init_db.py` - Database initialization
- `README.md` - Setup instructions

**Estimate:** 4 hours

---

### Story 2: API Server Startup

**As a** developer  
**I want** to start the orchestrator API server locally  
**So that** I can interact with the pipeline via HTTP

**Acceptance Criteria:**
- Single command (`./run.sh`) starts server
- Server runs on `localhost:8000`
- Swagger docs accessible at `/docs`
- Health check endpoint (`/health`) returns 200
- Environment variables loaded from `.env`
- Feature flag `DATA_DRIVEN_ORCHESTRATION` set to `true`
- Logs indicate successful startup

**Deliverables:**
- `run.sh` - Server startup script
- `.env.example` - Template for environment variables
- `app/routers/health.py` - Health check endpoint (if not exists)
- Updated `README.md` - How to run server

**Estimate:** 2 hours

---

### Story 3: First Self-Hosted Execution

**As a** pipeline user  
**I want** to execute a simple epic via local API  
**So that** I can verify the pipeline works end-to-end

**Acceptance Criteria:**
- Can create pipeline via `POST /pipelines`
- Can advance through PM phase via `POST /pipelines/{id}/advance`
- PM phase generates valid epic artifact
- Artifact stored in database
- Usage recorded in `pipeline_prompt_usage` table
- Can retrieve artifacts via `GET /pipelines/{id}/artifacts`
- Test script verifies complete flow

**Test Epic:** "Add a /metrics endpoint to the orchestrator API that returns basic stats"

**Deliverables:**
- `scripts/test_self_hosted.py` - End-to-end test script
- Documentation of test results
- Verification that all 175A+175B components work

**Estimate:** 4 hours

---

### Story 4: JSON Schema Migration

**As a** pipeline developer  
**I want** LLMs to output only JSON (not prose)  
**So that** token costs are minimized and post-processing is deterministic

**Acceptance Criteria:**
- Pydantic schemas defined for all artifact types:
  - `EpicSpec` (PM phase output)
  - `ArchitectureSpec` (Architect phase output)
  - `CodeDeliverable` (Developer phase output)
  - `QAReport` (QA phase output)
- Role prompts updated to request JSON-only output
- Response parser validates JSON against schemas
- Jinja2 templates generate human-readable docs from JSON
- Test with simple epic shows 70%+ token reduction

**Deliverables:**
- `app/schemas/artifacts.py` - Pydantic models for all artifacts
- `app/templates/` - Jinja2 templates for human docs
- Updated role prompts in database
- `scripts/migrate_to_json.py` - Migration script
- Documentation of schema formats

**Estimate:** 8 hours

---

### Story 5: Token Usage Tracking & Cost Reporting

**As a** pipeline developer  
**I want** comprehensive token usage and cost tracking  
**So that** I can optimize prompts and monitor expenses

**Acceptance Criteria:**
- Database extended to store token counts per LLM call
- Cost calculated based on Anthropic pricing (input/output rates)
- CLI command to view token usage by pipeline, phase, role
- Dashboard endpoint (`/metrics/tokens`) showing:
  - Total tokens used (input/output)
  - Cost per pipeline
  - Cost per phase
  - Cost per role
  - Average tokens per phase
  - Trends over time
- Alerts when pipeline exceeds token budget
- Export token usage data to CSV/JSON

**Deliverables:**
- Migration script to add token columns to `pipeline_prompt_usage`
- Updated `UsageRecorder` to capture token counts
- `TokenMetricsService` for aggregation and cost calculation
- CLI command: `python manage.py token-report --pipeline <id>`
- API endpoint: `GET /metrics/tokens`
- Documentation of pricing model

**Estimate:** 4 hours

---

## Architecture Constraints

### Minimal Scope - Out of Scope for 175C

**NOT included in 175C:**
- ❌ File system read/write (175D)
- ❌ Git integration (175E)
- ❌ Web UI (176)
- ❌ Multi-user support
- ❌ Authentication
- ❌ Docker deployment
- ❌ Production hardening

**175C is ONLY:**
- ✅ Local dev environment
- ✅ API server startup
- ✅ First successful execution
- ✅ JSON schema foundation

### JSON Schema Examples

#### PM Phase Output (EpicSpec)

```python
from pydantic import BaseModel, Field
from typing import List

class Story(BaseModel):
    id: str = Field(description="Story identifier, e.g., STORY-1")
    title: str = Field(max_length=100)
    user_story: str = Field(description="As a X, I want Y, so that Z")
    acceptance_criteria: List[str]
    estimate_hours: int
    priority: str = Field(pattern="^(critical|high|medium|low)$")

class EpicSpec(BaseModel):
    epic_id: str
    title: str = Field(max_length=100)
    goal: str = Field(max_length=500, description="One sentence goal")
    success_criteria: List[str]
    stories: List[Story]
    out_of_scope: List[str]
    risks: List[str]
    total_estimate_hours: int
```

**Updated PM Prompt:**
```
You are a product manager. Output ONLY valid JSON matching this schema:

{schema_json}

Epic description: {epic_context}

Output JSON (no markdown, no prose):
```

**Token Savings:**
- Before: ~15K tokens (prose epic document)
- After: ~2K tokens (JSON spec)
- **87% reduction**

#### Template for Human Docs

```jinja2
# {{ epic.title }}

**Goal:** {{ epic.goal }}

## Success Criteria
{% for criterion in epic.success_criteria %}
- {{ criterion }}
{% endfor %}

## Stories
{% for story in epic.stories %}
### {{ story.id }}: {{ story.title }}
{{ story.user_story }}

**Acceptance Criteria:**
{% for ac in story.acceptance_criteria %}
- {{ ac }}
{% endfor %}

**Estimate:** {{ story.estimate_hours }} hours
{% endfor %}

**Total Estimate:** {{ epic.total_estimate_hours }} hours
```

---

## Success Metrics

**Primary:**
- ✅ Local server starts and responds
- ✅ Pipeline creates and executes successfully
- ✅ All artifacts validate against schemas
- ✅ Tests pass in local environment

**Secondary:**
- ✅ Token usage for test epic <5K tokens
- ✅ Execution time <60 seconds
- ✅ Setup time <10 minutes
- ✅ Documentation enables new developer to run in <30 minutes

---

## Risks & Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Database migration issues | Medium | High | Test migrations thoroughly, provide rollback |
| Environment setup complexity | Low | Medium | Comprehensive README, tested on multiple OSes |
| JSON schema too restrictive | Medium | Medium | Start with flexible schemas, iterate |
| LLM refuses JSON-only format | Low | High | Prompt engineering, fallback parser |

---

## Dependencies

**Requires:**
- ✅ PIPELINE-175A deployed (database tables exist)
- ✅ PIPELINE-175B deployed (execution engine exists)
- ✅ Anthropic API key available

**Enables:**
- ⏳ PIPELINE-175D: File System Integration
- ⏳ PIPELINE-175E: Git Integration
- ⏳ PIPELINE-176: Web UI
- ⏳ Self-improvement loop

---

## Token Budget

**Estimated Usage (JSON-first):**
- Architecture phase: ~1,500 tokens (JSON component specs)
- Development phase: ~2,500 tokens (JSON code deliverable + token tracking)
- QA phase: ~500 tokens (JSON issue list)
- Testing/iterations: ~1,500 tokens

**Total: ~6,000 tokens** (vs ~100K for prose approach)

---

## Next Steps

**After PM Approval:**
1. Architect phase: Design JSON schemas and component changes
2. BA phase: Detailed acceptance criteria for each story
3. Dev phase: Implement scripts, schemas, templates
4. QA phase: Verify end-to-end execution
5. Deploy: Run first self-hosted epic

**After 175C Complete:**
- Pipeline can develop itself
- Token costs drop 77%
- Iteration speed increases 10x
- Ready for autonomous development

---

**PM:** [Your Name]  
**Date:** 2025-12-05  
**Status:** Ready for Architect Phase  
**Priority:** CRITICAL - Token costs unsustainable
