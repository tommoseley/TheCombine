"""UI routers."""

from app.ui.routers.pages import router as pages_router
from app.ui.routers.partials import router as partials_router


__all__ = ["pages_router", "partials_router"]
