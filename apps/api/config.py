"""
Application configuration via environment variables.
All secrets are loaded from .env and never hardcoded.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # ── App ──────────────────────────────────────────────────────────────────
    APP_NAME: str = "SocialCoach AI"
    APP_ENV: str = "development"          # development | staging | production
    DEBUG: bool = False
    SECRET_KEY: str                        # JWT signing key
    API_V1_PREFIX: str = "/api/v1"

    # ── Database ─────────────────────────────────────────────────────────────
    DATABASE_URL: str                      # postgres+asyncpg://...
    DATABASE_URL_SYNC: str                 # postgresql://... (for Alembic)
    SUPABASE_URL: str
    SUPABASE_SERVICE_ROLE_KEY: str         # Bypasses RLS for backend workers

    # ── Redis ─────────────────────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # ── Security / Encryption ─────────────────────────────────────────────────
    OAUTH_VAULT_ENCRYPTION_KEY: str        # 32-byte base64 key for AES-256-GCM
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # ── Google Gemini (LLM) ───────────────────────────────────────────────────
    GEMINI_API_KEY: str
    GEMINI_MODEL: str = "gemini-2.0-flash-exp"
    GEMINI_PRO_MODEL: str = "gemini-2.0-pro"

    # ── Search APIs (Agent 1) ─────────────────────────────────────────────────
    TAVILY_API_KEY: str
    NEWS_API_KEY: str
    SERPAPI_KEY: str = ""

    # ── Meta (Instagram + Facebook) ───────────────────────────────────────────
    META_APP_ID: str
    META_APP_SECRET: str
    META_WEBHOOK_VERIFY_TOKEN: str

    # ── LinkedIn ──────────────────────────────────────────────────────────────
    LINKEDIN_CLIENT_ID: str
    LINKEDIN_CLIENT_SECRET: str
    LINKEDIN_WEBHOOK_VERIFY_TOKEN: str

    # ── X (Twitter) ───────────────────────────────────────────────────────────
    TWITTER_API_KEY: str
    TWITTER_API_SECRET: str
    TWITTER_BEARER_TOKEN: str
    TWITTER_WEBHOOK_ENV_NAME: str = "production"

    # ── Storage (S3 / Supabase Storage) ──────────────────────────────────────
    STORAGE_BUCKET_CAROUSELS: str = "carousels"
    STORAGE_BUCKET_ASSETS: str = "assets"
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "us-east-1"

    # ── Carousel Renderer Microservice ────────────────────────────────────────
    CAROUSEL_RENDERER_URL: str = "http://localhost:3001"

    # ── Sentry ────────────────────────────────────────────────────────────────
    SENTRY_DSN: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
