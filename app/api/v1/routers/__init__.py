"""API routers."""

from app.api.v1.routers.workflows import router as workflows_router
from app.api.v1.routers.executions import router as executions_router
from app.api.v1.routers.websocket import router as websocket_router
from app.api.v1.routers.sse import SSERouter, sse_router
from app.api.v1.routers.documents import router as documents_router
from app.api.v1.routers.telemetry import router as telemetry_router
from app.api.v1.routers.document_workflows import router as document_workflows_router
from app.api.v1.routers.interrupts import router as interrupts_router
from app.api.v1.routers.admin_workbench import router as admin_workbench_router
from app.api.v1.routers.admin_git import router as admin_git_router
from app.api.v1.routers.admin_validation import router as admin_validation_router


__all__ = [
    "workflows_router",
    "executions_router",
    "websocket_router",
    "SSERouter",
    "sse_router",
    "documents_router",
    "telemetry_router",
    "document_workflows_router",
    "interrupts_router",
    "admin_workbench_router",
    "admin_git_router",
    "admin_validation_router",
]
