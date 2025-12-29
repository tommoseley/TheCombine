"""
Health check endpoint for The Combine API.
Alternative version with separate liveness and readiness probes.
"""
from fastapi import APIRouter, Depends, status, Response
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.database import get_db

router = APIRouter(tags=["health"])
logger = logging.getLogger(__name__)


@router.get("/health", status_code=status.HTTP_200_OK)
async def liveness_check():
    """
    Simple liveness check - just confirms the app is running.
    Does NOT check database (for fast health checks).
    Use this for container liveness probes.
    """
    return {"status": "healthy"}


@router.get("/health/ready", status_code=status.HTTP_200_OK)
async def readiness_check(response: Response, db: AsyncSession = Depends(get_db)):
    """
    Readiness check - confirms app AND database are ready.
    Use this for container readiness probes.
    """
    try:
        # Test database connectivity
        result = await db.execute(text("SELECT 1"))
        result.scalar()
        
        return {
            "status": "ready",
            "database": "connected"
        }
    except Exception as e:
        logger.error(f"Readiness check failed: {e}", exc_info=True)
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return {
            "status": "not_ready",
            "database": "disconnected",
            "error": str(e)
        }


@router.get("/health/detailed", status_code=status.HTTP_200_OK)
async def detailed_health_check(response: Response, db: AsyncSession = Depends(get_db)):
    """
    Detailed health check with comprehensive information.
    """
    health_status = {
        "status": "healthy",
        "checks": {}
    }
    
    overall_healthy = True
    
    # Database check
    try:
        result = await db.execute(text("SELECT version()"))
        db_version = result.scalar()
        health_status["checks"]["database"] = {
            "status": "healthy",
            "version": db_version
        }
    except Exception as e:
        logger.error(f"Database health check failed: {e}", exc_info=True)
        overall_healthy = False
        health_status["checks"]["database"] = {
            "status": "unhealthy",
            "error": str(e)
        }
    
    # Migrations check
    try:
        result = await db.execute(text("SELECT version_num FROM alembic_version"))
        migration_version = result.scalar()
        health_status["checks"]["migrations"] = {
            "status": "healthy",
            "current_version": migration_version
        }
    except Exception as e:
        logger.warning(f"Migration check failed: {e}")
        health_status["checks"]["migrations"] = {
            "status": "unknown",
            "error": str(e)
        }
    
    # Set overall status
    if not overall_healthy:
        health_status["status"] = "unhealthy"
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    
    return health_status