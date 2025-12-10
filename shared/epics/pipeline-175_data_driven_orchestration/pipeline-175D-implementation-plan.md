# 🏗️ Developer Mentor Implementation Plan – PIPELINE-175D (Metrics Dashboard)

---

## Epic & Intent Recap

**PIPELINE-175D: Metrics Dashboard**

- **Goal:** Provide a lightweight operator dashboard surfacing token usage, cost data, and system health from existing audit tables to validate end-to-end functionality and build operator confidence.

- **Key Success Criteria:**
  - Operator can view total cost and token usage across all pipelines in <3 seconds
  - Per-pipeline cost breakdown visible with phase-level detail
  - Dashboard confirms UsageRecorder is writing data (live spend validation)
  - Zero changes to orchestrator logic or pipeline execution flow
  - All endpoints respond <2s for 1000 pipelines (soft target)

- **Critical Constraints:**
  - No authentication (operator tool, trusted network)
  - Uses existing 175C schema (no new tables)
  - SQLite with no new indexes (ADR-014)
  - Jinja2 server-rendered UI (no build tooling, ADR-015)
  - Tailwind CSS + Chart.js from CDN
  - Chart.js has graceful table fallback (ADR-016)

- **Success/Failure Definitions:**
  - `success_count` = pipelines with `status='completed'`
  - `failure_count` = pipelines with `status IN ('failed', 'error')`
  - All other statuses excluded from these counts

---

## Architecture Alignment

**Data Flow:**
```
SQLite DB
  ↓
Repositories (extensions)
  - PipelinePromptUsageRepository.get_system_aggregates()
  - PipelinePromptUsageRepository.get_pipeline_usage()
  - PipelinePromptUsageRepository.get_daily_aggregates()
  - PipelineRepository.get_pipeline_with_epic()
  ↓
TokenMetricsService
  - Wraps all repository calls in try/except
  - Returns internal dataclasses (MetricsSummary, PipelineMetrics, etc.)
  - Never raises exceptions to router
  ↓
MetricsRouter
  - Converts internal types → Pydantic schemas for JSON
  - Passes internal types → Jinja2 templates for HTML
  - Handles None → 404
  ↓
Response (JSON or HTML)
  - JSON: MetricsSummaryResponse, PipelineMetricsResponse
  - HTML: overview.html, detail.html with full context objects
```

**Component Breakdown:**
1. **TokenMetricsService** - Business logic, aggregation, error handling
2. **MetricsRouter** - Thin API layer, 4 endpoints (2 JSON, 2 HTML)
3. **MetricsSchemas** - Pydantic models for JSON responses
4. **Repository Extensions** - SQL aggregation queries
5. **Templates** - 4 Jinja2 files (2 pages, 2 partials)
6. **Tests** - 36 unit + 12 integration

**Type System (from ArchitectureSpec type_glossary):**
- **Internal types** (service layer): MetricsSummary, PipelineMetrics, PipelineSummary, DailyCost (includes all fields)
- **External types** (JSON API): MetricsSummaryResponse (excludes last_usage_timestamp), PipelineMetricsResponse
- **Shared type**: PhaseMetrics (used in both internal and external)

---

## Work Plan by Developer

### Dev A – Backend & Services

**Responsibility:** Implement repository extensions and TokenMetricsService with comprehensive error handling.

---

#### **Task A1: Repository Extension - PipelinePromptUsageRepository**

**File:** `app/orchestrator_api/persistence/repositories/pipeline_prompt_usage_repository.py`

**What to implement:**

Add three new methods to the existing `PipelinePromptUsageRepository` class:

1. **`get_system_aggregates() -> dict`**
   - **SQL:** Single query with aggregations:
     ```sql
     SELECT 
       SUM(cost_usd) as total_cost,
       SUM(input_tokens) as total_input,
       SUM(output_tokens) as total_output,
       COUNT(*) as count,
       MAX(created_at) as last_timestamp
     FROM pipeline_prompt_usage
     ```
   - **Returns:** `{"total_cost": float, "total_input_tokens": int, "total_output_tokens": int, "count": int, "last_timestamp": datetime | None}`
   - **Error handling:** Raise exception on DB error (service will catch)
   - **Empty table:** Return zeros and None for timestamp

2. **`get_pipeline_usage(pipeline_id: str) -> list[UsageRecord]`**
   - **SQL:** `SELECT * FROM pipeline_prompt_usage WHERE pipeline_id = ? ORDER BY created_at`
   - **Returns:** List of SQLAlchemy model instances (existing `PipelinePromptUsage` model)
   - **Error handling:** Raise exception on DB error
   - **Not found:** Return empty list

3. **`get_daily_aggregates(days: int) -> list[dict]`**
   - **SQL:** 
     ```sql
     SELECT DATE(created_at) as date, SUM(cost_usd) as cost 
     FROM pipeline_prompt_usage 
     WHERE created_at >= DATE('now', '-{days} days')
     GROUP BY DATE(created_at)
     ```
   - **Returns:** List of `{"date": str (YYYY-MM-DD), "total_cost": float}`
   - **Important:** Uses database UTC timezone (see ADR-014)
   - **Error handling:** Raise exception on DB error
   - **Sparse data:** Only returns days with data (service fills gaps)

**Reference:** ArchitectureSpec Component "PipelinePromptUsageRepository (Extension)", ADR-013 (SQL aggregation)

**Unit tests:** 3 tests covering each method with mock DB

---

#### **Task A2: Repository Extension - PipelineRepository**

**File:** `app/orchestrator_api/persistence/repositories/pipeline_repository.py`

**What to implement:**

Add one new method to existing `PipelineRepository` class:

**`get_pipeline_with_epic(pipeline_id: str) -> dict | None`**
- **SQL:** `SELECT id, status, current_phase, artifacts, created_at FROM pipelines WHERE id = ?`
- **Returns:** 
  ```python
  {
    "pipeline_id": str,
    "status": str,
    "current_phase": str,
    "epic_description": str | None,  # Extracted from artifacts JSON
    "created_at": datetime
  }
  ```
- **Epic extraction logic:**
  - Parse `artifacts` JSON field
  - Look for `artifacts.get("epic", {}).get("description")` or similar structure
  - If JSON invalid or epic missing: `epic_description = None`
- **Error handling:** Raise exception on DB error
- **Not found:** Return `None`

**Reference:** ArchitectureSpec Component "PipelineRepository (Extension)", Story 175D-2

**Unit tests:** 3 tests (found with epic, found without epic, not found)

---

#### **Task A3: Create Internal Dataclasses**

**File:** `app/orchestrator_api/services/token_metrics_types.py` (NEW)

**What to implement:**

Create dataclasses for internal service layer types:

```python
from dataclasses import dataclass
from datetime import datetime

@dataclass
class MetricsSummary:
    total_pipelines: int
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    success_count: int
    failure_count: int
    last_usage_timestamp: datetime | None

@dataclass
class PipelineSummary:
    pipeline_id: str
    epic_description: str | None
    status: str
    total_cost_usd: float
    total_tokens: int
    created_at: datetime

@dataclass
class PhaseMetricsInternal:
    phase_name: str
    role_name: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    execution_time_ms: int | None
    timestamp: str

@dataclass
class PipelineMetrics:
    pipeline_id: str
    status: str
    current_phase: str
    epic_description: str | None
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    phase_breakdown: list[PhaseMetricsInternal]

@dataclass
class DailyCost:
    date: str  # YYYY-MM-DD
    total_cost_usd: float
```

**Reference:** ArchitectureSpec type_glossary, internal_types section

---

#### **Task A4: Implement TokenMetricsService**

**File:** `app/orchestrator_api/services/token_metrics_service.py` (NEW)

**What to implement:**

Create `TokenMetricsService` class with four methods. **CRITICAL:** All methods must wrap repository calls in try/except and never raise exceptions.

**Imports:**
```python
import logging
from datetime import datetime, timedelta
from typing import Optional

from app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository import PipelinePromptUsageRepository
from app.orchestrator_api.persistence.repositories.pipeline_repository import PipelineRepository
from app.orchestrator_api.persistence.database import get_db_session
from app.orchestrator_api.services.token_metrics_types import (
    MetricsSummary, PipelineMetrics, PipelineSummary, DailyCost, PhaseMetricsInternal
)
```

**Methods:**

1. **`get_summary() -> MetricsSummary`**
   - Call `PipelinePromptUsageRepository().get_system_aggregates()`
   - Call `PipelineRepository().get_status_counts()` or query directly:
     - `success_count = COUNT where status='completed'`
     - `failure_count = COUNT where status IN ('failed', 'error')`
   - **Error handling:**
     ```python
     try:
         aggregates = usage_repo.get_system_aggregates()
         # ... build MetricsSummary
     except Exception as e:
         logging.warning(f"Metrics aggregation failed: {e}")
         return MetricsSummary(
             total_pipelines=0,
             total_cost_usd=0.0,
             total_input_tokens=0,
             total_output_tokens=0,
             success_count=0,
             failure_count=0,
             last_usage_timestamp=None
         )
     ```
   - Return populated `MetricsSummary` dataclass

2. **`get_pipeline_metrics(pipeline_id: str) -> PipelineMetrics | None`**
   - Call `PipelineRepository().get_pipeline_with_epic(pipeline_id)`
   - If pipeline not found: return `None`
   - Call `PipelinePromptUsageRepository().get_pipeline_usage(pipeline_id)`
   - Build `phase_breakdown` from usage records
   - Calculate totals (sum input/output tokens, cost)
   - **Error handling:**
     ```python
     try:
         pipeline = pipeline_repo.get_pipeline_with_epic(pipeline_id)
         if not pipeline:
             return None
         usage_records = usage_repo.get_pipeline_usage(pipeline_id)
         # ... build PipelineMetrics
     except Exception as e:
         logging.warning(f"Pipeline metrics failed for {pipeline_id}: {e}")
         return None
     ```

3. **`get_recent_pipelines(limit: int = 20) -> list[PipelineSummary]`**
   - Query pipelines table: `SELECT * FROM pipelines ORDER BY created_at DESC LIMIT {limit}`
   - Join with usage aggregates to get cost/token totals
   - **Error handling:** Return empty list on exception

4. **`get_daily_costs(days: int = 7) -> list[DailyCost]`**
   - Call `PipelinePromptUsageRepository().get_daily_aggregates(days)`
   - Fill missing dates with 0.0 cost (important for chart display)
   - **Date range logic:**
     ```python
     # Generate all dates in range
     end_date = datetime.now().date()
     start_date = end_date - timedelta(days=days-1)
     all_dates = [(start_date + timedelta(days=i)).isoformat() for i in range(days)]
     
     # Merge with actual data
     data_map = {row["date"]: row["total_cost"] for row in aggregates}
     return [DailyCost(date=d, total_cost_usd=data_map.get(d, 0.0)) for d in all_dates]
     ```
   - **Error handling:** Return empty list on exception

**Reference:** ArchitectureSpec Component "TokenMetricsService", ADR-012 (error handling contract)

**Unit tests:** 12 tests covering all methods with mocked repositories, exception handling, empty data

---

### Dev B – API & Schemas

**Responsibility:** Implement Pydantic schemas and FastAPI router with correct JSON/HTML endpoint handling.

---

#### **Task B1: Create Pydantic Schemas**

**File:** `app/orchestrator_api/schemas/metrics.py` (NEW)

**What to implement:**

Create Pydantic response models for JSON endpoints:

```python
from pydantic import BaseModel, Field
from typing import Optional

class MetricsSummaryResponse(BaseModel):
    """JSON response for GET /metrics/summary - excludes last_usage_timestamp"""
    total_pipelines: int
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    success_count: int
    failure_count: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "total_pipelines": 42,
                "total_cost_usd": 12.50,
                "total_input_tokens": 150000,
                "total_output_tokens": 50000,
                "success_count": 38,
                "failure_count": 4
            }
        }

class PhaseMetrics(BaseModel):
    """Shared schema for phase-level metrics"""
    phase_name: str
    role_name: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    execution_time_ms: Optional[int] = None
    timestamp: str

class PipelineMetricsResponse(BaseModel):
    """JSON response for GET /metrics/pipelines/{id}"""
    pipeline_id: str
    status: str
    current_phase: str
    epic_description: Optional[str] = None
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    phase_breakdown: list[PhaseMetrics]
    
    class Config:
        json_schema_extra = {
            "example": {
                "pipeline_id": "pipe_123",
                "status": "completed",
                "current_phase": "commit",
                "epic_description": "Add metrics dashboard",
                "total_cost_usd": 0.45,
                "total_input_tokens": 12000,
                "total_output_tokens": 3000,
                "phase_breakdown": [
                    {
                        "phase_name": "pm_phase",
                        "role_name": "pm",
                        "input_tokens": 5000,
                        "output_tokens": 1500,
                        "cost_usd": 0.15,
                        "execution_time_ms": 3200,
                        "timestamp": "2025-12-06T10:30:00Z"
                    }
                ]
            }
        }
```

**Important Notes:**
- `MetricsSummaryResponse` does NOT include `last_usage_timestamp` (that's only in the internal `MetricsSummary` type)
- `PhaseMetrics` is shared between internal and external use
- Use `Optional` for nullable fields

**Reference:** ArchitectureSpec Component "MetricsSchemas", type_glossary

**Unit tests:** 7 tests for schema validation, optional fields, JSON serialization

---

#### **Task B2: Create MetricsRouter**

**File:** `app/orchestrator_api/routers/metrics.py` (NEW)

**What to implement:**

Create FastAPI router with 4 endpoints (2 JSON, 2 HTML):

**Setup:**
```python
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from datetime import datetime

from app.orchestrator_api.services.token_metrics_service import TokenMetricsService
from app.orchestrator_api.schemas.metrics import MetricsSummaryResponse, PipelineMetricsResponse

router = APIRouter()
templates = Jinja2Templates(directory="app/orchestrator_api/templates")
```

**Endpoints:**

1. **`GET /metrics/summary`** (JSON)
   ```python
   @router.get("/metrics/summary", response_model=MetricsSummaryResponse)
   async def get_metrics_summary():
       service = TokenMetricsService()
       summary = service.get_summary()
       
       # Convert internal MetricsSummary → MetricsSummaryResponse
       # Exclude last_usage_timestamp
       return MetricsSummaryResponse(
           total_pipelines=summary.total_pipelines,
           total_cost_usd=summary.total_cost_usd,
           total_input_tokens=summary.total_input_tokens,
           total_output_tokens=summary.total_output_tokens,
           success_count=summary.success_count,
           failure_count=summary.failure_count
       )
   ```

2. **`GET /metrics/pipelines/{pipeline_id}`** (JSON)
   ```python
   @router.get("/metrics/pipelines/{pipeline_id}", response_model=PipelineMetricsResponse)
   async def get_pipeline_metrics(pipeline_id: str):
       service = TokenMetricsService()
       metrics = service.get_pipeline_metrics(pipeline_id)
       
       if metrics is None:
           raise HTTPException(status_code=404, detail="Pipeline not found")
       
       # Convert internal PipelineMetrics → PipelineMetricsResponse
       return PipelineMetricsResponse(
           pipeline_id=metrics.pipeline_id,
           status=metrics.status,
           current_phase=metrics.current_phase,
           epic_description=metrics.epic_description,
           total_cost_usd=metrics.total_cost_usd,
           total_input_tokens=metrics.total_input_tokens,
           total_output_tokens=metrics.total_output_tokens,
           phase_breakdown=[
               PhaseMetrics(
                   phase_name=p.phase_name,
                   role_name=p.role_name,
                   input_tokens=p.input_tokens,
                   output_tokens=p.output_tokens,
                   cost_usd=p.cost_usd,
                   execution_time_ms=p.execution_time_ms,
                   timestamp=p.timestamp
               ) for p in metrics.phase_breakdown
           ]
       )
   ```

3. **`GET /metrics`** (HTML)
   ```python
   @router.get("/metrics", response_class=HTMLResponse)
   async def metrics_overview(request: Request):
       service = TokenMetricsService()
       summary = service.get_summary()
       recent = service.get_recent_pipelines(limit=20)
       daily = service.get_daily_costs(days=7)
       
       # Calculate last_usage_minutes for indicator
       last_usage_minutes = None
       if summary.last_usage_timestamp:
           delta = datetime.now() - summary.last_usage_timestamp
           last_usage_minutes = int(delta.total_seconds() / 60)
       
       return templates.TemplateResponse("metrics/overview.html", {
           "request": request,
           "summary": summary,  # Full MetricsSummary with timestamp
           "recent_pipelines": recent,
           "daily_costs": daily,
           "last_usage_minutes": last_usage_minutes
       })
   ```

4. **`GET /metrics/pipelines/{pipeline_id}`** (HTML)
   ```python
   @router.get("/metrics/pipelines/{pipeline_id}", response_class=HTMLResponse, name="pipeline_detail")
   async def pipeline_detail(request: Request, pipeline_id: str):
       service = TokenMetricsService()
       pipeline = service.get_pipeline_metrics(pipeline_id)
       
       if pipeline is None:
           raise HTTPException(status_code=404, detail="Pipeline not found")
       
       return templates.TemplateResponse("metrics/detail.html", {
           "request": request,
           "pipeline": pipeline  # Full PipelineMetrics
       })
   ```

**Important:**
- JSON endpoints convert internal types → Pydantic schemas
- HTML endpoints pass internal types directly to templates
- Service never raises exceptions, so only check for `None`
- No authentication (intentionally - see ADR and deployment notes)

**Reference:** ArchitectureSpec Component "MetricsRouter", Stories 175D-1, 175D-2, 175D-4, 175D-5

**Unit tests:** 8 tests with mocked service, covering all endpoints, 404 handling

---

#### **Task B3: Register Router in main.py**

**File:** `app/orchestrator_api/main.py`

**What to implement:**

Add metrics router to FastAPI app:

```python
from app.orchestrator_api.routers import metrics

# In create_app() or where routers are registered:
app.include_router(metrics.router, tags=["metrics"])
```

**Important:** Do NOT add authentication dependencies to this router (see deployment_notes in ArchitectureSpec)

**Reference:** ArchitectureSpec deployment_notes

---

### Dev C – Templates & Tests

**Responsibility:** Implement Jinja2 templates with Tailwind CSS and comprehensive test suite.

---

#### **Task C1: Create Directory Structure**

**What to implement:**

Create template directory:
```
app/orchestrator_api/templates/metrics/
├── overview.html
├── detail.html
├── _indicator.html
└── _chart.html
```

---

#### **Task C2: Implement Overview Template**

**File:** `app/orchestrator_api/templates/metrics/overview.html`

**What to implement:**

**Context received:**
- `summary`: MetricsSummary (includes last_usage_timestamp)
- `recent_pipelines`: list[PipelineSummary]
- `daily_costs`: list[DailyCost]
- `last_usage_minutes`: int | None

**Template structure:**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Metrics Dashboard - The Combine</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <meta http-equiv="refresh" content="30">  <!-- Auto-refresh every 30s -->
</head>
<body class="bg-gray-100 min-h-screen p-8">
    <div class="max-w-7xl mx-auto">
        <h1 class="text-3xl font-bold text-gray-900 mb-8">Pipeline Metrics Dashboard</h1>
        
        <!-- Summary Cards -->
        <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-sm font-medium text-gray-500">Total Cost</h3>
                <p class="text-3xl font-bold text-gray-900">${{ "%.2f"|format(summary.total_cost_usd) }}</p>
            </div>
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-sm font-medium text-gray-500">Total Tokens</h3>
                <p class="text-3xl font-bold text-gray-900">
                    {{ "{:,}".format(summary.total_input_tokens + summary.total_output_tokens) }}
                </p>
            </div>
            <div class="bg-white rounded-lg shadow p-6">
                <h3 class="text-sm font-medium text-gray-500">Pipelines</h3>
                <p class="text-3xl font-bold text-gray-900">{{ summary.total_pipelines }}</p>
                <p class="text-sm text-gray-500 mt-1">
                    {{ summary.success_count }} success, {{ summary.failure_count }} failed
                </p>
            </div>
        </div>
        
        <!-- Live Indicator -->
        {% include "metrics/_indicator.html" %}
        
        <!-- Recent Pipelines Table -->
        <div class="bg-white rounded-lg shadow mb-8">
            <div class="px-6 py-4 border-b border-gray-200">
                <h2 class="text-xl font-semibold">Recent Pipelines</h2>
            </div>
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">ID</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Epic</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Status</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cost</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Tokens</th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    {% for pipeline in recent_pipelines %}
                    <tr>
                        <td class="px-6 py-4 text-sm">
                            <a href="/metrics/pipelines/{{ pipeline.pipeline_id }}" 
                               class="text-blue-600 hover:underline">
                                {{ pipeline.pipeline_id[:12] }}...
                            </a>
                        </td>
                        <td class="px-6 py-4 text-sm">
                            {{ pipeline.epic_description or "(no epic available)" }}
                        </td>
                        <td class="px-6 py-4 text-sm">
                            <span class="px-2 py-1 rounded-full text-xs 
                                {% if pipeline.status == 'completed' %}bg-green-100 text-green-800
                                {% elif pipeline.status in ['failed', 'error'] %}bg-red-100 text-red-800
                                {% else %}bg-yellow-100 text-yellow-800{% endif %}">
                                {{ pipeline.status }}
                            </span>
                        </td>
                        <td class="px-6 py-4 text-sm">${{ "%.4f"|format(pipeline.total_cost_usd) }}</td>
                        <td class="px-6 py-4 text-sm">{{ "{:,}".format(pipeline.total_tokens) }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
        
        <!-- Cost Trend Chart -->
        {% include "metrics/_chart.html" %}
    </div>
</body>
</html>
```

**Reference:** Story 175D-4, ArchitectureSpec Component "MetricsTemplates"

---

#### **Task C3: Implement Detail Template**

**File:** `app/orchestrator_api/templates/metrics/detail.html`

**Context received:**
- `pipeline`: PipelineMetrics

**Template structure:**

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Pipeline {{ pipeline.pipeline_id }} - Metrics</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-100 min-h-screen p-8">
    <div class="max-w-7xl mx-auto">
        <div class="mb-4">
            <a href="/metrics" class="text-blue-600 hover:underline">&larr; Back to Dashboard</a>
        </div>
        
        <h1 class="text-3xl font-bold text-gray-900 mb-2">Pipeline Details</h1>
        <p class="text-gray-600 mb-8">{{ pipeline.pipeline_id }}</p>
        
        <!-- Pipeline Summary -->
        <div class="bg-white rounded-lg shadow p-6 mb-8">
            <h2 class="text-xl font-semibold mb-4">Summary</h2>
            <dl class="grid grid-cols-2 gap-4">
                <div>
                    <dt class="text-sm font-medium text-gray-500">Epic</dt>
                    <dd class="text-sm text-gray-900">{{ pipeline.epic_description or "(no epic available)" }}</dd>
                </div>
                <div>
                    <dt class="text-sm font-medium text-gray-500">Status</dt>
                    <dd class="text-sm text-gray-900">{{ pipeline.status }}</dd>
                </div>
                <div>
                    <dt class="text-sm font-medium text-gray-500">Current Phase</dt>
                    <dd class="text-sm text-gray-900">{{ pipeline.current_phase }}</dd>
                </div>
                <div>
                    <dt class="text-sm font-medium text-gray-500">Total Cost</dt>
                    <dd class="text-sm text-gray-900">${{ "%.6f"|format(pipeline.total_cost_usd) }}</dd>
                </div>
                <div>
                    <dt class="text-sm font-medium text-gray-500">Input Tokens</dt>
                    <dd class="text-sm text-gray-900">{{ "{:,}".format(pipeline.total_input_tokens) }}</dd>
                </div>
                <div>
                    <dt class="text-sm font-medium text-gray-500">Output Tokens</dt>
                    <dd class="text-sm text-gray-900">{{ "{:,}".format(pipeline.total_output_tokens) }}</dd>
                </div>
            </dl>
        </div>
        
        <!-- Phase Breakdown -->
        <div class="bg-white rounded-lg shadow">
            <div class="px-6 py-4 border-b border-gray-200">
                <h2 class="text-xl font-semibold">Phase Breakdown</h2>
            </div>
            <table class="min-w-full divide-y divide-gray-200">
                <thead class="bg-gray-50">
                    <tr>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Phase</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Role</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Input Tokens</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Output Tokens</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Cost</th>
                        <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase">Duration</th>
                    </tr>
                </thead>
                <tbody class="bg-white divide-y divide-gray-200">
                    {% for phase in pipeline.phase_breakdown %}
                    <tr>
                        <td class="px-6 py-4 text-sm">{{ phase.phase_name }}</td>
                        <td class="px-6 py-4 text-sm">{{ phase.role_name }}</td>
                        <td class="px-6 py-4 text-sm">{{ "{:,}".format(phase.input_tokens) }}</td>
                        <td class="px-6 py-4 text-sm">{{ "{:,}".format(phase.output_tokens) }}</td>
                        <td class="px-6 py-4 text-sm">${{ "%.6f"|format(phase.cost_usd) }}</td>
                        <td class="px-6 py-4 text-sm">
                            {% if phase.execution_time_ms %}
                                {{ phase.execution_time_ms }}ms
                            {% else %}
                                -
                            {% endif %}
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</body>
</html>
```

**Reference:** Story 175D-5

---

#### **Task C4: Implement Indicator Partial**

**File:** `app/orchestrator_api/templates/metrics/_indicator.html`

**Context received:**
- `last_usage_minutes`: int | None

```html
<div class="bg-white rounded-lg shadow p-6 mb-8">
    <h2 class="text-lg font-semibold mb-2">Live Spend Validation</h2>
    
    {% if last_usage_minutes is none %}
        <div class="flex items-center">
            <span class="w-3 h-3 rounded-full bg-gray-400 mr-2"></span>
            <span class="text-sm text-gray-600">Last usage record: unavailable</span>
        </div>
    {% elif last_usage_minutes < 10 %}
        <div class="flex items-center">
            <span class="w-3 h-3 rounded-full bg-green-500 mr-2"></span>
            <span class="text-sm text-gray-900">Last usage record: {{ last_usage_minutes }} minutes ago</span>
        </div>
    {% elif last_usage_minutes < 60 %}
        <div class="flex items-center">
            <span class="w-3 h-3 rounded-full bg-yellow-500 mr-2"></span>
            <span class="text-sm text-gray-900">Last usage record: {{ last_usage_minutes }} minutes ago</span>
        </div>
    {% else %}
        <div class="flex items-center">
            <span class="w-3 h-3 rounded-full bg-red-500 mr-2"></span>
            <span class="text-sm text-gray-900">Last usage record: {{ last_usage_minutes }} minutes ago</span>
        </div>
    {% endif %}
</div>
```

**Reference:** Story 175D-6

---

#### **Task C5: Implement Chart Partial with Fallback**

**File:** `app/orchestrator_api/templates/metrics/_chart.html`

**Context received:**
- `daily_costs`: list[DailyCost]

```html
<div class="bg-white rounded-lg shadow p-6">
    <h2 class="text-xl font-semibold mb-4">Cost Trend (Last 7 Days)</h2>
    
    <!-- Chart Container -->
    <div id="chart-container">
        <canvas id="costChart" width="400" height="100"></canvas>
    </div>
    
    <!-- Fallback Table (hidden by default) -->
    <div id="chart-fallback-table" style="display: none;">
        <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
                <tr>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">Date</th>
                    <th class="px-4 py-2 text-left text-xs font-medium text-gray-500">Cost (USD)</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-200">
                {% for day in daily_costs %}
                <tr>
                    <td class="px-4 py-2 text-sm">{{ day.date }}</td>
                    <td class="px-4 py-2 text-sm">${{ "%.4f"|format(day.total_cost_usd) }}</td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
    
    <script>
        // Detect Chart.js availability and render or fallback
        if (typeof Chart !== 'undefined') {
            const ctx = document.getElementById('costChart').getContext('2d');
            const dailyCosts = {{ daily_costs | tojson }};
            
            new Chart(ctx, {
                type: 'bar',
                data: {
                    labels: dailyCosts.map(d => d.date),
                    datasets: [{
                        label: 'Cost (USD)',
                        data: dailyCosts.map(d => d.total_cost_usd),
                        backgroundColor: 'rgba(59, 130, 246, 0.5)',
                        borderColor: 'rgb(59, 130, 246)',
                        borderWidth: 1
                    }]
                },
                options: {
                    responsive: true,
                    scales: {
                        y: {
                            beginAtZero: true,
                            ticks: {
                                callback: function(value) {
                                    return '$' + value.toFixed(4);
                                }
                            }
                        }
                    }
                }
            });
        } else {
            // Chart.js failed to load - show table fallback
            document.getElementById('chart-container').style.display = 'none';
            document.getElementById('chart-fallback-table').style.display = 'block';
        }
    </script>
</div>
```

**Reference:** Story 175D-7, ADR-016

---

#### **Task C6: Unit Tests for Service**

**File:** `tests/unit/services/test_token_metrics_service.py` (NEW)

**What to implement:**

12 unit tests covering TokenMetricsService with mocked repositories:

```python
import pytest
from unittest.mock import Mock, patch
from datetime import datetime

from app.orchestrator_api.services.token_metrics_service import TokenMetricsService
from app.orchestrator_api.services.token_metrics_types import MetricsSummary

class TestTokenMetricsService:
    def test_get_summary_with_data(self):
        """Test get_summary returns correct MetricsSummary from repo data"""
        # Mock repositories
        # Call service.get_summary()
        # Assert returned MetricsSummary has correct fields
        
    def test_get_summary_empty_database(self):
        """Test get_summary returns zeros when no data"""
        
    def test_get_summary_repository_exception(self):
        """Test get_summary catches exception and returns safe defaults"""
        # Mock repo to raise Exception
        # Assert service returns MetricsSummary with all zeros
        # Assert warning logged
        
    def test_get_pipeline_metrics_found(self):
        """Test get_pipeline_metrics returns PipelineMetrics for valid ID"""
        
    def test_get_pipeline_metrics_not_found(self):
        """Test get_pipeline_metrics returns None for invalid ID"""
        
    def test_get_pipeline_metrics_no_usage_records(self):
        """Test get_pipeline_metrics handles pipeline with no usage"""
        # Should return PipelineMetrics with empty phase_breakdown
        
    def test_get_pipeline_metrics_exception(self):
        """Test get_pipeline_metrics catches exception and returns None"""
        
    def test_get_recent_pipelines_with_data(self):
        """Test get_recent_pipelines returns list of PipelineSummary"""
        
    def test_get_recent_pipelines_empty(self):
        """Test get_recent_pipelines returns empty list when no pipelines"""
        
    def test_get_daily_costs_fills_missing_dates(self):
        """Test get_daily_costs fills gaps with 0.0"""
        # Mock repo returns sparse data (days 1, 3, 5)
        # Assert returned list has all 7 days with zeros for missing
        
    def test_get_daily_costs_all_zeros(self):
        """Test get_daily_costs with no usage data"""
        
    def test_get_daily_costs_exception(self):
        """Test get_daily_costs catches exception and returns empty list"""
```

**Reference:** ArchitectureSpec test_strategy.unit_tests

---

#### **Task C7: Unit Tests for Schemas**

**File:** `tests/unit/schemas/test_metrics_schemas.py` (NEW)

**What to implement:**

7 tests for Pydantic schema validation:

```python
import pytest
from pydantic import ValidationError

from app.orchestrator_api.schemas.metrics import (
    MetricsSummaryResponse, PipelineMetricsResponse, PhaseMetrics
)

def test_metrics_summary_valid():
    """Test MetricsSummaryResponse validates correctly"""
    data = {
        "total_pipelines": 10,
        "total_cost_usd": 5.5,
        "total_input_tokens": 50000,
        "total_output_tokens": 15000,
        "success_count": 8,
        "failure_count": 2
    }
    response = MetricsSummaryResponse(**data)
    assert response.total_pipelines == 10
    
def test_metrics_summary_missing_field():
    """Test MetricsSummaryResponse raises error for missing required field"""
    data = {"total_pipelines": 10}  # Missing other required fields
    with pytest.raises(ValidationError):
        MetricsSummaryResponse(**data)
        
def test_pipeline_metrics_valid():
    """Test PipelineMetricsResponse validates with full data"""
    
def test_pipeline_metrics_optional_epic():
    """Test PipelineMetricsResponse handles missing epic_description"""
    # epic_description = None should be valid
    
def test_phase_metrics_valid():
    """Test PhaseMetrics validates correctly"""
    
def test_phase_metrics_optional_execution_time():
    """Test PhaseMetrics handles execution_time_ms = None"""
    
def test_json_serialization_round_trip():
    """Test schemas serialize to JSON and back"""
```

**Reference:** ArchitectureSpec test_strategy.unit_tests

---

#### **Task C8: Unit Tests for Repository Extensions**

**File:** `tests/unit/repositories/test_pipeline_prompt_usage_repository.py` (UPDATE)

**What to implement:**

Add 6 tests for new aggregation methods:

```python
def test_get_system_aggregates_with_data():
    """Test get_system_aggregates returns correct aggregations"""
    
def test_get_system_aggregates_empty_table():
    """Test get_system_aggregates returns zeros for empty table"""
    
def test_get_pipeline_usage_found():
    """Test get_pipeline_usage returns usage records"""
    
def test_get_pipeline_usage_not_found():
    """Test get_pipeline_usage returns empty list for invalid pipeline_id"""
    
def test_get_daily_aggregates_sparse_data():
    """Test get_daily_aggregates with partial data"""
    
def test_get_daily_aggregates_no_data():
    """Test get_daily_aggregates returns empty list"""
```

**File:** `tests/unit/repositories/test_pipeline_repository.py` (UPDATE)

**What to implement:**

Add 3 tests for epic extraction:

```python
def test_get_pipeline_with_epic_found():
    """Test get_pipeline_with_epic extracts epic description"""
    
def test_get_pipeline_with_epic_no_epic():
    """Test get_pipeline_with_epic handles missing epic in artifacts"""
    
def test_get_pipeline_with_epic_not_found():
    """Test get_pipeline_with_epic returns None for invalid ID"""
```

**Reference:** ArchitectureSpec test_strategy.unit_tests

---

#### **Task C9: Integration Tests for JSON Endpoints**

**File:** `tests/integration/test_metrics_endpoints.py` (NEW)

**What to implement:**

6 integration tests hitting actual endpoints:

```python
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_get_summary_with_seeded_data(client: AsyncClient):
    """Test GET /metrics/summary returns correct aggregations"""
    # Seed DB with pipelines and usage records
    response = await client.get("/metrics/summary")
    assert response.status_code == 200
    data = response.json()
    assert "total_pipelines" in data
    assert "total_cost_usd" in data
    # Verify aggregations match seeded data
    
@pytest.mark.asyncio
async def test_get_summary_empty_database(client: AsyncClient):
    """Test GET /metrics/summary with no data"""
    # Don't seed anything
    response = await client.get("/metrics/summary")
    assert response.status_code == 200
    data = response.json()
    assert data["total_pipelines"] == 0
    assert data["total_cost_usd"] == 0.0
    
@pytest.mark.asyncio
async def test_get_pipeline_metrics_found(client: AsyncClient):
    """Test GET /metrics/pipelines/{id} returns breakdown"""
    # Seed pipeline with usage records
    response = await client.get(f"/metrics/pipelines/{pipeline_id}")
    assert response.status_code == 200
    data = response.json()
    assert "phase_breakdown" in data
    assert len(data["phase_breakdown"]) > 0
    
@pytest.mark.asyncio
async def test_get_pipeline_metrics_not_found(client: AsyncClient):
    """Test GET /metrics/pipelines/{id} returns 404 for invalid ID"""
    response = await client.get("/metrics/pipelines/invalid_id")
    assert response.status_code == 404
    
@pytest.mark.asyncio
async def test_get_pipeline_metrics_missing_epic(client: AsyncClient):
    """Test pipeline metrics handles missing epic description"""
    # Seed pipeline without epic artifact
    response = await client.get(f"/metrics/pipelines/{pipeline_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["epic_description"] is None
    
@pytest.mark.asyncio
async def test_performance_summary_1000_pipelines():
    """Soft performance test - logs warning if >2s"""
    # Seed 1000 pipelines
    import time
    start = time.time()
    response = await client.get("/metrics/summary")
    duration = time.time() - start
    
    if duration > 2.0:
        import logging
        logging.warning(f"Performance target missed: {duration}s > 2s")
    
    # Always pass - this is a soft target
    assert response.status_code == 200
```

**Reference:** ArchitectureSpec test_strategy.integration_tests, Story 175D-8

---

#### **Task C10: Integration Tests for HTML Templates**

**File:** `tests/integration/test_metrics_templates.py` (NEW)

**What to implement:**

6 integration tests for template rendering:

```python
@pytest.mark.asyncio
async def test_metrics_overview_renders(client: AsyncClient):
    """Test GET /metrics HTML renders successfully"""
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Metrics Dashboard" in response.text
    
@pytest.mark.asyncio
async def test_metrics_overview_empty_data(client: AsyncClient):
    """Test metrics overview handles zero metrics"""
    response = await client.get("/metrics")
    assert response.status_code == 200
    assert "$0.00" in response.text  # Total cost
    
@pytest.mark.asyncio
async def test_pipeline_detail_renders(client: AsyncClient):
    """Test GET /metrics/pipelines/{id} HTML renders"""
    # Seed pipeline
    response = await client.get(f"/metrics/pipelines/{pipeline_id}")
    assert response.status_code == 200
    assert "Pipeline Details" in response.text
    
@pytest.mark.asyncio
async def test_pipeline_detail_missing_epic_fallback(client: AsyncClient):
    """Test detail page shows '(no epic available)' for missing epic"""
    # Seed pipeline without epic
    response = await client.get(f"/metrics/pipelines/{pipeline_id}")
    assert "(no epic available)" in response.text
    
@pytest.mark.asyncio
async def test_indicator_green_recent_usage(client: AsyncClient):
    """Test live indicator shows green for recent usage"""
    # Seed usage record from 5 minutes ago
    response = await client.get("/metrics")
    assert 'bg-green-500' in response.text
    
@pytest.mark.asyncio
async def test_indicator_red_stale_usage(client: AsyncClient):
    """Test live indicator shows red for old usage"""
    # Seed usage record from 90 minutes ago
    response = await client.get("/metrics")
    assert 'bg-red-500' in response.text
```

**Reference:** ArchitectureSpec test_strategy.integration_tests

---

## Contracts & Data Shapes

**Critical:** These must match exactly between service, router, schemas, and templates.

### JSON Endpoints

**GET /metrics/summary:**
```json
{
  "total_pipelines": 42,
  "total_cost_usd": 12.50,
  "total_input_tokens": 150000,
  "total_output_tokens": 50000,
  "success_count": 38,
  "failure_count": 4
}
```
**Does NOT include `last_usage_timestamp`** - that's only in internal MetricsSummary for HTML templates.

**GET /metrics/pipelines/{id}:**
```json
{
  "pipeline_id": "pipe_123",
  "status": "completed",
  "current_phase": "commit",
  "epic_description": "Add metrics dashboard",
  "total_cost_usd": 0.45,
  "total_input_tokens": 12000,
  "total_output_tokens": 3000,
  "phase_breakdown": [
    {
      "phase_name": "pm_phase",
      "role_name": "pm",
      "input_tokens": 5000,
      "output_tokens": 1500,
      "cost_usd": 0.15,
      "execution_time_ms": 3200,
      "timestamp": "2025-12-06T10:30:00Z"
    }
  ]
}
```

### Template Contexts

**GET /metrics (HTML):**
```python
{
  "request": request,  # FastAPI Request
  "summary": MetricsSummary,  # Includes last_usage_timestamp
  "recent_pipelines": list[PipelineSummary],
  "daily_costs": list[DailyCost],
  "last_usage_minutes": int | None
}
```

**GET /metrics/pipelines/{id} (HTML):**
```python
{
  "request": request,
  "pipeline": PipelineMetrics  # Full breakdown
}
```

---

## Testing Plan

### Must-Have Tests (Blocking for Epic Completion)

**Unit Tests (36 total):**
- TokenMetricsService: 12 tests
- MetricsSchemas: 7 tests
- MetricsRouter: 8 tests
- Repository extensions: 9 tests

**Integration Tests (12 total):**
- JSON endpoints: 6 tests
- HTML templates: 6 tests

**Total:** 48 tests

### Test Data Requirements

Seed fixtures must include:
- 50 pipelines with statuses: 30 'completed', 10 'failed', 5 'error', 5 'in_progress'
- 200+ usage records distributed across pipelines
- At least 5 pipelines with no usage records
- At least 3 pipelines with missing epic artifacts
- Usage records from last 7 days (varied dates)
- At least 1 pipeline with full phase execution (pm → arch → ba → dev → qa → commit)

### Test Execution Order

1. **Unit tests first** (fast, no DB)
2. **Repository integration tests** (with test DB)
3. **Endpoint integration tests** (with FastAPI test client)
4. **Template integration tests** (full rendering)

### Performance Tests

**Soft targets (warning logs, not failures):**
- GET /metrics/summary: <2s for 1000 pipelines
- GET /metrics/pipelines/{id}: <2s for 50 phases
- GET /metrics HTML: <2s render time

Implement as:
```python
if duration > 2.0:
    logging.warning(f"Performance target missed: {duration}s")
# Always pass - don't fail CI
```

---

## Risks / Open Questions

### Identified Risks

1. **Epic Description Extraction**
   - **Risk:** Artifacts JSON structure may vary across pipeline versions
   - **Mitigation:** Robust JSON parsing with fallback to None
   - **Action:** Dev A should check existing pipeline artifacts to confirm structure

2. **Success/Failure Count Query Performance**
   - **Risk:** Separate COUNT queries for status may be slow on large datasets
   - **Mitigation:** Could combine into single query with CASE statement
   - **Action:** Start with separate queries (simpler), optimize if >2s threshold hit

3. **Daily Cost Date Range**
   - **Risk:** SQLite DATE() behavior in different locales
   - **Mitigation:** Explicitly documented as UTC in ADR-014
   - **Action:** Add test to verify DATE() returns expected format

4. **Chart.js CDN Reliability**
   - **Risk:** CDN outage breaks charts
   - **Mitigation:** Graceful fallback to table (tested in integration tests)
   - **Action:** Ensure fallback actually works in tests

### Open Questions (Need Clarification)

1. **Pipeline Status Values**
   - **Question:** What are ALL possible status values in the pipelines table?
   - **Why it matters:** Success/failure counts need to handle all statuses correctly
   - **Action:** Dev A should query existing DB or check model definition

2. **Artifacts JSON Schema**
   - **Question:** Exact path to epic description in artifacts JSON?
   - **Current assumption:** `artifacts["epic"]["description"]`
   - **Action:** Verify with existing data before implementing

3. **Auto-Refresh UX**
   - **Question:** Is 30-second auto-refresh acceptable or should we use meta refresh?
   - **Current decision:** Using `<meta http-equiv="refresh" content="30">`
   - **Action:** Dev C can implement, get operator feedback in testing

### No Blockers Identified

All components can be implemented in parallel once repository extensions are complete. Service depends on repos, router depends on service, templates depend on router contracts.

---

## Implementation Order

**Phase 1: Data Layer (Day 1)**
- Dev A: Repository extensions (Tasks A1, A2)
- Dev A: Internal dataclasses (Task A3)
- Dev C: Test fixtures and seed data setup

**Phase 2: Service Layer (Day 1-2)**
- Dev A: TokenMetricsService (Task A4)
- Dev A: Unit tests for service
- Dev C: Unit tests for repositories

**Phase 3: API Layer (Day 2)**
- Dev B: Pydantic schemas (Task B1)
- Dev B: MetricsRouter (Task B2)
- Dev B: Register router (Task B3)
- Dev C: Unit tests for schemas and router

**Phase 4: UI Layer (Day 2-3)**
- Dev C: All templates (Tasks C2-C5)
- Dev C: Integration tests for templates

**Phase 5: Integration & Testing (Day 3)**
- Dev C: Integration tests for endpoints (Tasks C9-C10)
- All: Run full test suite
- All: Performance validation
- All: Fix any issues

**Total Estimate:** 16 hours (matches epic estimate)

---

## Final Checklist

Before marking epic complete:

- [ ] All 48 tests passing
- [ ] GET /metrics/summary returns correct JSON shape
- [ ] GET /metrics/pipelines/{id} returns 404 for invalid ID
- [ ] GET /metrics HTML renders with data
- [ ] GET /metrics HTML renders with zero data
- [ ] Indicator shows correct color based on timestamp
- [ ] Chart.js loads and displays OR table fallback shows
- [ ] Missing epic descriptions show "(no epic available)"
- [ ] No authentication required on /metrics routes
- [ ] Router registered in main.py
- [ ] Templates directory created
- [ ] Performance targets met or warnings logged
- [ ] Success/failure counts calculated correctly
- [ ] Service layer never raises exceptions to router
- [ ] All ADRs followed (011-016)

---

**This implementation plan is ready for execution. All three developers have clear, independent tasks that integrate cleanly. No ambiguities, no scope creep, faithful to ArchitectureSpec and EpicSpec.**


# ✅ Implementation Plan - Final Adjustments Applied

## Critical Implementation Details (QA Feedback Incorporated)

---

### 1. Repository vs Service Error Contract - ENFORCED

**Updated Implementation Guidance:**

#### **Dev A - Repository Layer (STRICT RULE)**

**File:** `app/orchestrator_api/persistence/repositories/pipeline_prompt_usage_repository.py`

```python
def get_system_aggregates(self) -> dict:
    """
    Get system-wide aggregates.
    
    Returns zeros/None for empty table (NOT an error).
    Raises exception on genuine DB errors (connection, SQL syntax, etc.).
    
    CRITICAL: Do NOT catch exceptions here - let service layer handle them.
    """
    try:
        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT 
                        COALESCE(SUM(cost_usd), 0.0) as total_cost,
                        COALESCE(SUM(input_tokens), 0) as total_input,
                        COALESCE(SUM(output_tokens), 0) as total_output,
                        COUNT(*) as count,
                        MAX(created_at) as last_timestamp
                    FROM pipeline_prompt_usage
                """)
            ).fetchone()
            
            return {
                "total_cost": float(result.total_cost),
                "total_input_tokens": int(result.total_input),
                "total_output_tokens": int(result.total_output),
                "count": int(result.count),
                "last_timestamp": result.last_timestamp  # Can be None
            }
    except Exception as e:
        # Do NOT log here - let service layer handle logging
        # Do NOT return defaults here - raise to service
        raise  # Re-raise DB errors to service layer
```

**Key Points:**
- ✅ Returns zeros/None for empty tables (valid data, not error)
- ✅ Raises on DB connection errors, SQL errors, etc.
- ❌ Does NOT catch and swallow exceptions
- ❌ Does NOT log errors (service layer's job)

#### **Dev A - Service Layer (STRICT RULE)**

**File:** `app/orchestrator_api/services/token_metrics_service.py`

```python
import logging

logger = logging.getLogger(__name__)

class TokenMetricsService:
    def get_summary(self) -> MetricsSummary:
        """
        Get system-wide metrics.
        
        CRITICAL: Wraps ALL repository calls in try/except.
        Never raises exceptions to router layer.
        """
        try:
            # Get usage aggregates
            usage_repo = PipelinePromptUsageRepository()
            aggregates = usage_repo.get_system_aggregates()
            
            # Get pipeline status counts
            pipeline_repo = PipelineRepository()
            success_count = pipeline_repo.count_by_status('completed')
            failure_count = pipeline_repo.count_by_status_in(['failed', 'error'])
            
            return MetricsSummary(
                total_pipelines=aggregates["count"],
                total_cost_usd=aggregates["total_cost"],
                total_input_tokens=aggregates["total_input_tokens"],
                total_output_tokens=aggregates["total_output_tokens"],
                success_count=success_count,
                failure_count=failure_count,
                last_usage_timestamp=aggregates["last_timestamp"]
            )
            
        except Exception as e:
            # Log the error with full context
            logger.warning(f"Failed to get metrics summary: {type(e).__name__}: {e}")
            
            # Return safe defaults - never raise to router
            return MetricsSummary(
                total_pipelines=0,
                total_cost_usd=0.0,
                total_input_tokens=0,
                total_output_tokens=0,
                success_count=0,
                failure_count=0,
                last_usage_timestamp=None
            )
```

**Key Points:**
- ✅ Wraps EVERY repository call in try/except
- ✅ Logs errors with context (type + message)
- ✅ Returns safe defaults on ANY exception
- ❌ NEVER lets exceptions escape to router

---

### 2. Timezone & Date Handling - CLARIFIED

**Updated Implementation Guidance:**

#### **Dev A - Task A1 (Repository)**

**File:** `app/orchestrator_api/persistence/repositories/pipeline_prompt_usage_repository.py`

```python
def get_daily_aggregates(self, days: int) -> list[dict]:
    """
    Get daily cost aggregates for last N days.
    
    IMPORTANT: Uses database UTC timezone via DATE(created_at).
    Date boundaries are based on DB time, not application server time.
    
    This is acceptable for MVP operator tool (see ADR-014).
    """
    with get_db_session() as session:
        result = session.execute(
            text("""
                SELECT 
                    DATE(created_at) as date,
                    SUM(cost_usd) as cost
                FROM pipeline_prompt_usage
                WHERE created_at >= DATE('now', '-' || :days || ' days')
                GROUP BY DATE(created_at)
                ORDER BY date
            """),
            {"days": days}
        ).fetchall()
        
        return [
            {"date": row.date, "total_cost": float(row.cost)}
            for row in result
        ]
```

#### **Dev A - Task A4 (Service)**

**File:** `app/orchestrator_api/services/token_metrics_service.py`

```python
from datetime import datetime, timedelta, timezone

def get_daily_costs(self, days: int = 7) -> list[DailyCost]:
    """
    Get daily costs for last N days, filling missing dates with 0.0.
    
    IMPORTANT: Date range uses UTC to match database DATE() function.
    X-axis represents UTC calendar days, not local timezone.
    
    This is documented and acceptable for MVP (see ADR-014).
    """
    try:
        usage_repo = PipelinePromptUsageRepository()
        aggregates = usage_repo.get_daily_aggregates(days)
        
        # Generate complete date range in UTC
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days - 1)
        
        all_dates = [
            (start_date + timedelta(days=i)).isoformat()
            for i in range(days)
        ]
        
        # Merge with actual data
        data_map = {row["date"]: row["total_cost"] for row in aggregates}
        
        return [
            DailyCost(date=date, total_cost_usd=data_map.get(date, 0.0))
            for date in all_dates
        ]
        
    except Exception as e:
        logger.warning(f"Failed to get daily costs: {e}")
        return []
```

**Key Points:**
- ✅ Both DB and Python use UTC for date calculations
- ✅ Documented in code comments
- ✅ Acceptable for MVP operator tool
- 📝 Future enhancement: Add timezone conversion if needed

---

### 3. Service Construction & Dependency Injection - SPECIFIED

**Updated Implementation Guidance:**

#### **Dev A - Task A4 (Service Construction)**

**File:** `app/orchestrator_api/services/token_metrics_service.py`

**Option 1: Internal Construction (Recommended for MVP)**

```python
class TokenMetricsService:
    """
    Metrics service layer.
    
    Constructs repository instances internally using get_db_session().
    Simpler for MVP, still unit-testable via mocking repositories.
    """
    
    def __init__(self):
        # No dependencies injected - construct internally
        pass
    
    def get_summary(self) -> MetricsSummary:
        # Construct repos on each call (session managed by repo)
        usage_repo = PipelinePromptUsageRepository()
        pipeline_repo = PipelineRepository()
        
        try:
            # Use repos...
            pass
        except Exception as e:
            logger.warning(f"Failed to get summary: {e}")
            return MetricsSummary(...)
```

**Unit Testing:**
```python
@patch('app.orchestrator_api.services.token_metrics_service.PipelinePromptUsageRepository')
@patch('app.orchestrator_api.services.token_metrics_service.PipelineRepository')
def test_get_summary(mock_pipeline_repo, mock_usage_repo):
    service = TokenMetricsService()
    # Mock repo methods
    mock_usage_repo.return_value.get_system_aggregates.return_value = {...}
    # Test service behavior
```

**Option 2: Dependency Injection (More testable, more setup)**

```python
class TokenMetricsService:
    """
    Metrics service layer with injected dependencies.
    
    Better for testing (no patching), but requires more setup in router.
    """
    
    def __init__(
        self,
        usage_repo: PipelinePromptUsageRepository = None,
        pipeline_repo: PipelineRepository = None
    ):
        self.usage_repo = usage_repo or PipelinePromptUsageRepository()
        self.pipeline_repo = pipeline_repo or PipelineRepository()
```

**DECISION FOR 175D: Use Option 1 (Internal Construction)**
- Simpler implementation
- Standard Python mocking works fine
- Can refactor to DI later if needed

---

### 4. get_recent_pipelines Implementation - SPECIFIED

**Updated Implementation Guidance:**

#### **Dev A - Task A4 (Efficient Query Strategy)**

**File:** `app/orchestrator_api/services/token_metrics_service.py`

```python
def get_recent_pipelines(self, limit: int = 20) -> list[PipelineSummary]:
    """
    Get recent pipelines with aggregated usage.
    
    Implementation: Single DB query with subquery for aggregates.
    Avoids N+1 query pattern.
    """
    try:
        with get_db_session() as session:
            result = session.execute(
                text("""
                    SELECT 
                        p.id as pipeline_id,
                        p.status,
                        p.artifacts,
                        p.created_at,
                        COALESCE(u.total_cost, 0.0) as total_cost,
                        COALESCE(u.total_tokens, 0) as total_tokens
                    FROM pipelines p
                    LEFT JOIN (
                        SELECT 
                            pipeline_id,
                            SUM(cost_usd) as total_cost,
                            SUM(input_tokens + output_tokens) as total_tokens
                        FROM pipeline_prompt_usage
                        GROUP BY pipeline_id
                    ) u ON p.id = u.pipeline_id
                    ORDER BY p.created_at DESC
                    LIMIT :limit
                """),
                {"limit": limit}
            ).fetchall()
            
            pipelines = []
            for row in result:
                # Extract epic description (defensive)
                epic_description = None
                if row.artifacts:
                    try:
                        artifacts = json.loads(row.artifacts)
                        epic_description = artifacts.get("epic", {}).get("description")
                    except (json.JSONDecodeError, AttributeError):
                        pass
                
                pipelines.append(PipelineSummary(
                    pipeline_id=row.pipeline_id,
                    epic_description=epic_description,
                    status=row.status,
                    total_cost_usd=float(row.total_cost),
                    total_tokens=int(row.total_tokens),
                    created_at=row.created_at
                ))
            
            return pipelines
            
    except Exception as e:
        logger.warning(f"Failed to get recent pipelines: {e}")
        return []
```

**Key Points:**
- ✅ Single query with LEFT JOIN and subquery
- ✅ Avoids N+1 pattern
- ✅ Handles missing usage records (LEFT JOIN returns 0s)
- ✅ Defensive epic extraction with try/except

---

### 5. Template Paths - VERIFIED

**Updated Implementation Guidance:**

#### **Dev B - Task B2 (Router Setup)**

**File:** `app/orchestrator_api/routers/metrics.py`

```python
from pathlib import Path
from fastapi.templating import Jinja2Templates

# Construct template path relative to project root
TEMPLATE_DIR = Path(__file__).parent.parent / "templates"
templates = Jinja2Templates(directory=str(TEMPLATE_DIR))

# Verify directory exists on import
if not TEMPLATE_DIR.exists():
    import logging
    logging.error(f"Template directory not found: {TEMPLATE_DIR}")
```

**Template Include Paths:**
```html
<!-- In overview.html -->
{% include "metrics/_indicator.html" %}
{% include "metrics/_chart.html" %}
```

**Directory Structure (Verify This Exists):**
```
app/orchestrator_api/
├── routers/
│   └── metrics.py
├── templates/
│   └── metrics/
│       ├── overview.html
│       ├── detail.html
│       ├── _indicator.html
│       └── _chart.html
```

**Dev C - Task C1 (Pre-Implementation Check):**
```bash
# Before writing templates, verify FastAPI template setup:
cd app/orchestrator_api
ls -la templates/  # Should exist from previous work or create it

# Create metrics subdirectory:
mkdir -p templates/metrics
```

---

### 6. Test Fixtures & Async - STANDARDIZED

**Updated Implementation Guidance:**

#### **Dev C - Create Shared Test Fixtures**

**File:** `tests/conftest.py` (UPDATE)

```python
import pytest
from httpx import AsyncClient
from app.orchestrator_api.main import app

@pytest.fixture
async def client():
    """Async test client for integration tests"""
    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client

@pytest.fixture
def seed_metrics_data(test_db):
    """
    Seed test database with metrics test data.
    
    Creates:
    - 50 pipelines (30 completed, 10 failed, 5 error, 5 in_progress)
    - 200+ usage records
    - Various epic artifacts (some missing)
    - Dates spread across last 7 days
    """
    from datetime import datetime, timedelta
    from app.orchestrator_api.persistence.repositories.pipeline_repository import PipelineRepository
    from app.orchestrator_api.persistence.repositories.pipeline_prompt_usage_repository import PipelinePromptUsageRepository
    
    # Seed pipelines
    pipeline_repo = PipelineRepository()
    usage_repo = PipelinePromptUsageRepository()
    
    pipelines = []
    
    # 30 completed with epic
    for i in range(30):
        pipeline_id = f"pipe_completed_{i}"
        pipeline_repo.create(
            pipeline_id=pipeline_id,
            status="completed",
            current_phase="commit",
            artifacts={"epic": {"description": f"Test epic {i}"}}
        )
        pipelines.append(pipeline_id)
        
        # Add usage records for each phase
        for phase in ["pm", "arch", "ba", "dev", "qa", "commit"]:
            usage_repo.record_usage(
                pipeline_id=pipeline_id,
                prompt_id=f"prompt_{phase}",
                input_tokens=5000,
                output_tokens=1500,
                cost_usd=0.075,
                model="claude-sonnet-4",
                execution_time_ms=3000
            )
    
    # 10 failed (some with epic, some without)
    for i in range(10):
        pipeline_id = f"pipe_failed_{i}"
        artifacts = {"epic": {"description": f"Failed epic {i}"}} if i < 5 else {}
        pipeline_repo.create(
            pipeline_id=pipeline_id,
            status="failed",
            current_phase="dev",
            artifacts=artifacts
        )
    
    # 5 error (no epic)
    for i in range(5):
        pipeline_id = f"pipe_error_{i}"
        pipeline_repo.create(
            pipeline_id=pipeline_id,
            status="error",
            current_phase="pm",
            artifacts={}
        )
    
    # 5 in_progress (no usage records yet)
    for i in range(5):
        pipeline_id = f"pipe_progress_{i}"
        pipeline_repo.create(
            pipeline_id=pipeline_id,
            status="in_progress",
            current_phase="arch",
            artifacts={"epic": {"description": f"In progress epic {i}"}}
        )
    
    return pipelines
```

#### **Dev C - Performance Test Pattern**

**File:** `tests/integration/test_metrics_endpoints.py`

```python
import pytest
import time
import logging
from httpx import AsyncClient

logger = logging.getLogger(__name__)

@pytest.mark.asyncio
async def test_performance_summary_soft_target(client: AsyncClient, seed_large_dataset):
    """
    Soft performance test - logs warning if >2s, doesn't fail.
    
    Uses time.time() for simple duration measurement.
    Not a benchmark harness - just a monitoring aid.
    """
    # Seed 1000 pipelines (separate fixture)
    
    start = time.time()
    response = await client.get("/metrics/summary")
    duration = time.time() - start
    
    # Always assert success
    assert response.status_code == 200
    
    # Log warning if performance target missed (not a failure)
    if duration > 2.0:
        logger.warning(
            f"Performance soft target missed: "
            f"{duration:.2f}s > 2.0s for /metrics/summary"
        )
    else:
        logger.info(f"Performance OK: {duration:.2f}s for /metrics/summary")
```

---

### 7. Epic Description Extraction - PRE-VERIFIED

**Updated Implementation Guidance:**

#### **Dev A - PRE-TASK: Verify Artifacts Schema**

**Before implementing Task A2, run this verification:**

```python
# scripts/verify_artifacts_schema.py
"""
One-time verification script to check actual artifacts JSON structure.
Run before implementing epic description extraction.
"""
from app.orchestrator_api.persistence.database import get_db_session
from sqlalchemy import text
import json

with get_db_session() as session:
    result = session.execute(
        text("SELECT id, artifacts FROM pipelines WHERE artifacts IS NOT NULL LIMIT 10")
    ).fetchall()
    
    print("Artifacts JSON structure analysis:")
    print("=" * 60)
    
    for row in result:
        print(f"\nPipeline: {row.id}")
        try:
            artifacts = json.loads(row.artifacts) if isinstance(row.artifacts, str) else row.artifacts
            print(f"  Type: {type(artifacts)}")
            print(f"  Keys: {artifacts.keys() if isinstance(artifacts, dict) else 'N/A'}")
            
            # Try to find epic description
            epic_desc = None
            if isinstance(artifacts, dict):
                # Try common paths
                paths = [
                    ("artifacts['epic']['description']", artifacts.get("epic", {}).get("description")),
                    ("artifacts['epic']['epic_description']", artifacts.get("epic", {}).get("epic_description")),
                    ("artifacts['pm']['epic_description']", artifacts.get("pm", {}).get("epic_description")),
                    ("artifacts['description']", artifacts.get("description")),
                ]
                
                for path, value in paths:
                    if value:
                        print(f"  ✅ Found epic at: {path} = '{value[:50]}...'")
                        epic_desc = value
                        break
            
            if not epic_desc:
                print(f"  ❌ No epic description found")
                print(f"  Full structure: {json.dumps(artifacts, indent=2)[:200]}...")
                
        except Exception as e:
            print(f"  ❌ Error parsing: {e}")
    
    print("=" * 60)
```

**Run this script, then update extraction logic accordingly:**

#### **Dev A - Task A2 (Updated with defensive extraction)**

**File:** `app/orchestrator_api/persistence/repositories/pipeline_repository.py`

```python
import json
import logging

logger = logging.getLogger(__name__)

def get_pipeline_with_epic(self, pipeline_id: str) -> dict | None:
    """
    Get pipeline with epic description extracted from artifacts.
    
    Uses defensive extraction to handle varying artifacts structures.
    Returns None for epic_description if not found (valid state).
    """
    with get_db_session() as session:
        result = session.execute(
            text("""
                SELECT id, status, current_phase, artifacts, created_at
                FROM pipelines
                WHERE id = :pipeline_id
            """),
            {"pipeline_id": pipeline_id}
        ).fetchone()
        
        if not result:
            return None
        
        # Defensive epic description extraction
        epic_description = None
        if result.artifacts:
            try:
                # Parse JSON (may be string or already dict)
                if isinstance(result.artifacts, str):
                    artifacts = json.loads(result.artifacts)
                else:
                    artifacts = result.artifacts
                
                # Try multiple paths (adjust based on verification script output)
                if isinstance(artifacts, dict):
                    # Path 1: artifacts.epic.description (most common)
                    epic_description = artifacts.get("epic", {}).get("description")
                    
                    # Path 2: artifacts.epic.epic_description (alternative)
                    if not epic_description:
                        epic_description = artifacts.get("epic", {}).get("epic_description")
                    
                    # Path 3: artifacts.pm.epic_description (legacy)
                    if not epic_description:
                        epic_description = artifacts.get("pm", {}).get("epic_description")
                    
            except (json.JSONDecodeError, AttributeError, TypeError) as e:
                logger.debug(f"Failed to extract epic from {pipeline_id}: {e}")
                # epic_description remains None - this is valid
        
        return {
            "pipeline_id": result.id,
            "status": result.status,
            "current_phase": result.current_phase,
            "epic_description": epic_description,
            "created_at": result.created_at
        }
```

---

## Final Implementation Checklist

### Pre-Implementation (Day 0)
- [ ] **Dev A:** Run `verify_artifacts_schema.py` to confirm epic extraction paths
- [ ] **Dev A:** Verify DB has pipelines with status values (completed, failed, error, etc.)
- [ ] **Dev C:** Verify `app/orchestrator_api/templates/` directory exists
- [ ] **Dev C:** Create `templates/metrics/` subdirectory
- [ ] **All:** Review error handling contract (repos raise, service catches)

### Phase 1: Data Layer (Day 1 Morning)
- [ ] **Dev A:** Implement repository extensions with STRICT error contract
- [ ] **Dev A:** Create internal dataclasses
- [ ] **Dev C:** Create test fixtures with seed data

### Phase 2: Service Layer (Day 1 Afternoon)
- [ ] **Dev A:** Implement TokenMetricsService with comprehensive try/except
- [ ] **Dev A:** Verify UTC date handling in get_daily_costs
- [ ] **Dev A:** Write 12 unit tests for service
- [ ] **Dev C:** Write 9 unit tests for repositories

### Phase 3: API Layer (Day 2 Morning)
- [ ] **Dev B:** Create Pydantic schemas (excluding last_usage_timestamp from JSON)
- [ ] **Dev B:** Implement MetricsRouter with internal→external type conversion
- [ ] **Dev B:** Register router in main.py (no auth)
- [ ] **Dev C:** Write 7 schema tests + 8 router tests

### Phase 4: UI Layer (Day 2 Afternoon)
- [ ] **Dev C:** Implement all 4 templates with defensive fallbacks
- [ ] **Dev C:** Verify Chart.js CDN fallback mechanism
- [ ] **Dev C:** Test template rendering with empty/full data

### Phase 5: Integration (Day 3)
- [ ] **Dev C:** Write 12 integration tests (6 JSON + 6 HTML)
- [ ] **All:** Run full test suite (48 tests)
- [ ] **All:** Verify performance soft targets
- [ ] **All:** Test live indicator with various timestamps
- [ ] **All:** Test missing epic fallbacks

### Final Verification
- [ ] All 48 tests passing
- [ ] Service layer catches ALL exceptions (verify logs)
- [ ] Repositories raise on DB errors (don't swallow)
- [ ] JSON responses exclude last_usage_timestamp
- [ ] HTML templates receive full internal types
- [ ] Chart fallback works
- [ ] Missing epics show "(no epic available)"
- [ ] Success/failure counts correct
- [ ] UTC dates documented and working

---

## EXECUTE THIS PLAN

All edge cases addressed. Error contracts enforced. Type boundaries clear. Dependencies specified. Test patterns standardized.

**No more clarifications needed. Begin implementation.**