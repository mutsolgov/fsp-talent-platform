"""
Adversarial Security & Invariants Test Suite for Phase 3:
1. 152-ФЗ Contact Privacy Barrier & Multi-Tenant Isolation
2. Salary Range Invariants (API boundaries & DB CheckConstraints)
3. Live matched_candidates_count Database Reflection
"""
from __future__ import annotations

import asyncio
import os
import sys
import time

# Ensure backend directory is in sys.path
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
from scripts.seed_reference_data import seed_reference_data

TEST_DB_URL = "sqlite+aiosqlite:///./test_adversarial_security.db"
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


def make_valid_inn(seq: int) -> str:
    """Generates guaranteed mathematically valid Russian INN with correct checksum."""
    base = f"77{seq:07d}"
    digits = [int(d) for d in base]
    weights = [2, 4, 10, 3, 5, 9, 4, 6, 8]
    c10 = (sum(d * w for d, w in zip(digits, weights)) % 11) % 10
    return f"{base}{c10}"


def _auth_headers(client, email: str, role: str = "employer") -> dict:
    global _seq_counter
    inn = None
    company_name = None
    if role == "employer":
        inn = make_valid_inn(_seq_counter)
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
        user_id = reg_resp.json()["user_id"]
    elif reg_resp.status_code == 409:
        login_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "StrongPassword123!"})
        token = login_resp.json()["access_token"]
        user_id = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"}).json()["id"]
    else:
        assert False, f"Auth failed for {email}: {reg_resp.text}"

    if role == "employer":
        async def _ensure_profile():
            async with test_session_factory() as session:
                stmt = select(EmployerProfile).where(EmployerProfile.user_id == user_id)
                prof = (await session.execute(stmt)).scalar_one_or_none()
                if not prof:
                    domain_name = email.split("@")[1] if "@" in email else "corp.ru"
                    session.add(EmployerProfile(
                        user_id=user_id,
                        company_name=company_name or "АО Компания",
                        inn=inn or make_valid_inn(888888),
                        domain=domain_name,
                        is_inn_verified=True,
                        trust_score=85,
                    ))
                    await session.commit()
        asyncio.run(_ensure_profile())

    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# SECTION 1: 152-ФЗ Contact Privacy Barrier & Multi-Tenant Isolation
# ==============================================================================


def test_152fz_candidate_bank_card_zero_contact_leakage(client):
    """
    Adversarial Check 1.1:
    In search results (/candidate-bank and /candidate-bank/search), CandidateBankCard
    must NEVER contain candidate contact fields (email, phone, telegram, github_url, raw resume PDF).
    Name must be masked: 'Имя Ф. (#C-123)'.
    is_contacts_unmasked must be False.
    """
    cand_headers = _auth_headers(client, "cand.privacy1@fsp.ru", role="candidate")
    survey_res = client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        headers=cand_headers,
        json={
            "specialization_id": 1,
            "claimed_grade_id": 2,
            "skills": ["python", "postgresql"],
            "city": "Москва",
            "work_format": "remote",
        },
    )
    assert survey_res.status_code == 201

    # Update profile with sensitive contacts
    client.patch(
        "/api/v1/candidate-profile/me",
        headers=cand_headers,
        json={
            "phone": "+7 (999) 111-22-33",
            "telegram": "@secret_candidate",
            "github_url": "https://github.com/secret_candidate",
        },
    )

    emp_headers = _auth_headers(client, "emp.privacy1@fsp.ru", role="employer")
    search_res = client.get("/api/v1/candidate-bank?specialization=backend", headers=emp_headers)
    assert search_res.status_code == 200
    items = search_res.json()["items"]
    assert len(items) >= 1

    card = items[0]
    forbidden_keys = ["email", "phone", "telegram", "github_url", "raw_resume_pdf_url", "raw_resume_pdf_path"]
    for key in forbidden_keys:
        assert key not in card or card[key] is None, f"Leak detected: {key} in CandidateBankCard!"

    # Verify masked name
    assert "(#C-" in card["masked_full_name"]
    assert card["is_contacts_unmasked"] is False


def test_152fz_anonymized_detail_zero_leakage_until_accepted(client):
    """
    Adversarial Check 1.2:
    GET /candidate-bank/{id} must keep is_contacts_masked=True and contact fields None
    under all preliminary states:
    - No invitation sent
    - Invitation sent but status='sent'
    - Invitation declined status='declined'
    - Other candidate trying to view (must return 403)
    """
    cand_headers = _auth_headers(client, "cand.privacy2@fsp.ru", role="candidate")
    client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        headers=cand_headers,
        json={"specialization_id": 1, "claimed_grade_id": 2, "skills": ["python"]},
    )
    client.patch(
        "/api/v1/candidate-profile/me",
        headers=cand_headers,
        json={
            "phone": "+7 (999) 777-88-99",
            "telegram": "@privacy_tester",
            "github_url": "https://github.com/privacy_tester",
        },
    )

    cand_me = client.get("/api/v1/candidate-profile/me", headers=cand_headers).json()
    cand_id = cand_me["id"]

    emp_headers = _auth_headers(client, "emp.privacy2@fsp.ru", role="employer")

    # State A: No invitation
    det_a = client.get(f"/api/v1/candidate-bank/{cand_id}", headers=emp_headers).json()
    assert det_a["is_contacts_masked"] is True
    assert det_a["email"] is None
    assert det_a["phone"] is None
    assert det_a["telegram"] is None
    assert det_a["github_url"] is None
    assert det_a["raw_resume_pdf_url"] is None
    assert "(#C-" in det_a["masked_full_name"]

    contacts_a = client.get(f"/api/v1/candidate-bank/{cand_id}/contacts", headers=emp_headers)
    assert contacts_a.status_code == 403

    # State B: Invitation sent (status == 'sent')
    inv_res = client.post(
        "/api/v1/invitations",
        headers=emp_headers,
        json={
            "candidate_profile_id": cand_id,
            "proposal_text": "Приглашение на собеседование в финтех",
            "salary_min": 220000,
            "salary_max": 330000,
        },
    )
    assert inv_res.status_code == 201
    inv_id = inv_res.json()["id"]

    det_b = client.get(f"/api/v1/candidate-bank/{cand_id}", headers=emp_headers).json()
    assert det_b["is_contacts_masked"] is True
    assert det_b["email"] is None
    assert det_b["phone"] is None
    assert det_b["telegram"] is None
    assert det_b["github_url"] is None
    assert det_b["raw_resume_pdf_url"] is None

    contacts_b = client.get(f"/api/v1/candidate-bank/{cand_id}/contacts", headers=emp_headers)
    assert contacts_b.status_code == 403

    # State C: Candidate declines invitation
    decline_res = client.post(
        f"/api/v1/invitations/{inv_id}/decline",
        headers=cand_headers,
        json={"decline_reason": "Not interested at this time"},
    )
    assert decline_res.status_code == 200

    det_c = client.get(f"/api/v1/candidate-bank/{cand_id}", headers=emp_headers).json()
    assert det_c["is_contacts_masked"] is True
    assert det_c["email"] is None
    assert det_c["phone"] is None
    assert det_c["telegram"] is None

    contacts_c = client.get(f"/api/v1/candidate-bank/{cand_id}/contacts", headers=emp_headers)
    assert contacts_c.status_code == 403

    # State D: Another candidate tries to access /candidate-bank/{id}
    cand2_headers = _auth_headers(client, "cand2.privacy@fsp.ru", role="candidate")
    cand_access = client.get(f"/api/v1/candidate-bank/{cand_id}", headers=cand2_headers)
    assert cand_access.status_code == 403


def test_152fz_multi_tenant_isolation_employer_a_vs_b(client):
    """
    Adversarial Check 1.3:
    Candidate accepts invitation from Employer A.
    Employer A now has legitimate access to candidate contacts.
    Employer B MUST STILL BE FORBIDDEN:
    - GET /candidate-bank/{id}/contacts for Employer B returns 403 Forbidden
    - GET /candidate-bank/{id} for Employer B returns masked contacts (None)
    """
    cand_headers = _auth_headers(client, "cand.multitenant@fsp.ru", role="candidate")
    client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        headers=cand_headers,
        json={"specialization_id": 1, "claimed_grade_id": 2, "skills": ["python"]},
    )
    client.patch(
        "/api/v1/candidate-profile/me",
        headers=cand_headers,
        json={
            "phone": "+7 (999) 555-44-33",
            "telegram": "@multitenant_target",
            "github_url": "https://github.com/multitenant_target",
        },
    )
    cand_me = client.get("/api/v1/candidate-profile/me", headers=cand_headers).json()
    cand_id = cand_me["id"]

    emp_a_headers = _auth_headers(client, "emp_a@alpha.ru", role="employer")
    emp_b_headers = _auth_headers(client, "emp_b@beta.ru", role="employer")

    # Employer A sends invitation
    inv_a_res = client.post(
        "/api/v1/invitations",
        headers=emp_a_headers,
        json={
            "candidate_profile_id": cand_id,
            "proposal_text": "Alpha Corp wants you",
            "salary_min": 250000,
            "salary_max": 350000,
        },
    )
    assert inv_a_res.status_code == 201
    inv_a_id = inv_a_res.json()["id"]

    # Candidate accepts Employer A's invitation
    acc_res = client.post(f"/api/v1/invitations/{inv_a_id}/accept", headers=cand_headers)
    assert acc_res.status_code == 200

    # Employer A can now access contacts
    emp_a_contacts = client.get(f"/api/v1/candidate-bank/{cand_id}/contacts", headers=emp_a_headers)
    assert emp_a_contacts.status_code == 200
    a_data = emp_a_contacts.json()
    assert a_data["email"] == "cand.multitenant@fsp.ru"

    emp_a_det = client.get(f"/api/v1/candidate-bank/{cand_id}", headers=emp_a_headers).json()
    assert emp_a_det["is_contacts_masked"] is False
    assert emp_a_det["email"] == "cand.multitenant@fsp.ru"

    # ADVERSARIAL STRESS: Employer B attempts to access contacts
    emp_b_contacts = client.get(f"/api/v1/candidate-bank/{cand_id}/contacts", headers=emp_b_headers)
    assert emp_b_contacts.status_code == 403, (
        f"Multi-tenant violation: Employer B accessed contacts! Status: {emp_b_contacts.status_code}"
    )

    emp_b_det = client.get(f"/api/v1/candidate-bank/{cand_id}", headers=emp_b_headers).json()
    assert emp_b_det["is_contacts_masked"] is True, "Multi-tenant violation: is_contacts_masked is False for Employer B"
    assert emp_b_det["email"] is None
    assert emp_b_det["phone"] is None
    assert emp_b_det["telegram"] is None
    assert emp_b_det["github_url"] is None
    assert emp_b_det["raw_resume_pdf_url"] is None
    assert "(#C-" in emp_b_det["masked_full_name"]


def test_152fz_application_access_isolation(client):
    """
    Adversarial Check 1.4:
    Direct Application access path:
    Candidate applies to Employer A's vacancy.
    Employer A can view contacts; Employer B cannot view contacts.
    """
    cand_headers = _auth_headers(client, "cand.app_target@fsp.ru", role="candidate")
    client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        headers=cand_headers,
        json={"specialization_id": 1, "claimed_grade_id": 2, "skills": ["python"]},
    )
    client.patch(
        "/api/v1/candidate-profile/me",
        headers=cand_headers,
        json={"phone": "+7 (900) 123-45-67", "telegram": "@app_applicant"},
    )
    cand_me = client.get("/api/v1/candidate-profile/me", headers=cand_headers).json()
    cand_id = cand_me["id"]

    emp_a_headers = _auth_headers(client, "emp_a.vac@alpha.ru", role="employer")
    emp_b_headers = _auth_headers(client, "emp_b.vac@beta.ru", role="employer")

    # Employer A posts a vacancy
    vac_res = client.post(
        "/api/v1/vacancies",
        headers=emp_a_headers,
        json={
            "specialization_id": 1,
            "grade_id": 2,
            "title": "Backend Middle Developer",
            "description": "Разработка микросервисов",
            "required_skills": ["python", "fastapi"],
            "salary_min": 180000,
            "salary_max": 250000,
        },
    )
    assert vac_res.status_code == 201
    vac_id = vac_res.json()["id"]

    # Candidate applies to Employer A's vacancy
    apply_res = client.post(
        "/api/v1/applications",
        headers=cand_headers,
        json={"vacancy_id": vac_id, "cover_letter": "Очень хочу в команду"},
    )
    assert apply_res.status_code == 201

    # Employer A has contact access via application
    emp_a_contacts = client.get(f"/api/v1/candidate-bank/{cand_id}/contacts", headers=emp_a_headers)
    assert emp_a_contacts.status_code == 200

    # Employer B still has NO access
    emp_b_contacts = client.get(f"/api/v1/candidate-bank/{cand_id}/contacts", headers=emp_b_headers)
    assert emp_b_contacts.status_code == 403


# ==============================================================================
# SECTION 2: Salary Range Invariants (API & DB Constraints)
# ==============================================================================


def test_salary_spread_and_bounds_invariants(client):
    """
    Adversarial Check 2.1:
    POST /api/v1/employer-needs salary range invariants:
    - min <= 0 -> 422
    - max < min -> 422
    - max / min > 3.5 -> 422
    - boundary max / min == 3.5 -> 201
    """
    emp_headers = _auth_headers(client, "emp.sal_bounds_checker@fsp.ru", role="employer")

    test_cases = [
        (0, 100000, 422),          # salary_min <= 0
        (-50000, 100000, 422),      # salary_min < 0
        (200000, 150000, 422),      # salary_max < salary_min
        (100000, 360000, 422),      # spread = 3.6 > 3.5
        (100000, 400000, 422),      # spread = 4.0 > 3.5
        (100000, 350000, 201),      # spread = 3.5 EXACT boundary -> VALID
        (200000, 200000, 201),      # spread = 1.0 -> VALID
    ]

    for salary_min, salary_max, expected_status in test_cases:
        payload = {
            "specialization_id": 1,
            "target_grade_id": 2,
            "title": "Инженер платформы",
            "team_tasks_text": "Разработка высоконагруженных систем",
            "salary_min": salary_min,
            "salary_max": salary_max,
            "salary_currency": "RUB",
            "work_format": "remote",
        }
        res = client.post("/api/v1/employer-needs", headers=emp_headers, json=payload)
        assert res.status_code == expected_status, (
            f"Failed for (min={salary_min}, max={salary_max}): "
            f"expected {expected_status}, got {res.status_code} ({res.text})"
        )


def test_salary_currency_rub_invariant_probe(client):
    """
    Adversarial Check 2.2:
    Probe whether non-RUB currency (e.g. USD, EUR) is strictly rejected with 422
    as mandated by the invariant 'currency strictly RUB'.
    """
    emp_headers = _auth_headers(client, "emp.currency_probe@fsp.ru", role="employer")

    payload_usd = {
        "specialization_id": 1,
        "target_grade_id": 2,
        "title": "Инженер платформы",
        "team_tasks_text": "Разработка высоконагруженных систем",
        "salary_min": 100000,
        "salary_max": 200000,
        "salary_currency": "USD",
        "work_format": "remote",
    }
    res_usd = client.post("/api/v1/employer-needs", headers=emp_headers, json=payload_usd)
    assert res_usd.status_code == 422, f"Expected 422 for USD currency, got {res_usd.status_code}: {res_usd.text}"
    assert "ERR_INVALID_CURRENCY" in res_usd.text or "RUB" in res_usd.text or "руб" in res_usd.text


def test_multi_employer_registration_and_need_creation_no_collision(client):
    """
    Adversarial Check 2.2b:
    Verify that registering multiple employers without pre-seeded profiles
    and accessing /api/v1/employer-needs never crashes with 500 SQLite UNIQUE constraint collision.
    """
    reg1 = client.post(
        "/api/v1/auth/register",
        json={
            "email": "emp.fresh1@corp1.ru",
            "password": "StrongPassword123!",
            "role": "employer",
            "company_name": "ООО Спец 1",
            "inn": make_valid_inn(700101),
            "consent_pdn_processing": True,
            "consent_profile_publication": True,
        },
    )
    assert reg1.status_code == 201
    tok1 = reg1.json()["tokens"]["access_token"]
    h1 = {"Authorization": f"Bearer {tok1}"}

    reg2 = client.post(
        "/api/v1/auth/register",
        json={
            "email": "emp.fresh2@corp2.ru",
            "password": "StrongPassword123!",
            "role": "employer",
            "company_name": "ООО Спец 2",
            "inn": make_valid_inn(700102),
            "consent_pdn_processing": True,
            "consent_profile_publication": True,
        },
    )
    assert reg2.status_code == 201
    tok2 = reg2.json()["tokens"]["access_token"]
    h2 = {"Authorization": f"Bearer {tok2}"}

    list1 = client.get("/api/v1/employer-needs", headers=h1)
    assert list1.status_code == 200

    list2 = client.get("/api/v1/employer-needs", headers=h2)
    assert list2.status_code == 200

    c1 = client.post(
        "/api/v1/employer-needs",
        headers=h1,
        json={
            "specialization_id": 1,
            "target_grade_id": 2,
            "title": "Backend Need 1",
            "team_tasks_text": "Tasks 1",
            "salary_min": 100000,
            "salary_max": 200000,
            "salary_currency": "RUB",
        },
    )
    assert c1.status_code == 201

    c2 = client.post(
        "/api/v1/employer-needs",
        headers=h2,
        json={
            "specialization_id": 1,
            "target_grade_id": 2,
            "title": "Backend Need 2",
            "team_tasks_text": "Tasks 2",
            "salary_min": 150000,
            "salary_max": 250000,
            "salary_currency": "RUB",
        },
    )
    assert c2.status_code == 201


def test_salary_invariants_put_employer_needs(client):
    """
    Adversarial Check 2.3:
    PUT /api/v1/employer-needs/{id} salary update validation:
    - Changing salary_max such that spread > 3.5 -> 422 rejected
    - Changing salary_min <= 0 -> 422 rejected
    - Changing salary_max < salary_min -> 422 rejected
    """
    emp_headers = _auth_headers(client, "emp.sal_put@fsp.ru", role="employer")
    create_res = client.post(
        "/api/v1/employer-needs",
        headers=emp_headers,
        json={
            "specialization_id": 1,
            "target_grade_id": 2,
            "title": "Backend Need",
            "team_tasks_text": "Задачи бэкенда",
            "salary_min": 100000,
            "salary_max": 200000,
            "salary_currency": "RUB",
        },
    )
    assert create_res.status_code == 201
    need_id = create_res.json()["id"]

    # 1. Update with spread > 3.5
    bad_spread = client.put(
        f"/api/v1/employer-needs/{need_id}",
        headers=emp_headers,
        json={"salary_max": 400000},  # 400000 / 100000 = 4.0 > 3.5
    )
    assert bad_spread.status_code == 422

    # 2. Update with salary_min <= 0
    bad_min = client.put(
        f"/api/v1/employer-needs/{need_id}",
        headers=emp_headers,
        json={"salary_min": 0},
    )
    assert bad_min.status_code == 422

    # 3. Update with salary_max < salary_min
    bad_order = client.put(
        f"/api/v1/employer-needs/{need_id}",
        headers=emp_headers,
        json={"salary_min": 250000, "salary_max": 200000},
    )
    assert bad_order.status_code == 422

    # 4. Valid update
    valid_up = client.put(
        f"/api/v1/employer-needs/{need_id}",
        headers=emp_headers,
        json={"salary_min": 120000, "salary_max": 300000},
    )
    assert valid_up.status_code == 200
    assert valid_up.json()["salary_min"] == 120000
    assert valid_up.json()["salary_max"] == 300000


def test_salary_invariants_post_invitations(client):
    """
    Adversarial Check 2.4:
    POST /api/v1/invitations must strictly enforce salary range invariants.
    """
    cand_headers = _auth_headers(client, "cand.sal_inv@fsp.ru", role="candidate")
    client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        headers=cand_headers,
        json={"specialization_id": 1, "claimed_grade_id": 2, "skills": ["python"]},
    )
    cand_me = client.get("/api/v1/candidate-profile/me", headers=cand_headers).json()
    cand_id = cand_me["id"]

    emp_headers = _auth_headers(client, "emp.sal_inv_tester@fsp.ru", role="employer")

    test_cases = [
        (0, 200000, 422),
        (-10000, 200000, 422),
        (250000, 200000, 422),
        (100000, 380000, 422),  # spread 3.8 > 3.5
        (100000, 350000, 201),  # spread 3.5 valid
    ]

    for salary_min, salary_max, expected_status in test_cases:
        res = client.post(
            "/api/v1/invitations",
            headers=emp_headers,
            json={
                "candidate_profile_id": cand_id,
                "proposal_text": "Приглашение на проект",
                "salary_min": salary_min,
                "salary_max": salary_max,
            },
        )
        assert res.status_code == expected_status, (
            f"Invitation failed for (min={salary_min}, max={salary_max}): "
            f"expected {expected_status}, got {res.status_code} ({res.text})"
        )


def test_salary_invariants_post_vacancies(client):
    """
    Adversarial Check 2.5:
    POST /api/v1/vacancies must strictly enforce salary range invariants.
    """
    emp_headers = _auth_headers(client, "emp.sal_vac_tester@fsp.ru", role="employer")

    test_cases = [
        (0, 200000, 422),
        (-10000, 200000, 422),
        (250000, 200000, 422),
        (100000, 380000, 422),  # spread 3.8 > 3.5
        (100000, 350000, 201),  # spread 3.5 valid
    ]

    for salary_min, salary_max, expected_status in test_cases:
        res = client.post(
            "/api/v1/vacancies",
            headers=emp_headers,
            json={
                "specialization_id": 1,
                "grade_id": 2,
                "title": "Инженер разработки",
                "description": "Описание вакансии для инженера бэкенда",
                "required_skills": ["python"],
                "salary_min": salary_min,
                "salary_max": salary_max,
            },
        )
        assert res.status_code == expected_status, (
            f"Vacancy failed for (min={salary_min}, max={salary_max}): "
            f"expected {expected_status}, got {res.status_code} ({res.text})"
        )


def test_salary_database_check_constraints_rejection(client):
    """
    Adversarial Check 2.6:
    Direct SQL/DB layer verification:
    Attempting to directly bypass API layer and insert rows with salary_min <= 0
    or salary_max < salary_min into employer_needs, invitations, or vacancies
    must trigger an SQLite IntegrityError / CheckConstraint violation.
    """
    from sqlalchemy.exc import IntegrityError

    async def _test():
        async with test_session_factory() as session:
            res = await session.execute(
                text(
                    "INSERT INTO users (email, hashed_password, role, is_active) "
                    "VALUES ('db_constraint@fsp.ru', 'hash', 'employer', 1) RETURNING id"
                )
            )
            user_id = res.scalar_one()

            res_emp = await session.execute(
                text(
                    "INSERT INTO employer_profiles (user_id, company_name, inn, domain, is_inn_verified, trust_score) "
                    "VALUES (:uid, 'ООО Тест', :inn, 'test.ru', 1, 90) RETURNING id"
                ),
                {"uid": user_id, "inn": make_valid_inn(999999)},
            )
            emp_profile_id = res_emp.scalar_one()
            await session.commit()

            # 1. EmployerNeed: salary_min <= 0
            with pytest.raises(IntegrityError):
                await session.execute(
                    text(
                        "INSERT INTO employer_needs (employer_profile_id, specialization_id, target_grade_id, "
                        "salary_min, salary_max, team_tasks_text, work_format, is_active) "
                        "VALUES (:emp_id, 1, 2, -100, 200000, 'Tasks', 'remote', 1)"
                    ),
                    {"emp_id": emp_profile_id},
                )
                await session.commit()
            await session.rollback()

            # 2. EmployerNeed: salary_max < salary_min
            with pytest.raises(IntegrityError):
                await session.execute(
                    text(
                        "INSERT INTO employer_needs (employer_profile_id, specialization_id, target_grade_id, "
                        "salary_min, salary_max, team_tasks_text, work_format, is_active) "
                        "VALUES (:emp_id, 1, 2, 300000, 200000, 'Tasks', 'remote', 1)"
                    ),
                    {"emp_id": emp_profile_id},
                )
                await session.commit()
            await session.rollback()

            # 3. Vacancy: salary_min <= 0
            with pytest.raises(IntegrityError):
                await session.execute(
                    text(
                        "INSERT INTO vacancies (employer_profile_id, specialization_id, grade_id, title, "
                        "description, salary_min, salary_max, work_format, status) "
                        "VALUES (:emp_id, 1, 2, 'Title', 'Desc', 0, 200000, 'remote', 'published')"
                    ),
                    {"emp_id": emp_profile_id},
                )
                await session.commit()
            await session.rollback()

            # 4. Vacancy: salary_max < salary_min
            with pytest.raises(IntegrityError):
                await session.execute(
                    text(
                        "INSERT INTO vacancies (employer_profile_id, specialization_id, grade_id, title, "
                        "description, salary_min, salary_max, work_format, status) "
                        "VALUES (:emp_id, 1, 2, 'Title', 'Desc', 250000, 150000, 'remote', 'published')"
                    ),
                    {"emp_id": emp_profile_id},
                )
                await session.commit()
            await session.rollback()

    asyncio.run(_test())


# ==============================================================================
# SECTION 3: Live matched_candidates_count
# ==============================================================================


def test_matched_candidates_count_accuracy_and_reactivity(client):
    """
    Adversarial Check 3.1:
    Verify that matched_candidates_count:
    1. Accurately counts ONLY published candidates matching specialization and grade.
    2. Does NOT count unpublished candidates.
    3. Does NOT count candidates of different specialization or grade.
    4. Dynamically increases when a new candidate publishes their profile.
    5. Dynamically reflects across both GET /employer-needs and GET /employer-needs/{id}.
    """
    emp_headers = _auth_headers(client, "emp.matcher@fsp.ru", role="employer")

    # Create need for specialization_id=1 (backend), target_grade_id=2 (middle)
    need_res = client.post(
        "/api/v1/employer-needs",
        headers=emp_headers,
        json={
            "specialization_id": 1,
            "target_grade_id": 2,
            "title": "Backend Middle Needs",
            "team_tasks_text": "Командная разработка",
            "salary_min": 150000,
            "salary_max": 250000,
            "salary_currency": "RUB",
        },
    )
    assert need_res.status_code == 201
    need_id = need_res.json()["id"]
    initial_count = need_res.json()["matched_candidates_count"]

    # 1. Add candidate 1 matching (spec=1, grade=2, is_published=True)
    cand1_headers = _auth_headers(client, "cand.match1@fsp.ru", role="candidate")
    surv1 = client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        headers=cand1_headers,
        json={"specialization_id": 1, "claimed_grade_id": 2, "skills": ["python"]},
    )
    assert surv1.status_code == 201

    # Verify count incremented by 1
    detail_res1 = client.get(f"/api/v1/employer-needs/{need_id}", headers=emp_headers).json()
    assert detail_res1["matched_candidates_count"] == initial_count + 1, (
        f"Expected {initial_count + 1}, got {detail_res1['matched_candidates_count']}"
    )

    # 2. Add candidate 2 with DIFFERENT grade (spec=1, grade=3 - Senior)
    cand2_headers = _auth_headers(client, "cand.match2_senior@fsp.ru", role="candidate")
    client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        headers=cand2_headers,
        json={"specialization_id": 1, "claimed_grade_id": 3, "skills": ["python", "docker"]},
    )
    # Count for Middle should NOT change
    detail_res2 = client.get(f"/api/v1/employer-needs/{need_id}", headers=emp_headers).json()
    assert detail_res2["matched_candidates_count"] == initial_count + 1

    # 3. Add candidate 3 with DIFFERENT specialization (spec=2 - frontend, grade=2)
    cand3_headers = _auth_headers(client, "cand.match3_frontend@fsp.ru", role="candidate")
    client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        headers=cand3_headers,
        json={"specialization_id": 2, "claimed_grade_id": 2, "skills": ["typescript", "react"]},
    )
    # Count for Backend Middle should NOT change
    detail_res3 = client.get(f"/api/v1/employer-needs/{need_id}", headers=emp_headers).json()
    assert detail_res3["matched_candidates_count"] == initial_count + 1

    # 4. Add candidate 4 matching spec=1, grade=2, but unpublish via /unpublish
    cand4_headers = _auth_headers(client, "cand.match4_unpub@fsp.ru", role="candidate")
    client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        headers=cand4_headers,
        json={"specialization_id": 1, "claimed_grade_id": 2, "skills": ["python"]},
    )
    # Count should be initial_count + 2
    detail_res4 = client.get(f"/api/v1/employer-needs/{need_id}", headers=emp_headers).json()
    assert detail_res4["matched_candidates_count"] == initial_count + 2

    # Now unpublish cand4 via explicit unpublish endpoint
    unpub_res = client.post("/api/v1/candidate-profile/unpublish", headers=cand4_headers)
    assert unpub_res.status_code == 200
    assert unpub_res.json()["is_published"] is False

    # Count should decrement back to initial_count + 1
    detail_res5 = client.get(f"/api/v1/employer-needs/{need_id}", headers=emp_headers).json()
    assert detail_res5["matched_candidates_count"] == initial_count + 1, (
        f"Unpublished candidate was counted! Expected {initial_count + 1}, got {detail_res5['matched_candidates_count']}"
    )

    # Re-publish cand4 via explicit publish endpoint
    pub_res = client.post("/api/v1/candidate-profile/publish", headers=cand4_headers)
    assert pub_res.status_code == 200
    assert pub_res.json()["is_published"] is True

    detail_res6 = client.get(f"/api/v1/employer-needs/{need_id}", headers=emp_headers).json()
    assert detail_res6["matched_candidates_count"] == initial_count + 2

    # Verify list endpoint also returns the exact same matched_candidates_count
    list_res = client.get("/api/v1/employer-needs", headers=emp_headers).json()
    target_need_in_list = next((n for n in list_res["items"] if n["id"] == need_id), None)
    assert target_need_in_list is not None
    assert target_need_in_list["matched_candidates_count"] == initial_count + 2
