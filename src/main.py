"""
FastAPI application entrypoint for the Customer Support Agent.

WHY THIS FILE EXISTS:
---------------------
This is the ENTRY POINT of our entire application. When you run:
    uvicorn src.main:app --reload

It does the following:
1. uvicorn finds this file (src/main.py)
2. Looks for the 'app' variable (our FastAPI instance)
3. Starts an HTTP server that routes requests to our functions

WHAT HAPPENS AT STARTUP:
-------------------------
1. Logging is configured (structured JSON or colored console)
2. Settings are validated (crashes early if .env is wrong)
3. FastAPI app is created with metadata (title, description, version)
4. Routes are registered (health check, later: tickets, webhooks, etc.)
5. Lifespan events handle startup/shutdown tasks (DB connections, etc.)

HOW TO RUN:
-----------
    # Development (auto-reloads on code changes):
    uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

    # Then visit:
    #   http://localhost:8000         → API root
    #   http://localhost:8000/health  → Health check
    #   http://localhost:8000/docs    → Interactive API documentation (Swagger UI)
"""

from contextlib import asynccontextmanager
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.config import settings
from src.utils.logging import get_logger, setup_logging

# ---------------------------------------------------------------------------
# Initialize logging FIRST — before anything else tries to log
# ---------------------------------------------------------------------------
setup_logging(
    log_level=settings.LOG_LEVEL,
    json_format=settings.is_production,  # JSON in prod, colored text in dev
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — runs code at startup and shutdown
# ---------------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manages application lifecycle events.
    
    Code BEFORE 'yield' runs at STARTUP:
        - Connect to databases
        - Initialize AI models
        - Warm up caches
    
    Code AFTER 'yield' runs at SHUTDOWN:
        - Close database connections
        - Flush logs
        - Clean up resources
    
    WHY async context manager?
    FastAPI's modern way to handle startup/shutdown. The old way
    (@app.on_event("startup")) is deprecated. This approach guarantees
    cleanup runs even if the app crashes.
    """
    # ---- STARTUP ----
    logger.info(
        "application_starting",
        app_name=settings.APP_NAME,
        environment=settings.APP_ENV,
        llm_provider=settings.LLM_PROVIDER,
        llm_model=settings.LLM_MODEL,
    )
    
    # Initialize database connection pool
    from src.db.session import init_db, close_db
    try:
        await init_db()
    except Exception as e:
        logger.warning("database_init_skipped", error=str(e),
                       message="App will run but DB features won't work")
    
    # TODO: Initialize Redis connection
    # TODO: Load embedding model
    
    logger.info("application_started", message="All systems ready ✓")
    
    yield  # ← App runs here, handling requests
    
    # ---- SHUTDOWN ----
    logger.info("application_shutting_down")
    
    # Close database connections
    await close_db()
    



# ---------------------------------------------------------------------------
# Create the FastAPI application
# ---------------------------------------------------------------------------
app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "AI-powered autonomous customer support system. "
        "Handles tickets, escalates intelligently, and maintains audit trails."
    ),
    version="0.1.0",
    lifespan=lifespan,
    
    # Swagger UI configuration
    docs_url="/docs",           # Interactive API docs at /docs
    redoc_url="/redoc",         # Alternative docs at /redoc
    openapi_url="/openapi.json", # OpenAPI schema
)


# ---------------------------------------------------------------------------
# CORS Middleware — allows frontend to talk to our API
# ---------------------------------------------------------------------------
# In development, allow all origins. In production, restrict this!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if settings.is_development else [],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ===========================================================================
# ROUTES
# ===========================================================================

@app.get("/", tags=["General"])
async def root():
    """
    API root endpoint.
    
    Returns basic information about the API. Useful for verifying
    the server is running and checking the current version.
    """
    return {
        "name": settings.APP_NAME,
        "version": "0.1.0",
        "status": "running",
        "docs": "/docs",
        "environment": settings.APP_ENV,
    }


@app.get("/health", tags=["General"])
async def health_check():
    """
    Health check endpoint.
    
    Used by monitoring tools, load balancers, and Docker to verify
    the application is alive and can serve requests.
    
    Returns:
        - status: "healthy" if everything is OK
        - timestamp: current server time (proves it's live, not cached)
        - checks: status of each subsystem (database, redis, llm)
    
    TODO Phase 2: Add real database and Redis connectivity checks
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "environment": settings.APP_ENV,
        "checks": {
            "database": "not_configured",   # TODO: real check
            "redis": "not_configured",      # TODO: real check  
            "llm": "not_configured",        # TODO: real check
        },
    }


# ===========================================================================
# API Routes — connect our endpoints to the app
# ===========================================================================
from src.api.routes.tickets import router as tickets_router
from src.api.routes.webhooks import router as webhooks_router
from src.api.routes.analytics import router as analytics_router

app.include_router(tickets_router)
app.include_router(webhooks_router)
app.include_router(analytics_router)
