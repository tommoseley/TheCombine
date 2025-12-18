"""Routers package."""

from app.api.routers import health, auth
from app.api.routers.documents import router as documents_router


__all__ = ["health", "auth", "documents_router"]    