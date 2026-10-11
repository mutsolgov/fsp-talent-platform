"""
FSP IT-Talent Platform — Core Application Configuration.
"""
from __future__ import annotations

import os
from typing import List
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "Цифровая платформа-агрегатор ИТ-вакансий с верифицированным профилем достижений участника ФСП"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    DATABASE_URL: str = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./fsp_talent.db")
    SYNC_DATABASE_URL: str = os.getenv("SYNC_DATABASE_URL", "")

    def __init__(self, **values):
        super().__init__(**values)
        if not self.SYNC_DATABASE_URL:
            db_url = self.DATABASE_URL
            if "sqlite+aiosqlite" in db_url:
                self.SYNC_DATABASE_URL = db_url.replace("sqlite+aiosqlite", "sqlite")
            elif "postgresql+asyncpg" in db_url:
                self.SYNC_DATABASE_URL = db_url.replace("postgresql+asyncpg", "postgresql")
            else:
                self.SYNC_DATABASE_URL = db_url

    SECRET_KEY: str = os.getenv("SECRET_KEY", "fsp-secret-jwt-key-2026-production-token-fsp-russia-lct")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    CORS_ORIGINS: List[str] = ["*"]

    # 152-ФЗ Policy version
    POLICY_VERSION: str = "v1.0-2026"

    # Demo & Jury bypass configuration
    DEMO_BYPASS_ENABLED: bool = os.getenv("DEMO_BYPASS_ENABLED", "True").lower() in ("true", "1", "yes")
    COOLDOWN_DAYS: int = int(os.getenv("COOLDOWN_DAYS", "30"))

    # Keycloak 26 OIDC Configuration
    KEYCLOAK_INTERNAL_URL: str = os.getenv("KEYCLOAK_INTERNAL_URL", "http://keycloak:8080/auth")
    KEYCLOAK_EXTERNAL_URL: str = os.getenv("KEYCLOAK_EXTERNAL_URL", "/auth")
    KEYCLOAK_REALM: str = os.getenv("KEYCLOAK_REALM", "fsp-realm")
    KEYCLOAK_CLIENT_ID: str = os.getenv("KEYCLOAK_CLIENT_ID", "fsp-frontend")


settings = Settings()
