"""
Health check endpoint for The Combine API.

Provides system health status and uptime information.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timezone
from sqlalchemy import text
import logging

from app.core.dependencies import get_startup_time
from app.core.database import engine

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Returns system status, uptime, and database connectivity.
    """
    try:
        startup_time = get_startup_time()
        if startup_time.tzinfo is None:
            startup_time = startup_time.replace(tzinfo=timezone.utc)
        current_time = datetime.now(timezone.utc)
        uptime_seconds = (current_time - startup_time).total_seconds()
        
        # Check database connectivity
        db_status = "connected"
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
        except Exception as e:
            db_status = f"error: {str(e)}"
            logger.error(f"Database health check failed: {e}")
        
        return {
            "status": "healthy" if db_status == "connected" else "degraded",
            "timestamp": current_time.isoformat(),
            "uptime_seconds": uptime_seconds,
            "database": db_status,
            "service": "The Combine API",
            "version": "1.0.0"
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "unhealthy",
                "error": str(e)
            }
        )


@router.get("/health/ready")
async def readiness_check():
    """
    Readiness check for load balancers.
    
    Returns 200 if service is ready to accept traffic.
    """
    try:
        # Check database connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        
        return {"status": "ready"}
        
    except Exception as e:
        logger.error(f"Readiness check failed: {e}")
        raise HTTPException(
            status_code=503,
            detail={
                "status": "not_ready",
                "error": "Database unavailable"
            }
        )


@router.get("/health/live")
async def liveness_check():
    """
    Liveness check for orchestrators.
    
    Returns 200 if service is alive (even if not ready).
    """
    return {"status": "alive"}