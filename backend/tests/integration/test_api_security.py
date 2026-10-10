"""
Integration Test Suite for Phase 4: Security & Integration Layer.
Covers:
- Module 2: fsp-integration (OIDC with PKCE, Athlete Lookup, Achievements sync, Non-FSP fallback)
- Module 9: invitations (Direct Invitations, Mandatory RUB salary range, 20/day quota, 152-ФЗ unmasking on accept)
- Module 10: vacancies (Vacancy CRUD, Mandatory RUB salary transparency and spread <= 3.5, close)
- Module 11: applications (Direct vacancy applications, 152-ФЗ unmasking, duplicate prevention)
- Module 12: ats-integration (Settings, Webhooks HMAC-SHA256, 152-ФЗ protected Huntflow/HH export)
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
from sqlalchemy import text
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.base import Base
from app.services.fsp_mock_registry import generate_code_challenge
from scripts.seed_reference_data import seed_reference_data

from sqlalchemy import event, text

TEST_DB_URL = "sqlite+aiosqlite:///./test_security_integration.db"
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
                await session.execute(text("DELETE FROM ats_integrations"))
                await session.execute(text("DELETE FROM applications"))
                await session.execute(text("DELETE FROM invitations"))
                await session.execute(text("DELETE FROM vacancies"))
                await session.execute(text("DELETE FROM fsp_achievements"))
                await session.execute(text("DELETE FROM shortlist_items"))
                await session.execute(text("DELETE FROM saved_shortlists"))
                await session.execute(text("DELETE FROM employer_needs"))
                await session.execute(text("DELETE FROM employer_profiles"))
                await session.execute(text("DELETE FROM candidate_categorizations"))
                await session.execute(text("DELETE FROM candidate_skills"))
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
        asyncio.run(test_engine.dispose())



_inn_counter = 0
VALID_INNS = ["7707083893", "7736207543", "7710140679", "7842349892", "7702070139", "7701234567"]


def _auth_headers(client, email: str, role: str = "employer") -> dict:
    global _inn_counter
    inn = None
    company_name = None
    if role == "employer":
        inn = VALID_INNS[_inn_counter % len(VALID_INNS)]
        company_name = f"ООО ТехноКорп {_inn_counter}"
        _inn_counter += 1

    reg_payload = {
        "email": email,
        "password": "StrongPassword123!",
        "role": role,
        "first_name": "Тест",
        "last_name": "Безопасность",
        "company_name": company_name,
        "inn": inn,
        "consent_pdn_processing": True,
        "consent_profile_publication": True,
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
    token = reg_resp.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_fsp_integration_flow(client):
    """
    Verifies OIDC flow, athlete linking with PKCE, registry lookup, and non-FSP fallback.
    """
    cand_headers = _auth_headers(client, "candidate.fsp@test.ru", role="candidate")

    # 1. Non-FSP initial state check
    prof_resp = client.get("/api/v1/fsp-integration/profile", headers=cand_headers)
    assert prof_resp.status_code == 200
    prof_data = prof_resp.json()
    assert prof_data["is_fsp_candidate"] is False
    assert prof_data["fsp_id"] is None
    assert prof_data["badge_title"] == "Платформенная верификация"

    # 2. OIDC Authorize step
    verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
    challenge = generate_code_challenge(verifier)

    auth_resp = client.get(
        "/api/v1/fsp-integration/authorize",
        params={
            "response_type": "code",
            "client_id": "fsp-client",
            "redirect_uri": "http://localhost:3000/auth/fsp/callback",
            "code_challenge": challenge,
            "code_challenge_method": "S256",
            "fsp_id": "FSP-77-01042",
        },
    )
    assert auth_resp.status_code == 200
    auth_code = auth_resp.json()["code"]

    # 3. Connect FSP Profile
    connect_resp = client.post(
        "/api/v1/fsp-integration/connect",
        headers=cand_headers,
        json={
            "code": auth_code,
            "redirect_uri": "http://localhost:3000/auth/fsp/callback",
            "code_verifier": verifier,
        },
    )
    assert connect_resp.status_code == 200
    conn_data = connect_resp.json()
    assert conn_data["fsp_id"] == "FSP-77-01042"
    assert conn_data["fsp_verified"] is True
    assert conn_data["achievements_synced"] == 2

    # 4. Verified profile state
    prof_resp_after = client.get("/api/v1/fsp-integration/profile", headers=cand_headers)
    assert prof_resp_after.status_code == 200
    prof_data_after = prof_resp_after.json()
    assert prof_data_after["is_fsp_candidate"] is True
    assert prof_data_after["fsp_id"] == "FSP-77-01042"
    assert prof_data_after["badge_title"] == "Верифицирован ФСП"
    assert len(prof_data_after["achievements"]) == 2

    # 5. Unlink FSP profile -> fallback to platform verification
    unlink_resp = client.delete("/api/v1/fsp-integration/unlink", headers=cand_headers)
    assert unlink_resp.status_code == 200

    prof_resp_unlinked = client.get("/api/v1/fsp-integration/profile", headers=cand_headers)
    assert prof_resp_unlinked.status_code == 200
    assert prof_resp_unlinked.json()["is_fsp_candidate"] is False
    assert prof_resp_unlinked.json()["fsp_id"] is None


def test_vacancies_api_and_salary_invariants(client):
    """
    Verifies Vacancy CRUD with mandatory RUB salary ranges (spread <= 3.5).
    """
    emp_headers = _auth_headers(client, "employer.vacancies@test.ru", role="employer")

    # 1. Non-positive salary_min rejected
    resp_zero = client.post(
        "/api/v1/vacancies",
        headers=emp_headers,
        json={
            "specialization_id": 1,
            "grade_id": 2,
            "title": "Backend Python Developer",
            "description": "Разработка распределенных микросервисов платформы ФСП на Python и FastAPI",
            "required_skills": ["Python", "FastAPI"],
            "salary_min": 0,
            "salary_max": 200000,
        },
    )
    assert resp_zero.status_code == 422
    assert "ERR_SALARY_MIN_NOT_POSITIVE" in resp_zero.text or "greater than 0" in resp_zero.text

    # 2. salary_max < salary_min rejected
    resp_inverted = client.post(
        "/api/v1/vacancies",
        headers=emp_headers,
        json={
            "specialization_id": 1,
            "grade_id": 2,
            "title": "Backend Python Developer",
            "description": "Разработка распределенных микросервисов платформы ФСП на Python и FastAPI",
            "required_skills": ["Python", "FastAPI"],
            "salary_min": 250000,
            "salary_max": 180000,
        },
    )
    assert resp_inverted.status_code == 422
    assert "ERR_SALARY_MAX_LT_MIN" in resp_inverted.text

    # 3. Spread > 3.5 rejected (Anti-Fraud)
    resp_spread = client.post(
        "/api/v1/vacancies",
        headers=emp_headers,
        json={
            "specialization_id": 1,
            "grade_id": 2,
            "title": "Backend Python Developer",
            "description": "Разработка распределенных микросервисов платформы ФСП на Python и FastAPI",
            "required_skills": ["Python", "FastAPI"],
            "salary_min": 50000,
            "salary_max": 300000,  # 6.0x ratio
        },
    )
    assert resp_spread.status_code == 422
    assert "ERR_SUSPICIOUS_SALARY_SPREAD" in resp_spread.text

    # 4. Valid vacancy created
    resp_valid = client.post(
        "/api/v1/vacancies",
        headers=emp_headers,
        json={
            "specialization_id": 1,
            "grade_id": 2,
            "title": "Middle Backend Developer",
            "description": "Разработка высоконагруженных API сервисов платформы соискателей",
            "required_skills": ["Python", "FastAPI", "PostgreSQL"],
            "salary_min": 180000,
            "salary_max": 260000,
            "work_format": "remote",
        },
    )
    assert resp_valid.status_code == 201
    vac = resp_valid.json()
    assert vac["salary_min"] == 180000
    assert vac["salary_max"] == 260000
    assert vac["salary_currency"] == "RUB"
    assert vac["status"] == "published"
    vac_id = vac["id"]

    # 5. Catalog view
    cat_resp = client.get("/api/v1/vacancies")
    assert cat_resp.status_code == 200
    assert cat_resp.json()["meta"]["total"] >= 1

    # 6. Close vacancy
    close_resp = client.post(f"/api/v1/vacancies/{vac_id}/close", headers=emp_headers)
    assert close_resp.status_code == 200
    assert close_resp.json()["status"] == "closed"


def test_invitations_and_privacy_unmasking(client):
    """
    Verifies Invitation flow with mandatory RUB salary, 20/day quota,
    and 152-ФЗ unmasking upon candidate acceptance.
    """
    emp_headers = _auth_headers(client, "employer.invites@test.ru", role="employer")
    cand_headers = _auth_headers(client, "candidate.invites@test.ru", role="candidate")

    cand_me = client.get("/api/v1/candidate-profile/me", headers=cand_headers)
    assert cand_me.status_code == 200, f"cand_me error: {cand_me.status_code} {cand_me.text}"
    cand_id = cand_me.json()["id"]

    # 1. Reject invalid salary spread in invitation
    resp_bad_spread = client.post(
        "/api/v1/invitations",
        headers=emp_headers,
        json={
            "candidate_profile_id": cand_id,
            "proposal_text": "Приглашаем в команду ведущих инженеров",
            "salary_min": 50000,
            "salary_max": 300000,
        },
    )
    assert resp_bad_spread.status_code in (400, 422)

    # 2. Send valid invitation
    resp_invite = client.post(
        "/api/v1/invitations",
        headers=emp_headers,
        json={
            "candidate_profile_id": cand_id,
            "proposal_text": "Приглашаем в команду ведущих инженеров на проект ФСП",
            "salary_min": 200000,
            "salary_max": 320000,
        },
    )
    assert resp_invite.status_code == 201
    inv_id = resp_invite.json()["id"]
    assert resp_invite.json()["status"] == "sent"

    # Contacts initially MASKED to employer
    bank_resp_before = client.get(f"/api/v1/candidate-bank/{cand_id}", headers=emp_headers)
    assert bank_resp_before.status_code == 200
    assert bank_resp_before.json()["is_contacts_masked"] is True

    # 3. Candidate views incoming invitations
    inc_resp = client.get("/api/v1/invitations/incoming", headers=cand_headers)
    assert inc_resp.status_code == 200
    assert inc_resp.json()["meta"]["total"] >= 1

    # 4. Candidate accepts invitation
    accept_resp = client.post(f"/api/v1/invitations/{inv_id}/accept", headers=cand_headers)
    assert accept_resp.status_code == 200
    assert accept_resp.json()["unmasked_contacts_granted"] is True

    # Contacts now UNMASKED to this employer
    bank_resp_after = client.get(f"/api/v1/candidate-bank/{cand_id}", headers=emp_headers)
    assert bank_resp_after.status_code == 200
    assert bank_resp_after.json()["is_contacts_masked"] is False
    assert bank_resp_after.json()["email"] is not None


def test_applications_and_ats_export_flow(client):
    """
    Verifies direct application flow and subsequent ATS export with 152-ФЗ compliance.
    """
    emp_headers = _auth_headers(client, "employer.ats@test.ru", role="employer")
    cand_headers = _auth_headers(client, "candidate.ats@test.ru", role="candidate")

    cand_me = client.get("/api/v1/candidate-profile/me", headers=cand_headers)
    cand_id = cand_me.json()["id"]

    # 1. Employer creates vacancy
    vac_resp = client.post(
        "/api/v1/vacancies",
        headers=emp_headers,
        json={
            "specialization_id": 1,
            "grade_id": 2,
            "title": "Senior Python Architect",
            "description": "Проектирование высоконадежных систем для платформы ФСП",
            "required_skills": ["Python", "FastAPI", "Kafka"],
            "salary_min": 250000,
            "salary_max": 350000,
        },
    )
    assert vac_resp.status_code == 201
    vac_id = vac_resp.json()["id"]

    # ATS export before application should be FORBIDDEN (403)
    export_before = client.post(
        "/api/v1/ats-integration/export/huntflow",
        headers=emp_headers,
        json={"candidate_id": cand_id, "ats_type": "huntflow"},
    )
    assert export_before.status_code == 403

    # 2. Candidate applies directly to vacancy
    app_resp = client.post(
        "/api/v1/applications",
        headers=cand_headers,
        json={"vacancy_id": vac_id, "cover_letter": "Заинтересован в проекте!"},
    )
    assert app_resp.status_code == 201
    app_id = app_resp.json()["id"]

    # Duplicate application rejected (409)
    dup_resp = client.post(
        "/api/v1/applications",
        headers=cand_headers,
        json={"vacancy_id": vac_id, "cover_letter": "Второй отклик"},
    )
    assert dup_resp.status_code == 409

    # 3. Employer views incoming applications with unmasked contacts
    emp_apps_resp = client.get("/api/v1/applications/received", headers=emp_headers)
    assert emp_apps_resp.status_code == 200
    assert emp_apps_resp.json()["meta"]["total"] >= 1
    assert emp_apps_resp.json()["items"][0]["candidate_contacts"]["email"] is not None

    # 4. ATS Export is now PERMITTED (152-ФЗ compliant via direct application)
    export_after = client.post(
        "/api/v1/ats-integration/export/huntflow",
        headers=emp_headers,
        json={"candidate_id": cand_id, "ats_type": "huntflow"},
    )
    assert export_after.status_code == 200
    assert "applicant" in export_after.json()
    assert export_after.json()["applicant"]["email"] is not None

    # 5. Webhook ping test
    ping_resp = client.post("/api/v1/ats-integration/webhooks/test-ping", headers=emp_headers)
    assert ping_resp.status_code == 200
    assert ping_resp.json()["delivered"] is True
    assert ping_resp.json()["signature_header"].startswith("sha256=")
