"""Public UI routes."""
from .home_routes import router as home_router
from .project_routes import router as project_router
from .document_routes import router as document_router
from .search_routes import router as search_router
from .debug_routes import router as debug_router
from .view_routes import router as view_router

__all__ = [
    "home_router",
    "project_router",
    "document_router",
    "search_router",
    "debug_router",
    "view_router",
]
