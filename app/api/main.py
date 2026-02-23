"""
Main FastAPI application for The Combine API.

The Combine: AI-driven pipeline automation system.
"""

from dotenv import load_dotenv
import os
load_dotenv()  # noqa: E402 — must run before any app imports read env vars

from fastapi import FastAPI, Request  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import FileResponse  # noqa: E402
from datetime import datetime  # noqa: E402
from contextlib import asynccontextmanager  # noqa: E402
import logging  # noqa: E402


from starlette.middleware.sessions import SessionMiddleware  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import init_database  # noqa: E402

# Import API dependencies
from app.core.dependencies import set_startup_time  # noqa: E402

# Import routers
from app.api.routers import health  # noqa: E402
from app.web import routes as web_routes  # noqa: E402
from app.api.routers.documents import router as document_router  # noqa: E402
from app.api.routers.document_status_router import router as document_status_router  # noqa: E402
# Phase 8 (WS-DOCUMENT-SYSTEM-CLEANUP): Admin replay endpoint behind feature flag
from app.core.config import ENABLE_DEBUG_ROUTES  # noqa: E402
from app.auth.routes import router as auth_router  # noqa: E402
from app.api.routers.protected import router as protected_router  # noqa: E402
from app.api.routers.accounts import router as accounts_router  # noqa: E402
from app.api.routers.commands import router as commands_router  # noqa: E402  # WS-STORY-BACKLOG-COMMANDS
from app.api.routers.config_routes import router as config_router  # noqa: E402

# Phase 8-10 routers (workflows, executions, telemetry, dashboard)
from app.api.v1 import api_router as v1_router  # noqa: E402
from app.web.routes.admin.composer_routes import router as composer_router  # noqa: E402
from app.web.routes.production import router as production_router  # noqa: E402  # ADR-043: Production Line
# Import middleware
from app.api.middleware import (  # noqa: E402
    error_handling,
    request_id,
    body_size,
    logging as log_middleware,
    secret_ingress,
)

# Configure logging
LOG_DIR = os.getenv("LOG_DIR", "/tmp")  # Directory for log files
LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# Generate timestamped log filename
LOG_TIMESTAMP = datetime.now().strftime("%Y%m%d-%H%M%S")
LOG_FILE = os.path.join(LOG_DIR, f"combine-{LOG_TIMESTAMP}.log")

# Set up root logger
logging.basicConfig(
    level=logging.DEBUG,
    format=LOG_FORMAT
)

# Add file handler
file_handler = logging.FileHandler(LOG_FILE)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
logging.getLogger().addHandler(file_handler)

logger = logging.getLogger(__name__)
logger.info(f"Logging to file: {LOG_FILE}")


# ============================================================================
# LIFESPAN (startup/shutdown)
# ============================================================================

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler for startup and shutdown."""
    import signal

    # Startup
    logger.info("Starting The Combine API")
    set_startup_time(datetime.utcnow())

    try:
        await init_database()
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Database initialization failed: {e}")
        raise

    # Set up signal handler to close SSE connections before uvicorn waits
    original_sigint = signal.getsignal(signal.SIGINT)
    original_sigterm = signal.getsignal(signal.SIGTERM)

    def handle_shutdown_signal(signum, frame):
        logger.info("Received shutdown signal, closing SSE connections...")
        try:
            from app.api.v1.routers.production import get_shutdown_event
            get_shutdown_event().set()
        except Exception as e:
            logger.warning(f"Error signaling SSE shutdown: {e}")
        # Call the original handler (uvicorn's)
        if signum == signal.SIGINT and callable(original_sigint):
            original_sigint(signum, frame)
        elif signum == signal.SIGTERM and callable(original_sigterm):
            original_sigterm(signum, frame)

    # Register signal handlers (only on main thread)
    try:
        signal.signal(signal.SIGINT, handle_shutdown_signal)
        signal.signal(signal.SIGTERM, handle_shutdown_signal)
    except ValueError:
        # Can't set signal handlers from non-main thread
        pass

    logger.info("The Combine API started successfully")
    logger.info(f"API Documentation: http://{settings.API_HOST}:{settings.API_PORT}/docs")

    yield

    # Shutdown
    logger.info("Shutting down The Combine API...")

    # Close SSE connections gracefully (backup, in case signal didn't fire)
    try:
        from app.api.v1.routers.production import shutdown_sse_connections
        await shutdown_sse_connections()
    except Exception as e:
        logger.warning(f"Error shutting down SSE connections: {e}")

# Create FastAPI app
app = FastAPI(
    title="The Combine",
    description="AI-driven pipeline automation system",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Mount static files from app/web directory
app.mount("/web", StaticFiles(directory="app/web"), name="web")

# Mount SPA static assets (Vite build output)
# Only mount if the spa/dist directory exists (after npm run build)
import pathlib  # noqa: E402
SPA_DIST_PATH = pathlib.Path("spa/dist")
SPA_ENABLED = SPA_DIST_PATH.exists()
if SPA_ENABLED:
    # Mount SPA assets at /assets (JS, CSS bundles)
    app.mount("/assets", StaticFiles(directory="spa/dist/assets"), name="spa-assets")
    logger.info("SPA assets mounted at /assets")
    # Mount SPA content (YAML/JSON config files)
    SPA_CONTENT_PATH = SPA_DIST_PATH / "content"
    if SPA_CONTENT_PATH.exists():
        app.mount("/content", StaticFiles(directory="spa/dist/content"), name="spa-content")
        logger.info("SPA content mounted at /content")

# ============================================================================
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

# Custom middleware (last added = first executed)
app.add_middleware(log_middleware.LoggingMiddleware)
app.add_middleware(request_id.RequestIDMiddleware)
app.add_middleware(body_size.BodySizeMiddleware)
app.add_middleware(secret_ingress.SecretIngressMiddleware)  # GOV-SEC-T0-002: Gate 1
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
    https_only=os.getenv('HTTPS_ONLY', 'false').lower() == 'true',
    path='/'
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

# Phase 8 (WS-DOCUMENT-SYSTEM-CLEANUP): Admin replay endpoint behind feature flag
if ENABLE_DEBUG_ROUTES:
    from app.api.routers.admin import router as api_admin_router
    app.include_router(api_admin_router)  # ADR-010: /api/admin endpoints
    logger.info("DEBUG_ROUTES_ENABLED: /api/admin/llm-runs/*/replay endpoint active")
else:
    logger.info("DEBUG_ROUTES_DISABLED: /api/admin endpoints disabled in production")

app.include_router(protected_router)
app.include_router(accounts_router)
app.include_router(commands_router)  # WS-STORY-BACKLOG-COMMANDS
app.include_router(config_router)  # System config API

# Phase 8-10: Workflow execution engine routes
app.include_router(v1_router)  # /api/v1/workflows, /api/v1/executions
app.include_router(composer_router)  # ADR-034: Composer preview endpoints
app.include_router(production_router)  # ADR-043: Production Line UI


# ============================================================================
# SPA ROUTES - Serve React SPA at root
# ============================================================================

if SPA_ENABLED:
    @app.get("/logo-256.png")
    @app.get("/logo-light.png")
    @app.get("/logo-dark.png")
    @app.get("/logo-blueprint.png")
    async def serve_spa_logos(request: Request):
        """Serve SPA logo files."""
        # Extract filename from path
        filename = request.url.path.lstrip("/")
        logo_path = SPA_DIST_PATH / filename
        if logo_path.exists():
            return FileResponse(logo_path)
        return FileResponse(SPA_DIST_PATH / "logo-256.png")

    @app.get("/favicon.ico")
    async def serve_favicon():
        """Serve favicon."""
        return FileResponse(SPA_DIST_PATH / "logo-256.png", media_type="image/png")

# Note: The home route at "/" is defined in home_routes.py and will be updated
# to serve the SPA index.html instead of the Jinja template.


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

