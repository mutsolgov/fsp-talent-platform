"""
Integration Test Suite for REQ-28: Employer Profile Management API.
Tests GET /me, PUT /me, and GET /me/trust-status, including antifraud validation,
role-based access control, and 152-ФЗ compliance.
"""
from __future__ import annotations

import asyncio
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import event, text
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.base import Base
import app.models as _models  # noqa: F401
from scripts.seed_reference_data import seed_reference_data

TEST_DB_URL = "sqlite+aiosqlite:///./test_employer_profile_integration.db"
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
                for tbl in [
                    "invitations", "ats_integrations", "employer_needs",
                    "employer_profiles", "candidate_profiles", "user_consents", "users"
                ]:
                    try:
                        await session.execute(text(f"DELETE FROM {tbl}"))
                    except Exception:
                        pass
                await session.commit()

    asyncio.run(_setup())

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        asyncio.run(test_engine.dispose())


def _create_user_and_headers(client: TestClient, email: str, role: str, inn: str = "7707083893") -> dict:
    payload = {
        "email": email,
        "password": "StrongPassword123!",
        "role": role,
        "first_name": "Иван",
        "last_name": "Тестов",
        "consent_pdn_processing": True,
        "consent_profile_publication": True,
    }
    if role == "employer":
        payload["company_name"] = "ООО Тестовая Компания"
        payload["inn"] = inn

    reg_resp = client.post("/api/v1/auth/register", json=payload)
    assert reg_resp.status_code == 201, f"Register failed: {reg_resp.text}"
    token = reg_resp.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_employer_profile_unauthorized(client: TestClient):
    """GET /api/v1/employer-profiles/me without token -> 401."""
    resp = client.get("/api/v1/employer-profiles/me")
    assert resp.status_code == 401


def test_employer_profile_candidate_forbidden(client: TestClient):
    """Candidate accessing employer profile -> 403."""
    headers = _create_user_and_headers(client, "candidate.user@example.com", role="candidate")
    resp = client.get("/api/v1/employer-profiles/me", headers=headers)
    assert resp.status_code == 403
    assert "ERR_EMPLOYER_ROLE_REQUIRED" in resp.text


def test_get_employer_profile_success(client: TestClient):
    """Employer successfully fetches own profile with 200 and all fields."""
    headers = _create_user_and_headers(client, "employer.one@example.com", role="employer", inn="7707083893")
    resp = client.get("/api/v1/employer-profiles/me", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["company_name"] == "ООО Тестовая Компания"
    assert data["inn"] == "7707083893"
    assert data["is_inn_verified"] is True
    assert data["trust_score"] >= 50
    assert data["invite_daily_limit"] == 20
    assert data["invites_sent_today"] == 0
    assert data["city"] == "Москва"
    assert "last_invite_reset_at" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert data["active_needs_count"] == 0
    assert data["ats_connected"] is False


def test_update_employer_profile_success(client: TestClient):
    """PUT /api/v1/employer-profiles/me updates profile fields and returns updated object."""
    headers = _create_user_and_headers(client, "employer.update@example.com", role="employer", inn="7707083893")

    update_payload = {
        "company_name": "ООО Яндекс Технологии",
        "inn": "7736207543",
        "domain": "yandex.ru.corporate.io",
        "city": "Санкт-Петербург",
        "website": "https://company.ru",
        "description": "Ведущая технологическая корпорация",
    }
    resp = client.put("/api/v1/employer-profiles/me", headers=headers, json=update_payload)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["company_name"] == "ООО Яндекс Технологии"
    assert data["inn"] == "7736207543"
    assert data["domain"] == "yandex.ru.corporate.io"
    assert data["city"] == "Санкт-Петербург"
    assert data["website"] == "https://company.ru"
    assert data["description"] == "Ведущая технологическая корпорация"


def test_update_employer_profile_invalid_inn(client: TestClient):
    """PUT /api/v1/employer-profiles/me with checksum-invalid INN -> 422."""
    headers = _create_user_and_headers(client, "employer.badinn@example.com", role="employer", inn="7707083893")

    resp = client.put(
        "/api/v1/employer-profiles/me",
        headers=headers,
        json={"inn": "7707083890"},  # Invalid checksum
    )
    assert resp.status_code == 422
    assert "ERR_INVALID_INN" in resp.text


def test_update_employer_profile_forbidden_domain(client: TestClient):
    """PUT /api/v1/employer-profiles/me with public webmail domain like gmail.com -> 422."""
    headers = _create_user_and_headers(client, "employer.baddomain@example.com", role="employer", inn="7707083893")

    resp = client.put(
        "/api/v1/employer-profiles/me",
        headers=headers,
        json={"domain": "gmail.com"},
    )
    assert resp.status_code == 422
    assert "бесплатных почтовых сервисов" in (resp.json().get("message") or resp.json().get("detail", ""))


def test_get_employer_trust_status(client: TestClient):
    """GET /api/v1/employer-profiles/me/trust-status returns trust score and remaining quota."""
    headers = _create_user_and_headers(client, "employer.trust@example.com", role="employer", inn="7707083893")

    resp = client.get("/api/v1/employer-profiles/me/trust-status", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert "trust_score" in data
    assert data["is_inn_verified"] is True
    assert data["invite_daily_limit"] == 20
    assert data["invites_sent_today"] == 0
    assert data["remaining_invites_today"] == 20
    assert data["can_send_invites"] is True


def test_update_employer_profile_duplicate_inn_conflict(client: TestClient):
    """PUT /api/v1/employer-profiles/me with an INN already taken by another company -> 409."""
    headers1 = _create_user_and_headers(client, "employer.comp1@example.com", role="employer", inn="7707083893")
    headers2 = _create_user_and_headers(client, "employer.comp2@example.com", role="employer", inn="7736207543")

    resp = client.put(
        "/api/v1/employer-profiles/me",
        headers=headers2,
        json={"inn": "7707083893"},
    )
    assert resp.status_code == 409
    assert "ERR_INN_ALREADY_REGISTERED" in resp.text

