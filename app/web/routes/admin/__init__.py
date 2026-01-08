"""Admin UI routes."""
from .pages import router as pages_router
from .dashboard import router as dashboard_router
from .partials import router as partials_router
from .documents import router as documents_router
from .admin_routes import router as admin_router
from .composer_routes import router as composer_router

__all__ = [
    "pages_router",
    "dashboard_router", 
    "partials_router",
    "documents_router",
    "admin_router",
    "composer_router",
]
