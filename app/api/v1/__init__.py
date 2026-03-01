"""API v1 module."""

from fastapi import APIRouter

from app.api.v1.routers import (
    workflows_router,
    executions_router,
    websocket_router,
    document_workflows_router,
    telemetry_router,
    admin_workbench_router,
    admin_git_router,
    admin_validation_router,
    admin_releases_router,
    admin_preview_router,
    admin_workspaces_router,
)
from app.api.v1.routers.production import router as production_router
from app.api.v1.routers.projects import router as projects_router
from app.api.v1.routers.dashboard import router as dashboard_router
from app.api.v1.routers.interrupts import router as interrupts_router
from app.api.v1.routers.intake import router as intake_router
from app.api.v1.routers.intents import router as intents_router
from app.api.v1.routers.metrics import router as metrics_router
from app.api.v1.routers.work_binder import router as work_binder_router


# Create main v1 router
api_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_router.include_router(workflows_router)
api_router.include_router(executions_router)
api_router.include_router(websocket_router)
api_router.include_router(document_workflows_router)
api_router.include_router(production_router)
api_router.include_router(projects_router)
api_router.include_router(dashboard_router)
api_router.include_router(interrupts_router)
api_router.include_router(intake_router)
api_router.include_router(intents_router)  # WS-BCP-001: Intent Intake
api_router.include_router(telemetry_router)  # WS-ADMIN-RECONCILE-001: Cost tracking
api_router.include_router(admin_workbench_router)  # ADR-044: Admin Workbench
api_router.include_router(admin_git_router)  # ADR-044 Addendum A: Git UX
api_router.include_router(admin_validation_router)  # ADR-044 WS-044-08: Governance Guardrails
api_router.include_router(admin_releases_router)  # ADR-044 WS-044-07: Release & Rollback Management
api_router.include_router(admin_preview_router)  # ADR-044 WS-044-06: Preview & Dry-Run Engine
api_router.include_router(admin_workspaces_router)  # ADR-044 WS-044-03: Prompt Editor Workspaces
api_router.include_router(metrics_router)  # WS-METRICS-001: Execution Metrics
api_router.include_router(work_binder_router)  # WP-WB-001: Work Binder


__all__ = ["api_router"]
