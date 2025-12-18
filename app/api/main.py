"""
Main FastAPI application for The Combine API.

The Combine: AI-driven pipeline automation system.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from datetime import datetime
import logging

from config import settings
from database import init_database

# Import API dependencies
from app.dependencies import set_startup_time

# Import routers
from app.api.routers import health, auth
from app.web import routes as web_routes
from app.api.routers.mentors import router as mentor_router
from app.api.routers.documents import router as document_router

# Import middleware
from app.api.middleware import (
    error_handling,
    request_id,
    body_size,
    logging as log_middleware
)

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="The Combine",
    description="AI-driven pipeline automation system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Mount static files from app/web directory
app.mount("/web", StaticFiles(directory="app/web"), name="web")

# ============================================================================
# STARTUP
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting The Combine API")
    
    # Set startup time
    set_startup_time(datetime.utcnow())
    
    # Initialize database
    try:
        await init_database()
        logger.info("✅ Database initialized")
    except Exception as e:
        logger.error(f"❌ Database initialization failed: {e}")
        raise
    
    logger.info("✅ The Combine API started successfully")
    logger.info(f"📚 API Documentation: http://{settings.API_HOST}:{settings.API_PORT}/docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down The Combine API...")


# ============================================================================
# MIDDLEWARE
# ============================================================================

# Add middleware (order matters - last added = first executed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Custom middleware
app.add_middleware(log_middleware.LoggingMiddleware)
app.add_middleware(request_id.RequestIDMiddleware)
app.add_middleware(body_size.BodySizeMiddleware)
app.add_middleware(error_handling.ErrorHandlingMiddleware)


# ============================================================================
# ROUTERS
# ============================================================================

# Health check
app.include_router(health.router, tags=["health"])
app.include_router(document_router)
app.include_router(mentor_router)

# ADD THIS LINE
app.include_router(web_routes.router)

# ============================================================================
# ROOT ENDPOINT
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint - API information."""
    return {
        "name": "The Combine API",
        "version": "1.0.0",
        "description": "AI-driven pipeline automation system",
        "status": "operational",
        "docs": "/docs",
        "health": "/health",
        "components": {
            "combine": "AI engine (mentors, services, persistence)",
            "api": "HTTP gateway (routers, middleware)"
        }
    }


# ============================================================================
# DEVELOPMENT SERVER (optional - use scripts/run.py instead)
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True,
        log_level="debug"
      
    )