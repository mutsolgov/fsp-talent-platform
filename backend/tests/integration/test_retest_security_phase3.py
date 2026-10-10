"""
Retest Adversarial Security Suite for Phase 3:
Exhaustively probes Defect 1 (Currency Invariant), Defect 2 (Multi-Employer Registration & Lazy Creation),
and re-verifies 152-ФЗ Privacy Barrier, Multi-Tenant Isolation, and Salary Spread Bounds.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time

backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy import event, text, select
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.base import Base
import app.models as _models  # noqa: F401
from app.models.employer_profiles import EmployerProfile
from app.models.candidate_profiles import CandidateProfile
from app.models.invitations import Invitation
from app.core.security import generate_valid_inn, get_password_hash
from scripts.seed_reference_data import seed_reference_data

TEST_DB_URL = "sqlite+aiosqlite:///./test_retest_security.db"
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
                    "ats_webhook_logs", "ats_integrations",
                    "challenge_submissions", "micro_challenges",
                    "cooldown_resets", "assessment_answers", "assessment_sessions",
                    "audit_logs",
                    "applications", "invitations", "vacancies", "fsp_achievements",
                    "shortlist_items", "saved_shortlists", "employer_needs",
                    "employer_profiles", "candidate_categorizations",
                    "candidate_skills", "candidate_profiles", "user_consents", "users"
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



_seq_counter = int(time.time() * 10) % 800000 + 10000


def _auth_headers(client, email: str, role: str = "employer") -> dict:
    global _seq_counter
    inn = None
    company_name = None
    if role == "employer":
        inn = generate_valid_inn(_seq_counter)
        company_name = f"АО ТестКорп {_seq_counter}"
        _seq_counter += 1

    reg_payload = {
        "email": email,
        "password": "StrongPassword123!",
        "role": role,
        "first_name": "Иван",
        "last_name": "Тестов",
        "company_name": company_name,
        "inn": inn,
        "consent_pdn_processing": True,
        "consent_profile_publication": True,
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    if reg_resp.status_code == 201:
        token = reg_resp.json()["tokens"]["access_token"]
    elif reg_resp.status_code == 409:
        login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "StrongPassword123!"})
        token = login_resp.json()["access_token"]
    else:
        assert False, f"Auth failed for {email}: {reg_resp.text}"

    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# DEFECT 1: SALARY CURRENCY REJECTION PROBES (POST & PUT)
# ==============================================================================


def test_retest_probe_defect_1_post_employer_needs_non_rub_rejected(client):
    """
    Adversarial Retest 1.1:
    POST /api/v1/employer-needs must strictly reject non-RUB currencies with 422.
    """
    emp_headers = _auth_headers(client, "emp.probe_post@corp.ru", role="employer")

    forbidden_currencies = ["USD", "EUR", "GBP", "CNY", "KZT", "JPY", "rub", "Rub", ""]
    for curr in forbidden_currencies:
        payload = {
            "specialization_id": 1,
            "target_grade_id": 2,
            "title": f"Need {curr}",
            "team_tasks_text": "Задачи бэкенда",
            "salary_min": 100000,
            "salary_max": 200000,
            "salary_currency": curr,
            "work_format": "remote",
        }
        res = client.post("/api/v1/employer-needs", headers=emp_headers, json=payload)
        assert res.status_code == 422, (
            f"Expected 422 Unprocessable Entity for salary_currency='{curr}', "
            f"got {res.status_code}: {res.text}"
        )
        assert ("ERR_INVALID_CURRENCY" in res.text or "RUB" in res.text or "ERR_VALIDATION_ERROR" in res.text), (
            f"Expected validation error referencing currency/RUB for '{curr}', got: {res.text}"
        )

    # Valid RUB payload must be accepted with 201
    valid_payload = {
        "specialization_id": 1,
        "target_grade_id": 2,
        "title": "Need Valid RUB",
        "team_tasks_text": "Задачи бэкенда",
        "salary_min": 100000,
        "salary_max": 200000,
        "salary_currency": "RUB",
        "work_format": "remote",
    }
    valid_res = client.post("/api/v1/employer-needs", headers=emp_headers, json=valid_payload)
    assert valid_res.status_code == 201
    assert valid_res.json()["salary_currency"] == "RUB"


def test_retest_probe_defect_1_put_employer_needs_non_rub_rejected(client):
    """
    Adversarial Retest 1.2:
    PUT /api/v1/employer-needs/{id} must strictly reject non-RUB currencies with 422.
    """
    emp_headers = _auth_headers(client, "emp.probe_put@corp.ru", role="employer")

    # Create baseline need
    create_res = client.post(
        "/api/v1/employer-needs",
        headers=emp_headers,
        json={
            "specialization_id": 1,
            "target_grade_id": 2,
            "title": "Base Need for PUT",
            "team_tasks_text": "Tasks",
            "salary_min": 120000,
            "salary_max": 220000,
            "salary_currency": "RUB",
            "work_format": "remote",
        },
    )
    assert create_res.status_code == 201
    need_id = create_res.json()["id"]

    forbidden_currencies = ["USD", "EUR", "GBP", "CNY", "KZT", "JPY", "rub"]
    for curr in forbidden_currencies:
        update_payload = {
            "salary_currency": curr,
        }
        res = client.put(f"/api/v1/employer-needs/{need_id}", headers=emp_headers, json=update_payload)
        assert res.status_code == 422, (
            f"Expected 422 for PUT with salary_currency='{curr}', "
            f"got {res.status_code}: {res.text}"
        )
        assert ("ERR_INVALID_CURRENCY" in res.text or "RUB" in res.text or "ERR_VALIDATION_ERROR" in res.text), (
            f"Expected validation error referencing currency/RUB in PUT response for '{curr}', got: {res.text}"
        )

    # Valid PUT with RUB must succeed
    valid_res = client.put(
        f"/api/v1/employer-needs/{need_id}",
        headers=emp_headers,
        json={"salary_min": 130000, "salary_max": 250000, "salary_currency": "RUB"},
    )
    assert valid_res.status_code == 200
    assert valid_res.json()["salary_min"] == 130000
    assert valid_res.json()["salary_max"] == 250000
    assert valid_res.json()["salary_currency"] == "RUB"


# ==============================================================================
# DEFECT 2: MULTI-EMPLOYER REGISTRATION & NO INN COLLISION
# ==============================================================================


def test_retest_probe_defect_2_multiple_employers_no_collision_and_full_workflow(client):
    """
    Adversarial Retest 2.1:
    Register 8 employers with distinct valid INNs.
    Perform actions for all:
    - create employer need
    - list employer needs
    - search candidate bank
    Confirm NO collision on employer_profiles.inn and NO HTTP 500 error occurs.
    """
    employers_tokens = []

    for i in range(1, 9):
        custom_inn = generate_valid_inn(800000 + i)
        email = f"emp.explicit_{i}@firm{i}.ru"
        res = client.post(
            "/api/v1/auth/register",
            json={
                "email": email,
                "password": "StrongPassword123!",
                "role": "employer",
                "company_name": f"ООО Фирма #{i}",
                "inn": custom_inn,
                "consent_pdn_processing": True,
                "consent_profile_publication": True,
            },
        )
        assert res.status_code == 201, f"Failed to register employer {email}: {res.text}"
        token = res.json()["tokens"]["access_token"]
        employers_tokens.append((email, token, custom_inn))

    # For each employer, perform full workflow: list needs, create need, search candidate bank
    created_needs = []
    for idx, (email, token, exp_inn) in enumerate(employers_tokens):
        headers = {"Authorization": f"Bearer {token}"}

        # List needs (initially empty)
        list_res = client.get("/api/v1/employer-needs", headers=headers)
        assert list_res.status_code == 200, f"Employer {email} failed to list needs: {list_res.text}"
        assert list_res.json()["meta"]["total"] == 0

        # Create need
        need_payload = {
            "specialization_id": 1,
            "target_grade_id": 2,
            "title": f"Позиция для работодателя {email}",
            "team_tasks_text": "Разработка микросервисов",
            "salary_min": 100000 + idx * 10000,
            "salary_max": 200000 + idx * 10000,
            "salary_currency": "RUB",
            "work_format": "remote",
        }
        create_res = client.post("/api/v1/employer-needs", headers=headers, json=need_payload)
        assert create_res.status_code == 201, (
            f"Employer {email} got status {create_res.status_code} on create need: {create_res.text}"
        )
        need_data = create_res.json()
        assert need_data["id"] is not None
        created_needs.append((email, need_data["id"]))

        # Search candidate bank
        bank_res = client.get("/api/v1/candidate-bank?specialization_id=1&grade_id=2", headers=headers)
        assert bank_res.status_code == 200, f"Employer {email} failed bank search: {bank_res.text}"

        # Verify own list has 1 item
        own_list = client.get("/api/v1/employer-needs", headers=headers)
        assert own_list.status_code == 200
        assert own_list.json()["meta"]["total"] == 1

    # Check DB-level uniqueness and absence of collisions
    async def _verify_db_profiles():
        async with test_session_factory() as session:
            stmt = select(EmployerProfile)
            profiles = list((await session.execute(stmt)).scalars().all())
            assert len(profiles) == len(employers_tokens), (
                f"Expected {len(employers_tokens)} profiles, found {len(profiles)}"
            )
            inns = [p.inn for p in profiles]
            assert len(set(inns)) == len(inns), f"Duplicate INNs found in database: {inns}"
            for p in profiles:
                assert len(p.inn) == 10, f"Invalid INN length {p.inn}"
                assert p.company_name, "Empty company name"

    asyncio.run(_verify_db_profiles())


def test_retest_probe_defect_2_deps_lazy_fallback_uniqueness(client):
    """
    Adversarial Retest 2.2:
    Simulate scenario where an employer user exists in users table without an EmployerProfile
    and calls employer endpoints. deps.get_current_employer must lazily create unique valid profiles
    without crashing on INN uniqueness.
    """
    async def _create_bare_users():
        created_users = []
        async with test_session_factory() as session:
            for i in range(1, 4):
                user = _models.users.User(
                    email=f"bare_emp_{i}@auto.ru",
                    hashed_password=get_password_hash("StrongPassword123!"),
                    role="employer",
                    is_active=True,
                    email_verified=True,
                )
                session.add(user)
                await session.flush()
                created_users.append((user.id, user.email))
            await session.commit()
        return created_users

    bare_users = asyncio.run(_create_bare_users())

    # For each bare user, log in and access an employer endpoint
    for uid, email in bare_users:
        login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "StrongPassword123!"})
        assert login_res.status_code == 200
        token = login_res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Access endpoint that triggers get_current_employer
        res = client.get("/api/v1/employer-needs", headers=headers)
        assert res.status_code == 200, f"Bare user {email} failed get_current_employer: {res.text}"

    # Verify that distinct profiles were created
    async def _check_profiles():
        async with test_session_factory() as session:
            stmt = select(EmployerProfile).where(
                EmployerProfile.user_id.in_([u[0] for u in bare_users])
            )
            profs = list((await session.execute(stmt)).scalars().all())
            assert len(profs) == len(bare_users)
            inns = [p.inn for p in profs]
            assert len(set(inns)) == len(inns), f"Duplicate lazy INNs: {inns}"

    asyncio.run(_check_profiles())


# ==============================================================================
# RE-VERIFICATION: 152-ФЗ PRIVACY BARRIER & MULTI-TENANT ISOLATION
# ==============================================================================


def test_retest_invariant_152fz_privacy_and_unmasking_barrier(client):
    """
    Adversarial Retest 3.1:
    Re-verify complete 152-ФЗ privacy lifecycle:
    1. Candidate Bank Card masks all personal data.
    2. Candidate Anonymized Detail masks all personal data until acceptance.
    3. GET /candidate-bank/{id}/contacts returns 403 Forbidden until acceptance.
    4. Upon acceptance by Employer A, Employer A gets unmasked contacts.
    5. Employer B STILL gets 403 Forbidden and masked detail (Multi-Tenant Isolation).
    """
    # 1. Candidate setup
    cand_headers = _auth_headers(client, "cand.privacy_retest@fsp.ru", role="candidate")
    surv_res = client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        headers=cand_headers,
        json={"specialization_id": 1, "claimed_grade_id": 2, "skills": ["python", "fastapi"]},
    )
    assert surv_res.status_code == 201

    cand_me = client.get("/api/v1/candidate-profile/me", headers=cand_headers).json()
    cand_id = cand_me["id"]

    # 2. Employer A and Employer B setup
    emp_a_headers = _auth_headers(client, "emp.firm_a@corp.ru", role="employer")
    emp_b_headers = _auth_headers(client, "emp.firm_b@corp.ru", role="employer")

    # 3. Bank Search (Employer A)
    search_res = client.get("/api/v1/candidate-bank/search?specialization_id=1", headers=emp_a_headers)
    assert search_res.status_code == 200
    card = next((c for c in search_res.json()["items"] if c["id"] == cand_id), None)
    assert card is not None
    assert card.get("email") is None
    assert card.get("phone") is None
    assert card.get("telegram") is None
    assert card.get("github_url") is None
    assert card.get("raw_resume_pdf_url") is None
    assert card.get("is_contacts_unmasked") is False

    # 4. Anonymized Detail (Employer A)
    detail_res = client.get(f"/api/v1/candidate-bank/{cand_id}", headers=emp_a_headers)
    assert detail_res.status_code == 200
    detail = detail_res.json()
    assert detail["is_contacts_masked"] is True
    assert detail["email"] is None
    assert detail["phone"] is None
    assert detail["telegram"] is None
    assert detail["github_url"] is None

    # 5. Contacts Barrier 403 (Employer A)
    contacts_barrier = client.get(f"/api/v1/candidate-bank/{cand_id}/contacts", headers=emp_a_headers)
    assert contacts_barrier.status_code == 403
    assert "152-ФЗ" in str(contacts_barrier.json()) or "152" in contacts_barrier.text

    # 6. Employer A sends invitation
    inv_res = client.post(
        "/api/v1/invitations",
        headers=emp_a_headers,
        json={
            "candidate_profile_id": cand_id,
            "proposal_text": "Приглашение на собеседование в Фирму А",
            "salary_min": 150000,
            "salary_max": 250000,
        },
    )
    assert inv_res.status_code == 201
    inv_id = inv_res.json()["id"]

    # While status is 'sent', contacts are STILL 403
    barrier_sent = client.get(f"/api/v1/candidate-bank/{cand_id}/contacts", headers=emp_a_headers)
    assert barrier_sent.status_code == 403

    # 7. Candidate accepts Employer A's invitation
    accept_res = client.post(f"/api/v1/invitations/{inv_id}/accept", headers=cand_headers)
    assert accept_res.status_code == 200
    assert accept_res.json()["status"] == "accepted"

    # 8. Employer A now calls GET /contacts -> 200 OK unmasked
    unmasked_res = client.get(f"/api/v1/candidate-bank/{cand_id}/contacts", headers=emp_a_headers)
    assert unmasked_res.status_code == 200
    unmasked = unmasked_res.json()
    assert unmasked["email"] is not None
    assert "@" in unmasked["email"]
    assert unmasked["unmasked_reason"] == "invitation_accepted"

    # 9. Multi-Tenant Barrier: Employer B calls GET /contacts -> MUST BE 403 FORBIDDEN!
    emp_b_barrier = client.get(f"/api/v1/candidate-bank/{cand_id}/contacts", headers=emp_b_headers)
    assert emp_b_barrier.status_code == 403, (
        f"Multi-tenant violation: Employer B was able to access unmasked contacts! {emp_b_barrier.text}"
    )

    # Employer B detail view must still be masked
    emp_b_detail = client.get(f"/api/v1/candidate-bank/{cand_id}", headers=emp_b_headers).json()
    assert emp_b_detail["is_contacts_masked"] is True
    assert emp_b_detail["email"] is None
    assert emp_b_detail["phone"] is None


# ==============================================================================
# RE-VERIFICATION: SALARY BOUNDS & SPREAD INVARIANTS
# ==============================================================================


def test_retest_salary_bounds_and_spread_invariants(client):
    """
    Adversarial Retest 4.1:
    Verify salary constraints:
    - min <= 0 -> 422
    - max < min -> 422
    - spread > 3.5 -> 422
    - spread == 3.5 -> 201
    """
    emp_headers = _auth_headers(client, "emp.salary_bounds@corp.ru", role="employer")

    cases = [
        (0, 100000, 422, "non-positive min"),
        (-5000, 100000, 422, "negative min"),
        (200000, 150000, 422, "max < min"),
        (100000, 350001, 422, "spread 3.50001 > 3.5"),
        (100000, 400000, 422, "spread 4.0 > 3.5"),
        (100000, 350000, 201, "spread 3.5 valid boundary"),
        (200000, 200000, 201, "spread 1.0 exact match"),
    ]

    for s_min, s_max, exp_code, label in cases:
        payload = {
            "specialization_id": 1,
            "target_grade_id": 2,
            "title": f"Need {label}",
            "team_tasks_text": "Tasks",
            "salary_min": s_min,
            "salary_max": s_max,
            "salary_currency": "RUB",
            "work_format": "remote",
        }
        res = client.post("/api/v1/employer-needs", headers=emp_headers, json=payload)
        assert res.status_code == exp_code, (
            f"Case '{label}' (min={s_min}, max={s_max}): expected {exp_code}, got {res.status_code} ({res.text})"
        )
