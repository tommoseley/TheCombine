"""FastAPI application for Orchestrator HTTP API."""

from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

import uvicorn

from workforce.orchestrator import Orchestrator
from workforce.canon_version_manager import CanonVersionManager
from workforce.utils.logging import log_info, log_error, log_warning
from app.orchestrator_api.middleware.error_handling import add_exception_handlers
from app.orchestrator_api.middleware.logging import RequestLoggingMiddleware
from app.orchestrator_api.middleware.request_id import RequestIDMiddleware
from app.orchestrator_api.middleware.body_size import BodySizeLimitMiddleware
from app.orchestrator_api.routers import artifacts, health
from app.orchestrator_api.routers import anthropic_pm_test  # Ensure this router is imported    
from database import init_database, close_database
from app.orchestrator_api.dependencies import set_orchestrator, set_startup_time
from app.backend.routers import pm_test, architect_test, ba_test
from config import settings

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown events."""
    
    # Startup
    log_info("Starting FastAPI application for Orchestrator")
    startup_time = datetime.now(timezone.utc)
    set_startup_time(startup_time)
    
    try:
        # Initialize database (creates tables if they don't exist)
        log_info("Initializing database...")
        init_database()
        
        # Initialize Orchestrator (stateless - manages canon only)
        log_info("Initializing Orchestrator...")
        canon_manager = CanonVersionManager()
        orchestrator = Orchestrator(canon_manager=canon_manager)
        orchestrator.initialize()
        
        # Set global orchestrator
        set_orchestrator(orchestrator)
        
        current_version = canon_manager.version_store.get_current_version()
        log_info(f"Orchestrator ready: PIPELINE_FLOW_VERSION={current_version}")
        log_info("Note: Orchestrator is stateless - database is source of truth for pipeline state")
        
    except Exception as e:
        log_error(f"Startup failed: {e}")
        raise
    
    yield
    
    # Shutdown
    log_info("Shutting down FastAPI application")
    close_database()
    log_info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title="Orchestrator API",
    description="HTTP API for The Combine Orchestrator runtime",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware (configure for production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID middleware (must be first for proper propagation)
app.add_middleware(RequestIDMiddleware)

# Body size limit middleware (QA-Blocker #1 fix)
app.add_middleware(BodySizeLimitMiddleware)

# Request logging middleware
app.add_middleware(RequestLoggingMiddleware)

# Exception handlers
add_exception_handlers(app)

# Include routers (reorganized for clarity)
app.include_router(health.router, tags=["health"])
app.include_router(artifacts.router, prefix="/pipelines", tags=["artifacts"])
app.include_router(anthropic_pm_test.router, tags=["anthropic"])
app.include_router(pm_test.router)
app.include_router(architect_test.router)  # Add this
app.include_router(ba_test.router)  # And this
app.mount("/web", StaticFiles(directory="app/frontend"), name="web")

if __name__ == "__main__":
    # Development server
    uvicorn.run(
        "app.orchestrator_api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=True
    )