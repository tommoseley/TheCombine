# Phase 4 Implementation Plan: UI Integration

**Objective:** Build HTMX-powered web UI for workflow management, execution monitoring, and human interaction flows.

**Starting Point:** 340 tests passing (Phase 3 complete)
**Target:** ~50 new tests → 390 total

---

## Overview

Phase 4 connects the HTTP API layer (Phase 3) to a user-facing web interface. Using HTMX for dynamic updates and following The Combine's "Calm Authority" design philosophy, we'll create a workbench-style UI optimized for long work sessions.

---

## Architecture

```
app/ui/
├── templates/
│   ├── base.html              # Base layout with navigation
│   ├── components/
│   │   ├── workflow_card.html     # Workflow summary card
│   │   ├── execution_status.html  # Execution status display
│   │   ├── step_progress.html     # Step progress indicator
│   │   ├── acceptance_form.html   # Accept/reject form
│   │   ├── clarification_form.html # Q&A form
│   │   └── document_preview.html  # Document content preview
│   ├── pages/
│   │   ├── dashboard.html         # Main dashboard
│   │   ├── workflows.html         # Workflow list
│   │   ├── workflow_detail.html   # Single workflow view
│   │   ├── executions.html        # Execution list
│   │   └── execution_detail.html  # Single execution view
│   └── partials/
│       ├── execution_list.html    # HTMX partial for list updates
│       ├── execution_row.html     # Single execution row
│       └── status_badge.html      # Status indicator
├── routers/
│   ├── pages.py               # Full page renders
│   ├── partials.py            # HTMX partial responses
│   └── __init__.py
├── static/
│   ├── css/
│   │   └── styles.css         # Tailwind + custom styles
│   └── js/
│       └── websocket.js       # WebSocket client for live updates
└── __init__.py
```

---

## Day-by-Day Plan

### Day 1: Base Layout & Dashboard (8 tests)
**Goal:** Establish base templates and dashboard page

**Templates:**
- `base.html` - Navigation, header, main content area
- `dashboard.html` - Overview with recent executions, workflow shortcuts

**Routes:**
- `GET /` → Dashboard
- `GET /dashboard` → Dashboard (alias)

**Tests:**
1. Dashboard renders successfully
2. Dashboard shows navigation
3. Dashboard shows recent executions section
4. Dashboard shows workflow shortcuts
5. Base template includes HTMX script
6. Base template includes WebSocket script
7. Navigation links are correct
8. Page title is set correctly

---

### Day 2: Workflow Pages (10 tests)
**Goal:** Workflow listing and detail pages

**Templates:**
- `workflows.html` - List of available workflows
- `workflow_detail.html` - Single workflow with steps, scopes, doc types
- `workflow_card.html` - Reusable workflow summary component

**Routes:**
- `GET /workflows` → Workflow list page
- `GET /workflows/{id}` → Workflow detail page
- `POST /workflows/{id}/start` → Start workflow (HTMX, redirects to execution)

**Tests:**
1. Workflow list page renders
2. Workflow list shows all workflows
3. Workflow card displays name and description
4. Workflow card shows step count
5. Workflow detail page renders
6. Workflow detail shows scopes
7. Workflow detail shows document types
8. Workflow detail shows steps
9. Start workflow button exists
10. Start workflow creates execution and redirects

---

### Day 3: Execution Pages (10 tests)
**Goal:** Execution listing and detail pages with live updates

**Templates:**
- `executions.html` - List with filters
- `execution_detail.html` - Full execution view with step progress
- `execution_status.html` - Status component with real-time updates
- `step_progress.html` - Visual step progress indicator

**Routes:**
- `GET /executions` → Execution list page
- `GET /executions?workflow_id=X&status=Y` → Filtered list
- `GET /executions/{id}` → Execution detail page
- `GET /partials/executions` → HTMX partial for list refresh
- `GET /partials/executions/{id}/status` → HTMX partial for status updates

**Tests:**
1. Execution list page renders
2. Execution list shows all executions
3. Execution list supports workflow filter
4. Execution list supports status filter
5. Execution detail page renders
6. Execution detail shows current step
7. Execution detail shows step progress
8. Status partial returns correct HTML
9. HTMX polling attribute present
10. Cancel button appears for running executions

---

### Day 4: Human Interaction Forms (10 tests)
**Goal:** Acceptance and clarification UI flows

**Templates:**
- `acceptance_form.html` - Accept/reject with comment
- `clarification_form.html` - Dynamic question/answer form
- `document_preview.html` - Preview document awaiting acceptance

**Routes:**
- `GET /executions/{id}/acceptance` → Acceptance form page
- `POST /executions/{id}/acceptance` → Submit acceptance (HTMX)
- `GET /executions/{id}/clarification` → Clarification form page
- `POST /executions/{id}/clarification` → Submit answers (HTMX)

**Tests:**
1. Acceptance form renders when waiting
2. Acceptance form shows document preview
3. Accept button submits correctly
4. Reject button submits correctly
5. Comment field is optional
6. Clarification form renders when waiting
7. Clarification form shows questions
8. Answer submission works
9. Form redirects after success
10. Wrong state shows error message

---

### Day 5: WebSocket Integration & Polish (12 tests)
**Goal:** Real-time updates and UI polish

**Features:**
- WebSocket client auto-connects on execution detail page
- Live status updates without polling
- Toast notifications for events
- Loading states and transitions

**JavaScript:**
- `websocket.js` - Connection management, event handling, DOM updates

**Tests:**
1. WebSocket script loads on execution page
2. WebSocket connects to correct endpoint
3. Step started event updates UI
4. Step completed event updates UI
5. Waiting acceptance event shows form
6. Waiting clarification event shows form
7. Completed event shows success state
8. Failed event shows error state
9. Connection lost shows reconnect message
10. Reconnect attempts on disconnect
11. Multiple executions can be viewed
12. Page works without JavaScript (graceful degradation)

---

## Component Specifications

### Status Badge
```html
<span class="status-badge status-{status}">
  {status_label}
</span>
```
Colors:
- `pending` → gray
- `running` → blue (animated pulse)
- `waiting_acceptance` → yellow
- `waiting_clarification` → yellow
- `completed` → green
- `failed` → red
- `cancelled` → gray

### Step Progress
```html
<div class="step-progress">
  <div class="step completed">✓ Discovery</div>
  <div class="step current">→ Analysis</div>
  <div class="step pending">○ Review</div>
</div>
```

### Execution Row (HTMX partial)
```html
<tr hx-get="/partials/executions/{id}/row" 
    hx-trigger="every 5s"
    hx-swap="outerHTML">
  <td>{execution_id}</td>
  <td>{workflow_name}</td>
  <td><span class="status-badge">{status}</span></td>
  <td>{started_at}</td>
  <td><a href="/executions/{id}">View</a></td>
</tr>
```

---

## HTMX Patterns

### Polling for Updates
```html
<div hx-get="/partials/executions/{id}/status"
     hx-trigger="every 3s"
     hx-swap="innerHTML">
  <!-- Status content -->
</div>
```

### Form Submission
```html
<form hx-post="/executions/{id}/acceptance"
      hx-target="#result"
      hx-swap="innerHTML">
  <input type="hidden" name="accepted" value="true">
  <textarea name="comment"></textarea>
  <button type="submit">Approve</button>
</form>
```

### WebSocket Events (via htmx-ws extension)
```html
<div hx-ext="ws"
     ws-connect="/api/v1/ws/executions/{id}">
  <div id="status" hx-swap-oob="true">
    <!-- Updated by WebSocket -->
  </div>
</div>
```

---

## Design Tokens (Calm Authority)

```css
:root {
  /* Colors */
  --color-bg: #1a1a2e;
  --color-surface: #16213e;
  --color-primary: #4a90d9;
  --color-success: #10b981;
  --color-warning: #f59e0b;
  --color-error: #ef4444;
  --color-text: #e2e8f0;
  --color-text-muted: #94a3b8;
  
  /* Spacing */
  --space-xs: 0.25rem;
  --space-sm: 0.5rem;
  --space-md: 1rem;
  --space-lg: 1.5rem;
  --space-xl: 2rem;
  
  /* Typography */
  --font-mono: 'JetBrains Mono', monospace;
  --font-sans: 'Inter', sans-serif;
}
```

---

## Test Infrastructure

### Template Testing
```python
from fastapi.testclient import TestClient

def test_dashboard_renders(client: TestClient):
    response = client.get("/")
    assert response.status_code == 200
    assert "Dashboard" in response.text

def test_execution_detail_shows_status(client: TestClient):
    # Create execution via API
    exec_id = create_test_execution(client)
    
    response = client.get(f"/executions/{exec_id}")
    assert response.status_code == 200
    assert "running" in response.text
```

### HTMX Partial Testing
```python
def test_status_partial_returns_html(client: TestClient):
    exec_id = create_test_execution(client)
    
    response = client.get(
        f"/partials/executions/{exec_id}/status",
        headers={"HX-Request": "true"}
    )
    assert response.status_code == 200
    assert "status-badge" in response.text
```

---

## File Summary

| Day | New Files | Tests |
|-----|-----------|-------|
| 1 | base.html, dashboard.html, pages.py | 8 |
| 2 | workflows.html, workflow_detail.html, workflow_card.html | 10 |
| 3 | executions.html, execution_detail.html, partials.py | 10 |
| 4 | acceptance_form.html, clarification_form.html | 10 |
| 5 | websocket.js, styles.css | 12 |

**Total: ~50 tests**

---

## Dependencies

```
jinja2>=3.1.0      # Already installed (FastAPI dependency)
python-multipart   # Form handling (may need to add)
```

No new external dependencies required - using FastAPI's built-in Jinja2 support.

---

## Success Criteria

1. All 50 new tests pass (390 total)
2. Dashboard accessible at `/`
3. Workflows viewable and startable
4. Executions trackable with live updates
5. Acceptance/clarification forms functional
6. WebSocket provides real-time updates
7. UI follows Calm Authority design
8. Graceful degradation without JavaScript
