"""UI routers."""

from app.ui.routers.pages import router as pages_router
from app.ui.routers.partials import router as partials_router
from app.ui.routers.documents import router as documents_router
from app.ui.routers.dashboard import router as dashboard_router


__all__ = [
    "pages_router",
    "partials_router",
    "documents_router",
    "dashboard_router",
]
