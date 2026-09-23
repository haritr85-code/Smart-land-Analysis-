"""
main.py
-------
FastAPI application entrypoint.
Configures CORS, lifespan, documentation endpoints, and includes all routers.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings

logging.basicConfig(
    level=logging.INFO if not settings.DEBUG else logging.DEBUG,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan handler.
    Runs once on startup and once on shutdown.
    Verifies DB connectivity without crashing the process if the database
    is waking up or temporarily spinning up (e.g. Supabase cold starts).
    Also ensures all required database tables exist.
    """
    logger.info("Starting %s [%s environment]", settings.APP_NAME, settings.APP_ENV)

    # Verify database connectivity and initialize tables if needed
    try:
        from app.db.session import engine
        from app.db.base import Base
        from sqlalchemy import text

        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection verified successfully.")

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        logger.info("Database schema verified / initialized.")
    except Exception as exc:
        logger.warning(
            "Database connection/initialization warning at startup: %s. "
            "The server will continue running to handle cold starts.",
            exc,
        )

    yield

    logger.info("Shutting down %s", settings.APP_NAME)
    try:
        from app.db.session import engine
        await engine.dispose()
    except Exception as exc:
        logger.warning("Error closing database connection pool during shutdown: %s", exc)


def create_application() -> FastAPI:
    """Application factory - builds and configures the FastAPI instance."""

    openapi_tags = [
        {"name": "Health", "description": "Liveness and health check endpoints"},
        {"name": "Authentication", "description": "User registration, authentication, and JWT token management"},
        {"name": "Land Management", "description": "Create, retrieve, update, and manage land parcels"},
        {"name": "Land Cover (ESA WorldCover)", "description": "Real-time ESA WorldCover 10m satellite classification via COG streaming"},
        {"name": "AI Suitability Analysis", "description": "Machine learning feasibility engine, risk assessment, and explainable AI"},
        {"name": "Dashboard", "description": "Aggregated analytics, metrics, building distributions, and recent analyses"},
        {"name": "PDF Reports", "description": "Generate and download comprehensive land feasibility audit PDF reports"},
    ]

    app = FastAPI(
        title=settings.APP_NAME,
        description="AI-Based Decision Support System for Building Planning - Backend API",
        version="1.0.0",
        openapi_tags=openapi_tags,
        openapi_url="/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )

    # ---------------- CORS ----------------
    # Allows Vercel production frontend and local dev environments
    default_origins = [
        "https://smart-land-analysis.vercel.app",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]
    configured_origins = list(settings.BACKEND_CORS_ORIGINS) if settings.BACKEND_CORS_ORIGINS else []
    
    # Filter out wildcard "*" to maintain strict browser CORS credential compliance
    allowed_origins = [orig for orig in configured_origins if orig != "*"]
    for orig in default_origins:
        if orig not in allowed_origins:
            allowed_origins.append(orig)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_origin_regex=r"https://.*\.vercel\.app|http://(localhost|127\.0\.0\.1)(:\d+)?",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["Content-Disposition", "content-disposition"],
    )

    # ---------------- Routers ----------------
    from app.routers import (
        analysis,
        auth,
        dashboard,
        land,
        landcover,
        reports,
    )

    # Include all API routers with the global API prefix (e.g. /api/v1)
    app.include_router(auth.router, prefix=settings.API_V1_PREFIX)
    app.include_router(land.router, prefix=settings.API_V1_PREFIX)
    app.include_router(landcover.router, prefix=settings.API_V1_PREFIX)
    app.include_router(analysis.router, prefix=settings.API_V1_PREFIX)
    app.include_router(dashboard.router, prefix=settings.API_V1_PREFIX)
    app.include_router(reports.router, prefix=settings.API_V1_PREFIX)

    # ---------------- Documentation Redirects ----------------
    @app.get(f"{settings.API_V1_PREFIX}/docs", include_in_schema=False)
    async def api_v1_docs():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/docs")

    @app.get(f"{settings.API_V1_PREFIX}/openapi.json", include_in_schema=False)
    async def api_v1_openapi():
        from fastapi.responses import RedirectResponse
        return RedirectResponse(url="/openapi.json")

    # ---------------- Health / Root Endpoints ----------------
    @app.get("/", tags=["Health"], status_code=200)
    async def root():
        """Root health check endpoint."""
        return {
            "message": "Smart Land Analysis API is running"
        }

    @app.get("/health", tags=["Health"])
    @app.get(f"{settings.API_V1_PREFIX}/health", tags=["Health"])
    async def health_check():
        """Health check endpoint - verifies the API process is alive."""
        return {
            "status": "ok",
            "message": "Smart Land Analysis API is running",
        }

    return app


app = create_application()
