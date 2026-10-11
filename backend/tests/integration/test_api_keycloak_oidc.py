"""
Integration Test Suite for Keycloak 26 OIDC Flow, PKCE S256, JIT Provisioning, and Offline Fallback.
Defined in docs/04 §4.1-4.3 and DISPATCH.md.
"""
from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import AsyncMock, patch

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import httpx
import jwt
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.database import get_db
from app.main import app
from app.models.base import Base
from app.services.fsp_mock_registry import generate_code_challenge
from scripts.seed_reference_data import seed_reference_data

TEST_DB_URL = "sqlite+aiosqlite:///./test_keycloak_oidc.db"
test_engine = create_async_engine(
    TEST_DB_URL,
    connect_args={"timeout": 30},
    echo=False,
)
test_session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)


@event.listens_for(test_engine.sync_engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    try:
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA busy_timeout = 30000")
        cursor.execute("PRAGMA foreign_keys = ON")
        cursor.close()
    except Exception:
        pass


async def override_get_db():
    async with test_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


_db_initialized = False


@pytest.fixture
def client():
    global _db_initialized

    async def _setup():
        global _db_initialized
        if not _db_initialized:
            async with test_engine.begin() as conn:
                await conn.run_sync(Base.metadata.drop_all)
                await conn.run_sync(Base.metadata.create_all)
            async with test_session_factory() as session:
                await seed_reference_data(session)
            _db_initialized = True
        else:
            async with test_session_factory() as session:
                await session.execute(text("DELETE FROM fsp_achievements"))
                await session.execute(text("DELETE FROM candidate_profiles"))
                await session.execute(text("DELETE FROM user_consents"))
                await session.execute(text("DELETE FROM users"))
                await session.commit()

    asyncio.run(_setup())

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()


def test_keycloak_settings_configuration():
    """Verifies that Keycloak OIDC settings are correctly exposed on settings object."""
    assert hasattr(settings, "KEYCLOAK_INTERNAL_URL")
    assert hasattr(settings, "KEYCLOAK_EXTERNAL_URL")
    assert hasattr(settings, "KEYCLOAK_REALM")
    assert hasattr(settings, "KEYCLOAK_CLIENT_ID")
    assert settings.KEYCLOAK_REALM == "fsp-realm"
    assert settings.KEYCLOAK_CLIENT_ID == "fsp-frontend"
    assert "/auth" in settings.KEYCLOAK_EXTERNAL_URL
    assert "keycloak" in settings.KEYCLOAK_INTERNAL_URL or "http" in settings.KEYCLOAK_INTERNAL_URL


def test_connect_offline_fallback_jit_provisioning(client: TestClient):
    """
    Verifies that when Keycloak container is offline, /fsp-integration/connect
    falls back gracefully to mock registry, provisions the user JIT, and returns JWT tokens.
    """
    verifier = "fsp_test_pkce_verifier_long_random_string_128_chars"
    challenge = generate_code_challenge(verifier)

    auth_resp = client.get(
        "/api/v1/fsp-integration/authorize",
        params={
            "response_type": "code",
            "client_id": "fsp-frontend",
            "redirect_uri": "http://localhost:3000/auth/fsp/callback",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "fsp_id": "FSP-77-01042",
        },
    )
    assert auth_resp.status_code == 200
    code = auth_resp.json()["code"]

    # Connect without Bearer token (SSO login scenario)
    conn_resp = client.post(
        "/api/v1/fsp-integration/connect",
        json={
            "code": code,
            "redirect_uri": "http://localhost:3000/auth/fsp/callback",
            "code_verifier": verifier,
        },
    )
    assert conn_resp.status_code == 200
    data = conn_resp.json()
    assert data["fsp_id"] == "FSP-77-01042"
    assert data["fsp_verified"] is True
    assert data["achievements_synced"] == 2
    assert "access_token" in data and data["access_token"] is not None
    assert "refresh_token" in data and data["refresh_token"] is not None
    assert data["role"] == "candidate"
    assert data["user_id"] is not None
    assert data["email"] is not None

    # Verify that returned access_token is valid for accessing authenticated endpoints
    headers = {"Authorization": f"Bearer {data['access_token']}"}
    prof_resp = client.get("/api/v1/fsp-integration/profile", headers=headers)
    assert prof_resp.status_code == 200
    assert prof_resp.json()["is_fsp_candidate"] is True
    assert prof_resp.json()["fsp_id"] == "FSP-77-01042"
    assert prof_resp.json()["badge_title"] == "Верифицирован ФСП"


def test_connect_mock_keycloak_network_exchange(client: TestClient):
    """
    Simulates a successful Keycloak 26 HTTP exchange with an ID token,
    verifying JIT provisioning from Keycloak claims.
    """
    test_id_token = jwt.encode(
        {
            "sub": "kc-user-uuid-1042",
            "email": "athlete.test@fsp-russia.ru",
            "given_name": "Алексей",
            "family_name": "Кузнецов",
            "fsp_id": "FSP-77-01042",
        },
        key="test_key",
        algorithm="HS256",
    )

    fake_kc_response = httpx.Response(
        status_code=200,
        json={
            "access_token": "mock_kc_access_token",
            "id_token": test_id_token,
            "refresh_token": "mock_kc_refresh_token",
            "token_type": "Bearer",
            "expires_in": 300,
        },
        request=httpx.Request("POST", "http://keycloak:8080/auth/realms/fsp-realm/protocol/openid-connect/token"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = fake_kc_response

        resp = client.post(
            "/api/v1/fsp-integration/connect",
            json={
                "code": "real_kc_code_abc123",
                "redirect_uri": "http://localhost:3000/auth/fsp/callback",
                "code_verifier": "valid_pkce_verifier_longer_than_ten_chars",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["fsp_id"] == "FSP-77-01042"
        assert data["fsp_verified"] is True
        assert data["access_token"] is not None
        assert data["refresh_token"] is not None
        assert data["user_id"] is not None
        assert data["email"] == "athlete.test@fsp-russia.ru"


def test_connect_keycloak_candidate_without_fsp(client: TestClient):
    """
    Simulates Keycloak SSO login for a candidate WITHOUT FSP history (fsp_id='').
    Verifies JIT provisioning with fsp_id=None, fsp_verified=False, zero achievements synced.
    """
    test_id_token = jwt.encode(
        {
            "sub": "kc-user-uuid-nonfsp",
            "email": "candidate.nofsp@fsp-russia.ru",
            "given_name": "Федор",
            "family_name": "Федотов",
            "fsp_id": "",
        },
        key="test_key",
        algorithm="HS256",
    )

    fake_kc_response = httpx.Response(
        status_code=200,
        json={
            "access_token": "mock_kc_access_token",
            "id_token": test_id_token,
            "refresh_token": "mock_kc_refresh_token",
            "token_type": "Bearer",
            "expires_in": 300,
        },
        request=httpx.Request("POST", "http://keycloak:8080/auth/realms/fsp-realm/protocol/openid-connect/token"),
    )

    with patch("httpx.AsyncClient.post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = fake_kc_response

        resp = client.post(
            "/api/v1/fsp-integration/connect",
            json={
                "code": "real_kc_code_nofsp_456",
                "redirect_uri": "http://localhost:3000/auth/fsp/callback",
                "code_verifier": "valid_pkce_verifier_longer_than_ten_chars",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["fsp_id"] == ""
        assert data["fsp_verified"] is False
        assert data["achievements_synced"] == 0
        assert data["access_token"] is not None

        headers = {"Authorization": f"Bearer {data['access_token']}"}
        prof_resp = client.get("/api/v1/fsp-integration/profile", headers=headers)
        assert prof_resp.status_code == 200
        assert prof_resp.json()["is_fsp_candidate"] is False
        assert prof_resp.json()["fsp_id"] is None
        assert prof_resp.json()["badge_title"] == "Платформенная верификация"


def test_connect_invalid_pkce_verifier_returns_400(client: TestClient):
    """Verifies that mismatched PKCE verifier returns HTTP 400."""
    verifier = "fsp_test_pkce_verifier_correct_128_chars_long_string"
    challenge = generate_code_challenge(verifier)

    auth_resp = client.get(
        "/api/v1/fsp-integration/authorize",
        params={
            "response_type": "code",
            "client_id": "fsp-frontend",
            "redirect_uri": "http://localhost:3000/auth/fsp/callback",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "fsp_id": "FSP-77-01042",
        },
    )
    assert auth_resp.status_code == 200
    code = auth_resp.json()["code"]

    conn_resp = client.post(
        "/api/v1/fsp-integration/connect",
        json={
            "code": code,
            "redirect_uri": "http://localhost:3000/auth/fsp/callback",
            "code_verifier": "wrong_verifier_mismatched_hash_value",
        },
    )
    assert conn_resp.status_code == 400


def test_connect_existing_authenticated_user_profile_linking(client: TestClient):
    """
    Verifies that when an already authenticated user calls /connect with Bearer header,
    their existing candidate profile is linked to FSP ID.
    """
    # 1. Register candidate user
    reg_resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": "existing.cand@example.com",
            "password": "Password123!",
            "role": "candidate",
            "first_name": "Иван",
            "last_name": "Иванов",
            "consent_pdn_processing": True,
            "consent_profile_publication": True,
        },
    )
    assert reg_resp.status_code == 201
    token = reg_resp.json()["tokens"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Authorize mock code
    verifier = "pkce_verifier_for_existing_candidate_linking_flow"
    challenge = generate_code_challenge(verifier)
    auth_resp = client.get(
        "/api/v1/fsp-integration/authorize",
        params={
            "response_type": "code",
            "client_id": "fsp-frontend",
            "redirect_uri": "http://localhost:3000/auth/fsp/callback",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "fsp_id": "FSP-78-02091",
        },
    )
    assert auth_resp.status_code == 200
    code = auth_resp.json()["code"]

    # 3. Connect with Bearer token
    conn_resp = client.post(
        "/api/v1/fsp-integration/connect",
        headers=headers,
        json={
            "code": code,
            "redirect_uri": "http://localhost:3000/auth/fsp/callback",
            "code_verifier": verifier,
        },
    )
    assert conn_resp.status_code == 200
    data = conn_resp.json()
    assert data["fsp_id"] == "FSP-78-02091"
    assert data["fsp_verified"] is True
    assert data["achievements_synced"] == 2
