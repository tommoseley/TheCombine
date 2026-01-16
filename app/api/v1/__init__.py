"""API v1 module."""

from fastapi import APIRouter

from app.api.v1.routers import (
    workflows_router,
    executions_router,
    websocket_router,
    document_workflows_router,
)


# Create main v1 router
api_router = APIRouter(prefix="/api/v1")

# Include sub-routers
api_router.include_router(workflows_router)
api_router.include_router(executions_router)
api_router.include_router(websocket_router)
api_router.include_router(document_workflows_router)


__all__ = ["api_router"]
