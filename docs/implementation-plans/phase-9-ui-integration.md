# Phase 9: UI Integration & End-to-End Testing

## Overview

Phase 9 connects the UI to the new API layer and validates the complete system with end-to-end tests. This phase brings together all components into a working user-facing application.

## Goals

1. **UI Execution Integration**: Connect UI to execution APIs with real-time progress
2. **Document Viewer**: Display generated documents in the UI
3. **Cost Dashboard**: Show telemetry and cost information
4. **E2E Testing**: Validate complete workflows from UI to LLM
5. **Error Handling**: Graceful error display and recovery

## Timeline: 5 Days

| Day | Focus | Estimated Tests |
|-----|-------|-----------------|
| 1 | Execution UI components | 12 |
| 2 | Real-time progress display | 10 |
| 3 | Document viewer & history | 10 |
| 4 | Cost dashboard | 8 |
| 5 | E2E integration tests | 10 |
| **Total** | | **~50** |

**Target: 839 tests (789 + 50)**

---

## Day 1: Execution UI Components

### Deliverables

1. **Execution Start Form** (app/ui/templates/executions/start.html)
   - Workflow selection dropdown
   - Project/scope selection
   - Initial input form
   - Start button with loading state

2. **Execution List Page** (app/ui/templates/executions/list.html)
   - Table of executions with status badges
   - Filter by workflow, status
   - Links to execution detail
   - Cancel button for active executions

3. **Execution Detail Page** (app/ui/templates/executions/detail.html)
   - Current status with progress indicator
   - Step list with status icons
   - Clarification form when needed
   - Document links when complete

4. **UI Router Updates** (app/ui/routers/executions.py)

```python
@router.get("/executions")
async def list_executions(request: Request):
    """List all executions."""
    ...

@router.get("/executions/new")
async def new_execution(request: Request):
    """Show execution start form."""
    ...

@router.post("/executions/start")
async def start_execution(request: Request):
    """Start a new execution."""
    ...

@router.get("/executions/{execution_id}")
async def execution_detail(request: Request, execution_id: str):
    """Show execution details."""
    ...
```

### Tests (12)
- Execution list page renders
- Execution list shows all executions
- Start form displays workflows
- Start form submits successfully
- Detail page shows status
- Detail page shows steps
- Cancel button works
- Filter by status works

---

## Day 2: Real-Time Progress Display

### Deliverables

1. **SSE Client Integration** (app/ui/static/js/execution-progress.js)

```javascript
class ExecutionProgress {
    constructor(executionId, onEvent) {
        this.executionId = executionId;
        this.onEvent = onEvent;
        this.eventSource = null;
    }
    
    connect() {
        this.eventSource = new EventSource(
            `/api/v1/executions/${this.executionId}/stream`
        );
        
        this.eventSource.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.onEvent(data);
        };
        
        this.eventSource.onerror = () => {
            this.reconnect();
        };
    }
    
    disconnect() {
        if (this.eventSource) {
            this.eventSource.close();
        }
    }
}
```

2. **Progress Component** (HTMX partial)
   - Step progress bar
   - Current step highlight
   - Animated status transitions
   - Time elapsed display

3. **Clarification Modal**
   - Display questions from LLM
   - Input fields for answers
   - Submit and continue

4. **Completion Handler**
   - Success notification
   - Link to generated documents
   - Cost summary display

### Tests (10)
- SSE connection establishes
- Progress updates display
- Step status changes animate
- Clarification modal appears
- Clarification submission works
- Completion notification shows
- Error state displays
- Reconnection on disconnect
- Time elapsed updates
- Cancel during execution

---

## Day 3: Document Viewer & History

### Deliverables

1. **Document List Page** (app/ui/templates/documents/list.html)
   - Filter by scope and type
   - Version indicator
   - Status badges (draft/active/stale)
   - Quick preview on hover

2. **Document Detail Page** (app/ui/templates/documents/detail.html)
   - Full content display
   - JSON pretty-printing
   - Metadata sidebar
   - Version history link

3. **Version History Page** (app/ui/templates/documents/versions.html)
   - All versions listed
   - Diff view between versions
   - Restore previous version

4. **Document UI Router** (app/ui/routers/documents.py)

```python
@router.get("/documents")
async def list_documents(request: Request):
    """List documents with filters."""
    ...

@router.get("/documents/{document_id}")
async def document_detail(request: Request, document_id: str):
    """Show document detail."""
    ...

@router.get("/documents/{document_id}/versions")
async def document_versions(request: Request, document_id: str):
    """Show version history."""
    ...
```

### Tests (10)
- Document list renders
- Filter by scope works
- Filter by type works
- Document detail shows content
- JSON content formatted
- Metadata displays correctly
- Version history lists all
- Version comparison works
- Status badges correct
- Empty state handled

---

## Day 4: Cost Dashboard

### Deliverables

1. **Dashboard Page** (app/ui/templates/dashboard/index.html)
   - Total cost summary card
   - Execution count metrics
   - Success rate gauge
   - Token usage chart

2. **Cost Breakdown Component**
   - By workflow pie chart
   - By model bar chart
   - Daily trend line chart
   - Date range selector

3. **Execution Cost Detail**
   - Per-step cost breakdown
   - Token counts per step
   - Model used per step
   - Latency metrics

4. **Dashboard Router** (app/ui/routers/dashboard.py)

```python
@router.get("/dashboard")
async def dashboard(request: Request):
    """Show main dashboard."""
    ...

@router.get("/dashboard/costs")
async def cost_dashboard(request: Request):
    """Show detailed cost dashboard."""
    ...

@router.get("/dashboard/api/summary")
async def dashboard_summary_api(request: Request):
    """API for dashboard data (HTMX)."""
    ...
```

5. **Chart Integration**
   - Chart.js for visualizations
   - HTMX for dynamic updates
   - Date range filtering

### Tests (8)
- Dashboard page renders
- Summary cards display data
- Cost breakdown shows
- Date filter works
- Charts render correctly
- Empty state handled
- Execution detail costs
- Token usage accurate

---

## Day 5: E2E Integration Tests

### Deliverables

1. **Full Workflow E2E Test**

```python
@pytest.mark.e2e
class TestFullWorkflowE2E:
    async def test_strategy_workflow_complete(self):
        """Test complete strategy workflow from UI to documents."""
        # 1. Start execution via UI
        # 2. Monitor progress via SSE
        # 3. Handle clarification if needed
        # 4. Verify documents created
        # 5. Check costs recorded
        # 6. Verify UI shows completion
        ...
```

2. **UI Integration Tests**

```python
class TestUIIntegration:
    def test_execution_list_shows_real_data(self):
        """UI shows actual executions from API."""
        ...
    
    def test_document_viewer_shows_content(self):
        """Document viewer displays real document content."""
        ...
    
    def test_dashboard_reflects_telemetry(self):
        """Dashboard shows actual telemetry data."""
        ...
```

3. **Error Handling Tests**

```python
class TestErrorHandling:
    def test_api_error_displays_gracefully(self):
        """API errors show user-friendly messages."""
        ...
    
    def test_sse_reconnection_works(self):
        """SSE reconnects after disconnect."""
        ...
    
    def test_invalid_execution_shows_404(self):
        """Invalid execution ID shows proper error."""
        ...
```

4. **Performance Tests**

```python
class TestPerformance:
    def test_execution_list_loads_quickly(self):
        """Execution list loads within acceptable time."""
        ...
    
    def test_sse_latency_acceptable(self):
        """SSE events arrive within latency budget."""
        ...
```

### Tests (10)
- Full strategy workflow E2E
- Execution list integration
- Document viewer integration
- Dashboard integration
- API error handling
- SSE reconnection
- Invalid ID handling
- Execution cancellation E2E
- Clarification flow E2E
- Cost tracking E2E

---

## File Structure

```
app/ui/
├── routers/
│   ├── executions.py      # Execution UI routes
│   ├── documents.py       # Document UI routes (new)
│   └── dashboard.py       # Dashboard routes (new)
├── templates/
│   ├── executions/
│   │   ├── list.html
│   │   ├── detail.html
│   │   ├── start.html
│   │   └── partials/
│   │       ├── progress.html
│   │       ├── steps.html
│   │       └── clarification.html
│   ├── documents/
│   │   ├── list.html
│   │   ├── detail.html
│   │   └── versions.html
│   └── dashboard/
│       ├── index.html
│       ├── costs.html
│       └── partials/
│           ├── summary.html
│           └── charts.html
└── static/
    └── js/
        ├── execution-progress.js
        └── charts.js

tests/
├── ui/
│   ├── test_executions_ui.py
│   ├── test_documents_ui.py
│   └── test_dashboard_ui.py
├── e2e/
│   ├── test_full_workflow.py
│   ├── test_error_handling.py
│   └── test_performance.py
└── integration/
    └── test_ui_api_integration.py
```

---

## UI Components Summary

### Execution Pages
| Page | URL | Description |
|------|-----|-------------|
| List | /executions | All executions with filters |
| Start | /executions/new | Start new execution form |
| Detail | /executions/{id} | Execution status and progress |

### Document Pages
| Page | URL | Description |
|------|-----|-------------|
| List | /documents | All documents with filters |
| Detail | /documents/{id} | Full document content |
| Versions | /documents/{id}/versions | Version history |

### Dashboard Pages
| Page | URL | Description |
|------|-----|-------------|
| Main | /dashboard | Overview metrics |
| Costs | /dashboard/costs | Detailed cost breakdown |

---

## Success Criteria

1. User can start a workflow execution from UI
2. Real-time progress displays via SSE
3. Clarification questions handled in UI
4. Generated documents viewable in UI
5. Cost dashboard shows accurate telemetry
6. All E2E tests pass
7. 839+ tests passing

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| SSE browser compatibility | Fallback to polling |
| Long execution timeouts | Progress persistence, reconnection |
| Large document rendering | Pagination, lazy loading |
| Chart performance | Client-side caching, aggregation |
| Test flakiness | Retry logic, deterministic mocks |

---

## Dependencies

- Phase 7: Execution engine (complete)
- Phase 8: API layer (complete)
- HTMX for dynamic updates
- Chart.js for visualizations
- Existing UI framework (Tailwind, Jinja2)

---

## Post-Phase 9

With Phase 9 complete, the system will have:
- Full UI for workflow execution
- Real-time progress monitoring
- Document management
- Cost tracking dashboard
- Comprehensive E2E test coverage

Next steps could include:
- Phase 10: Production hardening & deployment
- Phase 11: Multi-tenant support
- Phase 12: Advanced workflow features
