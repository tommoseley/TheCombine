"""
Main UI Router for The Combine
Combines all route modules - NO PREFIX (routes at root level)

Template Pattern V2:
- Each route module handles its own domain
- Single routes with HX-Request detection for full page vs HTMX partial
- Shared template utilities in shared.py

Route Structure:
- Public routes (public/): User-facing pages
  - home_routes: Home page (/)
  - project_routes: Project CRUD and listing (/projects/*)
  - document_routes: Document viewing and building
  - search_routes: Global search
  - debug_routes: Debug utilities
  
- Admin routes (admin/): Administrative pages
  - pages: Workflow/execution management
  - dashboard: Metrics dashboard
  - documents: Document management
  - partials: HTMX partials
"""

from fastapi import APIRouter

# Public routes
from .public.home_routes import router as home_router
from .public.project_routes import router as project_router
from .public.document_routes import router as document_router
from .public.search_routes import router as search_router
from .public.debug_routes import router as debug_router

# Create main router WITHOUT prefix - routes at root level
router = APIRouter(tags=["web-ui"])

# Include all sub-routers
router.include_router(home_router)
router.include_router(project_router)
router.include_router(document_router)
router.include_router(search_router)
router.include_router(debug_router)