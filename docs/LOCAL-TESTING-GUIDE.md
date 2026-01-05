# Local User Testing Guide

## Prerequisites

1. **PostgreSQL** running locally (or via Docker)
2. **Python 3.11+** with virtual environment
3. **.env** file configured

## Quick Start

### Option 1: Docker for Database Only

```bash
# Start just the database
docker-compose up -d db

# Wait for it to be ready
docker-compose logs -f db
# Look for "database system is ready to accept connections"

# Run the app locally
python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
```

### Option 2: Full Docker

```bash
docker-compose up -d
```

### Option 3: Local PostgreSQL

If you have PostgreSQL installed locally:

```bash
# Ensure DATABASE_URL in .env points to your local DB
# DATABASE_URL=postgresql://combine:combine@localhost:5432/combine

# Run migrations
alembic upgrade head

# Start the app
python -m uvicorn app.api.main:app --reload
```

## Access Points

| URL | Description |
|-----|-------------|
| http://localhost:8000 | Home Dashboard |
| http://localhost:8000/docs | API Documentation (Swagger) |
| http://localhost:8000/projects | Project List |
| http://localhost:8000/api/documents/types | Document Types (API) |
| http://localhost:8000/health | Health Check |
| http://localhost:8000/health/ready | Readiness Check |
| http://localhost:8000/health/detailed | Detailed Health |

## Testing Checklist

### 1. Basic Health
- [ ] Open http://localhost:8000/health - should return `{"status": "healthy"}`
- [ ] Open http://localhost:8000/health/ready - should show database connected

### 2. Authentication
- [ ] Click "Sign in with Google" - completes OAuth flow
- [ ] Click "Sign in with Microsoft" - completes OAuth flow
- [ ] User session persists across page refreshes

### 3. Workflows
- [ ] View workflow list at /workflows
- [ ] Click a workflow to see details
- [ ] Start a workflow execution

### 4. Execution Flow
- [ ] Start an execution from a workflow
- [ ] Watch real-time progress updates (SSE)
- [ ] Respond to clarification questions (if any)
- [ ] Accept/reject documents at quality gates
- [ ] View completed execution details

### 5. Documents
- [ ] Browse documents at /documents
- [ ] Filter by scope/type
- [ ] View document details
- [ ] Check version history

### 6. Cost Dashboard
- [ ] View /dashboard/costs
- [ ] Verify cost summaries
- [ ] Check daily breakdown chart
- [ ] Test period selection (7/14/30/90 days)

### 7. Error Handling
- [ ] Navigate to non-existent page - shows error page
- [ ] API 404 returns proper JSON error
- [ ] Invalid form submission shows validation errors

## Test Scenarios

### Scenario 1: Complete Workflow Execution
1. Go to /workflows
2. Click "Strategy Document" workflow
3. Click "Start Execution"
4. Watch progress via SSE updates
5. Answer any clarification questions
6. Accept documents at quality gates
7. Verify completed documents in /documents

### Scenario 2: Cancel Execution
1. Start a new execution
2. While running, click "Cancel"
3. Verify status changes to "cancelled"
4. Verify no further LLM calls

### Scenario 3: Reject Document
1. Start execution
2. At quality gate, click "Reject" with comment
3. Verify execution handles rejection appropriately

## Troubleshooting

### App Won't Start
```bash
# Check environment
python -c "from app.core.config import settings; print(settings.DATABASE_URL)"

# Check database connection
python -c "from app.core.database import engine; print(engine.url)"
```

### OAuth Errors
- Verify GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env
- Check redirect URI matches: http://localhost:8000/auth/google/callback

### No Workflows Showing
```bash
# Check workflow loading
python -c "from app.execution.workflow_loader import WorkflowLoader; print(WorkflowLoader().list_workflows())"
```

### Database Errors
```bash
# Run migrations
alembic upgrade head

# Check current version
alembic current
```

## Collecting Feedback

During testing, note:
1. **Bugs** - Unexpected behavior, errors
2. **UX Issues** - Confusing flows, unclear UI
3. **Performance** - Slow responses, timeouts
4. **Missing Features** - Expected functionality not present

## Logs

Watch application logs for errors:
```bash
# If running with uvicorn
# Logs appear in terminal

# If running with docker
docker-compose logs -f app
```