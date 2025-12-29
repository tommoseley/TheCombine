"""
Main UI Router for The Combine
Combines all route modules - NO PREFIX (routes at root level)

Template Pattern V2:
- Each route module handles its own domain
- Single routes with HX-Request detection for full page vs HTMX partial
- Shared template utilities in shared.py

Route Structure:
- home_routes: Home page (/)
- project_routes: Project CRUD and listing (/projects/*)
- document_routes: Document viewing and building (/projects/{id}/documents/*)
- epic_routes: Epic management
- story_routes: Story management
- search_routes: Global search
- mentor_routes: Mentor interactions (legacy)
- debug_routes: Debug utilities
"""

from fastapi import APIRouter

from .home_routes import router as home_router
from .project_routes import router as project_router
from .document_routes import router as document_router  # Replaces architecture_routes
from .search_routes import router as search_router
from .debug_routes import router as debug_router

# Create main router WITHOUT prefix - routes at root level
router = APIRouter(tags=["web-ui"])

# Include all sub-routers
router.include_router(home_router)
router.include_router(project_router)
router.include_router(document_router)  # Replaces architecture_router
router.include_router(search_router)
router.include_router(debug_router)