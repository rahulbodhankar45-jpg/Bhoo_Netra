"""
Land Stack India - Core Application Configuration
Defines settings, API versioning, security secrets, and environment parameters.
"""
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Land Stack India Backend"
    PROJECT_DESCRIPTION: str = "National Digital Public Infrastructure for Land Records & GIS Interoperability"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Security
    SECRET_KEY: str = "land-stack-india-national-secure-secret-key-2026-super-secure"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database: Dual mode (SQLite for zero-config run, PostgreSQL+PostGIS for production)
    DATABASE_URL: str = "sqlite:///./land_stack.db"
    POSTGRES_DATABASE_URL: str = "postgresql://landadmin:landpassword@localhost:5432/landstack"

    # Redis / Cache
    REDIS_URL: str = "redis://localhost:6379/0"
    CACHE_ENABLED: bool = True
    CACHE_TTL_SECONDS: int = 300

    # Rate Limiting
    RATE_LIMIT_PER_MINUTE: int = 120

    # CORS
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "https://landstack.gov.in",
        "*",
    ]

    # ULPIN Configuration
    ULPIN_DEFAULT_STATE_PREFIX: str = "IN"
    ULPIN_LENGTH: int = 14

    # Storage paths
    UPLOAD_DIR: str = "./storage/documents"

    # SMTP Email Configuration for OTP and Notifications
    SMTP_HOST: str | None = None
    SMTP_PORT: int = 587
    SMTP_USER: str | None = None
    SMTP_PASSWORD: str | None = None
    SMTP_FROM_EMAIL: str = "noreply@bhoonetra.gov.in"
    SMTP_FROM_NAME: str = "Land Stack India / BhooNetra"
    SMTP_TLS: bool = True
    SMTP_SSL: bool = False

    model_config = SettingsConfigDict(case_sensitive=True, env_file=".env", extra="ignore")


settings = Settings()
