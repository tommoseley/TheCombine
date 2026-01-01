"""
Main FastAPI application for The Combine API.

The Combine: AI-driven pipeline automation system.
"""

from dotenv import load_dotenv
import os
load_dotenv()

from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.templating import Jinja2Templates
from fastapi.responses import FileResponse
from datetime import datetime
import logging


from starlette.middleware.sessions import SessionMiddleware

from app.core.config import settings
from app.core.database import init_database

# Import API dependencies
from app.core.dependencies import set_startup_time

# Import routers
from app.api.routers import health, auth
from app.web import routes as web_routes
from app.api.routers.documents import router as document_router
from app.api.routers.document_status_router import router as document_status_router
from app.web.routes.document_status_routes import router as document_status_ui_router
from app.web.routes.admin_routes import router as admin_router
from app.api.routers.admin import router as api_admin_router  # ADR-010: Replay endpoint
from app.auth.routes import router as auth_router
from app.api.routers.protected import router as protected_router
from app.api.routers.accounts import router as accounts_router
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
app.mount("/static", StaticFiles(directory="app/web/static"), name="static")

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
        logger.info("âœ… Database initialized")
    except Exception as e:
        logger.error(f"âŒ Database initialization failed: {e}")
        raise
    
    logger.info("âœ… The Combine API started successfully")
    logger.info(f"ðŸ“š API Documentation: http://{settings.API_HOST}:{settings.API_PORT}/docs")

@app.get("/test-session")
async def test_session(request: Request):
    """Test if sessions work"""
    # Set a value in session
    request.session['test'] = 'hello'
    return {
        "session_data": dict(request.session),
        "cookie_name": "combine_session",
        "check": "Look for combine_session cookie in DevTools"
    }

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

# Add SessionMiddleware to your FastAPI app
# Place this AFTER app = FastAPI() but BEFORE any route definitions

# ============================================================================
# SESSION MIDDLEWARE (Required for Authlib OIDC)
# ============================================================================
# CRITICAL: Authlib requires SessionMiddleware to store state/nonce during OAuth flow.
# Without this, OAuth login will fail with cryptic errors about missing state.

app.add_middleware(
    SessionMiddleware,
    secret_key=os.getenv('SESSION_SECRET_KEY', os.urandom(32).hex()),
    session_cookie='combine_session',  # Cookie name for session state
    max_age=600,  # 10 minutes - only for OAuth flow, not user sessions
    same_site='lax',
    https_only=os.getenv('HTTPS_ONLY', 'false').lower() == 'true'
)

# Note: This is DIFFERENT from user session cookies (__Host-session).
# This session is ONLY for storing OAuth state/nonce during the login redirect.
# Actual user sessions will be managed separately in the database.

# ============================================================================
# ROUTERS
# ============================================================================

# Health check
app.include_router(health.router, tags=["health"])

# Authentication (OAuth login/logout)
app.include_router(auth_router)

# Document-centric API (new system)
app.include_router(document_router)

# Web UI routes - NO PREFIX (routes at root level: /, /projects/*, /search, etc.)
app.include_router(web_routes.router)

# Other routes - ALL at root level now
app.include_router(document_status_router, prefix="/api")
app.include_router(admin_router)  # Admin now at /admin (not /ui/admin)
app.include_router(api_admin_router)  # ADR-010: /api/admin endpoints
app.include_router(protected_router)
app.include_router(accounts_router)


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