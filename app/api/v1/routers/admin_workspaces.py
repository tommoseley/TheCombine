"""
Admin Workspaces API endpoints.

Per ADR-044 WS-044-03, these endpoints provide workspace-scoped
editing operations for configuration artifacts.

This module composes sub-routers for lifecycle, artifact, and scaffold
operations. All endpoint paths are preserved via prefix-free sub-routers.
"""

from fastapi import APIRouter

from app.api.v1.routers.admin_workspaces_lifecycle import router as lifecycle_router
from app.api.v1.routers.admin_workspaces_artifacts import router as artifacts_router
from app.api.v1.routers.admin_workspaces_scaffold import router as scaffold_router


router = APIRouter(prefix="/admin/workspaces", tags=["admin-workspaces"])

router.include_router(lifecycle_router)
router.include_router(artifacts_router)
router.include_router(scaffold_router)
