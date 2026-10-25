"""
FastAPI application entry point.
Registers all routers, CORS, middleware, and startup/shutdown events.
"""
from __future__ import annotations
import structlog
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware

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
        import sentry_sdk
        sentry_sdk.init(dsn=settings.SENTRY_DSN, traces_sample_rate=0.1)

    yield

    logger.info("Shutting down SocialCoach AI API")
    await engine.dispose()


app = FastAPI(
    title="SocialCoach AI — Backend API",
    description="Multi-tenant AI Social Media & Lead-Gen Agent Platform for Career Coaches",
    version="1.0.0",
    docs_url=f"{settings.API_V1_PREFIX}/docs" if settings.DEBUG else None,
    redoc_url=f"{settings.API_V1_PREFIX}/redoc" if settings.DEBUG else None,
    lifespan=lifespan,
)

# ── Middleware ─────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://*.socialcoach.ai"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

if settings.APP_ENV == "production":
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["api.socialcoach.ai"])

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


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": "1.0.0", "env": settings.APP_ENV}
