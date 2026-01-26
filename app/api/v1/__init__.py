"""API v1 module."""

from fastapi import APIRouter

from app.api.v1.routers import (
    workflows_router,
    executions_router,
    websocket_router,
    document_workflows_router,
)
from app.api.v1.routers.production import router as production_router
from app.api.v1.routers.projects import router as projects_router
from app.api.v1.routers.dashboard import router as dashboard_router
from app.api.v1.routers.interrupts import router as interrupts_router


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


__all__ = ["api_router"]
