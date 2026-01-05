"""UI module for The Combine."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.ui.routers import pages_router, partials_router


def setup_ui(app: FastAPI) -> None:
    """Configure UI routes and static files."""
    # Mount static files
    app.mount("/static", StaticFiles(directory="app/ui/static"), name="static")
    
    # Include page routes
    app.include_router(pages_router)
    app.include_router(partials_router)


__all__ = ["setup_ui"]
