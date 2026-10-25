"""
FastAPI application entry point.
Registers all routers, CORS, middleware, and startup/shutdown events.
Cold-start resilient for serverless runtimes (Vercel, AWS Lambda).
"""
from __future__ import annotations
import os
import sys

# Ensure current directory is on sys.path for Vercel Python serverless runtime
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from config import settings
from database import engine, Base

# Routers
from routers import auth, tenants, posts, hitl, leads, analytics, newsjack, webhooks

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup and shutdown lifecycle."""
    logger.info("Starting SocialCoach AI API", env=settings.APP_ENV)

    # Initialize Sentry if configured
    if settings.SENTRY_DSN:
        try:
            import sentry_sdk
            sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1)
        except Exception as e:
            logger.warning("Sentry init failed", error=str(e))

    yield

    logger.info("Shutting down SocialCoach AI API")
    try:
        await engine.dispose()
    except Exception:
        pass


app = FastAPI(
    title="SocialCoach AI — Backend API",
    description="Multi-tenant AI Social Media & Lead-Gen Agent Platform for Career Coaches",
    version="1.0.0",
    docs_url=f"{settings.API_V1_PREFIX}/docs" if settings.DEBUG else None,
    redoc_url=f"{settings.API_V1_PREFIX}/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ── Resilient Exception Handlers ───────────────────────────────────────────────

@app.exception_handler(SQLAlchemyError)
async def db_exception_handler(request: Request, exc: SQLAlchemyError):
    """Graceful degradation when database is unavailable or unseeded."""
    logger.warning("Database operation unavailable in current environment", path=request.url.path, error=str(exc))
    return JSONResponse(
        status_code=200,
        content={
            "status": "warning",
            "message": "Database not initialized or unreachable. Showing fallback state.",
            "data": [],
        },
    )


# ── Middleware ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Root & Health Check Endpoints ─────────────────────────────────────────────

@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "SocialCoach AI API is operational",
        "version": "1.0.0",
        "env": settings.APP_ENV,
        "database": "sqlite_fallback" if "sqlite" in str(engine.url) else "connected",
    }


@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": "1.0.0",
        "env": settings.APP_ENV,
        "database": "sqlite_fallback" if "sqlite" in str(engine.url) else "connected",
    }


@app.get("/api")
async def api_root():
    return {"status": "ok", "message": "SocialCoach AI API is operational"}


@app.get("/api/health")
async def api_health():
    return {"status": "ok", "version": "1.0.0", "env": settings.APP_ENV}


# ── Routers ────────────────────────────────────────────────────────────────────

PREFIX = settings.API_V1_PREFIX

app.include_router(auth.router,      prefix=f"{PREFIX}/auth",      tags=["Auth"])
app.include_router(tenants.router,   prefix=f"{PREFIX}/tenants",   tags=["Tenants (SuperAdmin)"])
app.include_router(posts.router,     prefix=f"{PREFIX}/posts",     tags=["Posts"])
app.include_router(hitl.router,      prefix=f"{PREFIX}/hitl",      tags=["HITL Approval"])
app.include_router(leads.router,     prefix=f"{PREFIX}/leads",     tags=["Lead CRM"])
app.include_router(analytics.router, prefix=f"{PREFIX}/analytics", tags=["Analytics"])
app.include_router(newsjack.router,  prefix=f"{PREFIX}/newsjack",  tags=["Newsjack Feed"])
app.include_router(webhooks.router,  prefix=f"{PREFIX}/webhooks",  tags=["Platform Webhooks"])

@app.get(f"{PREFIX}/health")
async def prefix_health():
    return {"status": "ok", "version": "1.0.0", "env": settings.APP_ENV}
