"""Routers package."""

from app.api.routers import health
from app.api.routers import artifacts
from app.api.routers import mentors
from app.api.routers.documents import router as documents_router


__all__ = ["health", "artifacts", "mentors", "documents_router"]    