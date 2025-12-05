"""Health check endpoint."""

from datetime import datetime,timezone
from fastapi import APIRouter
from pydantic import BaseModel

from app.orchestrator_api.dependencies import get_orchestrator, get_startup_time  
from app.orchestrator_api.persistence.database import check_database_connection
from workforce.utils.logging import log_warning

class HealthResponse(BaseModel):
    """Health check response."""
    status: str
    orchestrator_ready: bool
    canon_loaded: bool
    canon_version: str
    database_connected: bool
    uptime_seconds: int


router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint (unauthenticated).
    
    Returns service health status including Orchestrator readiness,
    canon version, database connectivity, and uptime.
    
    CRITICAL: This endpoint must NEVER throw exceptions.
    Always returns 200 with health status (healthy or unhealthy).
    """
    try:
        # Try to get orchestrator
        try:
            orchestrator = get_orchestrator()
            orchestrator_ready = True
            
            # Try to get canon info
            try:
                canon_version = str(orchestrator.canon_manager.version_store.get_current_version())
                canon_loaded = orchestrator.canon_manager.version_store.is_loaded()
            except Exception as e:
                log_warning(f"Health check: Canon access failed: {e}")
                canon_version = "unknown"
                canon_loaded = False
        except Exception as e:
            log_warning(f"Health check: Orchestrator not ready: {e}")
            orchestrator_ready = False
            canon_version = "unknown"
            canon_loaded = False
        
        # Try to get startup time
        try:
            startup_time = get_startup_time()
            uptime = int((datetime.now(timezone.utc)- startup_time).total_seconds())
        except Exception:
            uptime = 0
        
        # Try to check database
        try:
            db_connected = check_database_connection()
        except Exception as e:
            log_warning(f"Health check: Database check failed: {e}")
            db_connected = False
        
        # Determine overall status
        if orchestrator_ready and canon_loaded and db_connected:
            status = "healthy"
        else:
            status = "unhealthy"
        
        return HealthResponse(
            status=status,
            orchestrator_ready=orchestrator_ready,
            canon_loaded=canon_loaded,
            canon_version=canon_version,
            database_connected=db_connected,
            uptime_seconds=uptime
        )
        
    except Exception as e:
        # Absolute fallback - should never happen
        log_warning(f"Health check: Unexpected error: {e}")
        return HealthResponse(
            status="unhealthy",
            orchestrator_ready=False,
            canon_loaded=False,
            canon_version="unknown",
            database_connected=False,
            uptime_seconds=0
        )