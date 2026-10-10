"""
Empirical Adversarial Security & Psychometrics Test Suite (Challenger 1):
1. IDOR Stress Test: 2 Candidate accounts (A and B). Cand A creates a session.
   Cand B attempts access to all 6 session endpoints:
   - GET /sessions/{id} -> 403 Forbidden ("Нет доступа к чужой тест-сессии")
   - GET /sessions/{id}/progress -> 403 Forbidden ("Нет доступа к чужой тест-сессии")
   - GET /sessions/{id}/tasks/0 -> 403 Forbidden ("Нет доступа к чужой тест-сессии")
   - POST /sessions/{id}/submit-task -> 403 Forbidden ("Нет доступа к чужой тест-сессии")
   - POST /sessions/{id}/finish -> 403 Forbidden ("Нет доступа к чужой тест-сессии")
   - GET /sessions/{id}/results -> 403 Forbidden ("Нет доступа к чужой тест-сессии")
2. RBAC Stress Test:
   - Employer attempting POST /api/v1/candidate-profile/onboarding-survey -> 403
   - Candidate attempting POST /api/v1/micro-challenges -> 403
   - Employer B editing Employer A's challenge -> 403
   - Employer B deleting Employer A's challenge -> 403
3. Session Timeout Test:
   - Expired session timestamp -> POST /sessions/{id}/submit-task returns 410 Gone ("Время тестирования истекло")
4. Categorization Persistence Test:
   - Complete assessment session -> CandidateCategorization record created with is_current=True, confirmed_grade_id, test_score
   - Subsequent session retires old record (is_current=False) and marks new as is_current=True
5. IRT 3PL Parameter Loading Test:
   - Verifies Birnbaum 3PL scoring dynamically loads item parameters (param_a, param_b, param_c)
     from CanonicalItemFamily rather than using hardcoded constants (1.5, 0.5, 0.2).
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select, text, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import get_db
from app.main import app
from app.models.assessment_answers import AssessmentAnswer
from app.models.assessment_sessions import AssessmentSession
from app.models.base import Base
from app.models.candidate_categorizations import CandidateCategorization
from app.models.candidate_profiles import CandidateProfile
from app.models.canonical_item_families import CanonicalItemFamily
from app.models.categories import Category
from app.models.employer_profiles import EmployerProfile
from app.models.grades import Grade
from app.models.micro_challenges import MicroChallenge
from app.models.specializations import Specialization
from app.models.users import User
from app.services.kite_irt import BayesianEAPEstimator, IRT3PLItem
from scripts.seed_canonical_items import seed_canonical_items
from scripts.seed_reference_data import seed_reference_data

TEST_DB_URL = "sqlite+aiosqlite:///./test_adversarial_sec_irt.db"
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
                await seed_canonical_items(session)
            _db_initialized = True
        else:
            async with test_session_factory() as session:
                for tbl in [
                    "candidate_categorizations",
                    "challenge_submissions",
                    "micro_challenges",
                    "cooldown_resets",
                    "assessment_answers",
                    "assessment_sessions",
                    "candidate_skills",
                    "candidate_profiles",
                    "employer_profiles",
                    "user_consents",
                    "users",
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


VALID_INNS = ["7707083893", "7736207543", "7710140679", "7842349892", "7702070139", "7701234567"]
_inn_counter = 0


def _register_and_auth(client: TestClient, email: str, role: str = "candidate") -> dict:
    """Registers a user and returns authorization headers."""
    global _inn_counter
    payload = {
        "email": email,
        "password": "StrongPassword123!",
        "role": role,
        "first_name": "Тест",
        "last_name": "Пользователь",
        "consent_pdn_processing": True,
        "consent_profile_publication": True,
    }
    if role == "employer":
        inn = VALID_INNS[_inn_counter % len(VALID_INNS)]
        payload["inn"] = inn
        payload["company_name"] = f"ООО Компания {_inn_counter}"
        _inn_counter += 1

    resp = client.post("/api/v1/auth/register", json=payload)
    if resp.status_code == 201:
        token = resp.json()["tokens"]["access_token"]
    elif resp.status_code == 409:
        l_resp = client.post("/api/v1/auth/login", json={"email": email, "password": "StrongPassword123!"})
        assert l_resp.status_code == 200, f"Login failed: {l_resp.text}"
        token = l_resp.json()["access_token"]
    else:
        assert False, f"Register failed: {resp.status_code} {resp.text}"

    return {"Authorization": f"Bearer {token}"}


# ==============================================================================
# TEST 1: IDOR STRESS TEST ON ALL 6 ASSESSMENT ENDPOINTS
# ==============================================================================
def test_idor_stress_all_6_assessment_endpoints(client: TestClient):
    """
    Empirical IDOR Stress Test:
    Candidate A starts a session.
    Candidate B (an attacker) attempts unauthorized access to all 6 endpoints:
    1. GET /sessions/{id}
    2. GET /sessions/{id}/progress
    3. GET /sessions/{id}/tasks/0
    4. POST /sessions/{id}/submit-task
    5. POST /sessions/{id}/finish
    6. GET /sessions/{id}/results

    VERIFICATION:
    - All 6 endpoints MUST return HTTP 403 Forbidden.
    - Error detail MUST be exactly 'Нет доступа к чужой тест-сессии'.
    - Candidate A (the legitimate owner) CAN access their own session.
    """
    headers_a = _register_and_auth(client, "cand_a@fsp.ru", role="candidate")
    headers_b = _register_and_auth(client, "cand_b@fsp.ru", role="candidate")

    # Complete onboarding for both candidates
    for h in [headers_a, headers_b]:
        survey_res = client.post(
            "/api/v1/candidate-profile/onboarding-survey",
            json={
                "specialization_id": 1,
                "claimed_grade_id": 2,
                "work_format": "remote",
                "salary_min": 150000,
                "salary_max": 220000,
                "consent_personal_data": True,
                "consent_profile_publish": True,
                "skills": ["Python", "FastAPI"],
            },
            headers=h,
        )
        assert survey_res.status_code == 201, f"Onboarding failed: {survey_res.text}"

    # Candidate A creates an assessment session
    start_res = client.post(
        "/api/v1/assessment/sessions/start",
        json={"specialization_id": 1, "claimed_grade_id": 2, "session_type": "initial"},
        headers=headers_a,
    )
    assert start_res.status_code == 201, f"Session start failed: {start_res.text}"
    session_id = start_res.json()["session_id"]
    assert session_id > 0

    expected_detail = "Нет доступа к чужой тест-сессии"

    def _check_forbidden(resp, endpoint_name):
        assert resp.status_code == 403, f"{endpoint_name} IDOR failed: {resp.status_code} {resp.text}"
        detail = resp.json().get("detail") or resp.json().get("message")
        assert detail == expected_detail, f"{endpoint_name} unexpected detail: {detail}"

    # 1. GET /sessions/{id}
    r1 = client.get(f"/api/v1/assessment/sessions/{session_id}", headers=headers_b)
    _check_forbidden(r1, "Endpoint 1 (GET /sessions/{id})")

    # 2. GET /sessions/{id}/progress
    r2 = client.get(f"/api/v1/assessment/sessions/{session_id}/progress", headers=headers_b)
    _check_forbidden(r2, "Endpoint 2 (GET /sessions/{id}/progress)")

    # 3. GET /sessions/{id}/tasks/0
    r3 = client.get(f"/api/v1/assessment/sessions/{session_id}/tasks/0", headers=headers_b)
    _check_forbidden(r3, "Endpoint 3 (GET /sessions/{id}/tasks/0)")

    # 4. POST /sessions/{id}/submit-task
    submit_payload = {
        "task_index": 0,
        "answer_payload": {"selected_option": "A", "code": "def solution(): return 42"},
        "time_spent_seconds": 25,
    }
    r4 = client.post(f"/api/v1/assessment/sessions/{session_id}/submit-task", json=submit_payload, headers=headers_b)
    _check_forbidden(r4, "Endpoint 4 (POST /sessions/{id}/submit-task)")

    # 5. POST /sessions/{id}/finish
    r5 = client.post(f"/api/v1/assessment/sessions/{session_id}/finish", headers=headers_b)
    _check_forbidden(r5, "Endpoint 5 (POST /sessions/{id}/finish)")

    # 6. GET /sessions/{id}/results
    r6 = client.get(f"/api/v1/assessment/sessions/{session_id}/results", headers=headers_b)
    _check_forbidden(r6, "Endpoint 6 (GET /sessions/{id}/results)")

    # Legitimate Owner Verification: Candidate A has full access
    owner_get = client.get(f"/api/v1/assessment/sessions/{session_id}", headers=headers_a)
    assert owner_get.status_code == 200, f"Owner session get failed: {owner_get.text}"
    assert owner_get.json()["session_id"] == session_id

    owner_prog = client.get(f"/api/v1/assessment/sessions/{session_id}/progress", headers=headers_a)
    assert owner_prog.status_code == 200, f"Owner progress failed: {owner_prog.text}"

    owner_task = client.get(f"/api/v1/assessment/sessions/{session_id}/tasks/0", headers=headers_a)
    assert owner_task.status_code == 200, f"Owner task fetch failed: {owner_task.text}"


# ==============================================================================
# TEST 2: RBAC STRESS TEST
# ==============================================================================
def test_rbac_stress_candidate_and_employer_boundaries(client: TestClient):
    """
    Empirical RBAC Stress Test:
    1. Non-candidate role (employer) attempting POST /candidate-profile/onboarding-survey -> 403
    2. Candidate role attempting POST /micro-challenges -> 403
    3. Employer B attempting PUT /micro-challenges/{id} on Employer A's challenge -> 403
    4. Employer B attempting DELETE /micro-challenges/{id} on Employer A's challenge -> 403
    """
    cand_headers = _register_and_auth(client, "cand_rbac@fsp.ru", role="candidate")
    emp_a_headers = _register_and_auth(client, "emp_a@techcorp.ru", role="employer")
    emp_b_headers = _register_and_auth(client, "emp_b@othercorp.ru", role="employer")

    # 1. Employer attempting onboarding-survey -> 403 Forbidden
    survey_payload = {
        "specialization_id": 1,
        "claimed_grade_id": 2,
        "work_format": "remote",
        "salary_min": 100000,
        "salary_max": 200000,
        "consent_personal_data": True,
        "consent_profile_publish": True,
        "skills": ["SQL"],
    }
    r_survey = client.post("/api/v1/candidate-profile/onboarding-survey", json=survey_payload, headers=emp_a_headers)
    assert r_survey.status_code == 403, f"Employer survey should fail with 403: {r_survey.status_code} {r_survey.text}"
    survey_detail = r_survey.json().get("detail") or r_survey.json().get("message")
    assert "Только соискатели могут заполнять анкету онбординга" in survey_detail

    # 2. Candidate attempting to create micro-challenge -> 403 Forbidden
    challenge_payload = {
        "title": "Adversarial Challenge Creation by Candidate",
        "description_markdown": "Test challenge description",
        "specialization_id": 1,
        "grade_id": 2,
        "starter_code": "def solve(): pass",
        "test_cases": [{"input": "1", "expected": "1", "is_public": True}],
        "points": 40,
    }
    r_cand_chal = client.post("/api/v1/micro-challenges/", json=challenge_payload, headers=cand_headers)
    assert r_cand_chal.status_code == 403, f"Candidate challenge creation should fail with 403: {r_cand_chal.text}"
    chal_detail = r_cand_chal.json().get("detail") or r_cand_chal.json().get("message")
    assert "работодатели и администраторы" in chal_detail

    # 3. Employer A creates a legitimate challenge
    r_emp_create = client.post("/api/v1/micro-challenges/", json=challenge_payload, headers=emp_a_headers)
    assert r_emp_create.status_code == 201, f"Employer A creation failed: {r_emp_create.text}"
    chal_id = r_emp_create.json()["id"]

    # 4. Employer B attempts to edit Employer A's challenge -> 403 Forbidden
    edit_payload = {"title": "Tampered Title by Employer B"}
    r_emp_b_edit = client.put(f"/api/v1/micro-challenges/{chal_id}", json=edit_payload, headers=emp_b_headers)
    assert r_emp_b_edit.status_code == 403, f"Employer B edit should fail with 403: {r_emp_b_edit.text}"
    edit_detail = r_emp_b_edit.json().get("detail") or r_emp_b_edit.json().get("message")
    assert "создавший его работодатель или администратор" in edit_detail

    # 5. Employer B attempts to delete Employer A's challenge -> 403 Forbidden
    r_emp_b_del = client.delete(f"/api/v1/micro-challenges/{chal_id}", headers=emp_b_headers)
    assert r_emp_b_del.status_code == 403, f"Employer B delete should fail with 403: {r_emp_b_del.text}"
    del_detail = r_emp_b_del.json().get("detail") or r_emp_b_del.json().get("message")
    assert "создавший его работодатель или администратор" in del_detail

    # Legitimate Author Verification: Employer A can edit and delete
    r_emp_a_edit = client.put(f"/api/v1/micro-challenges/{chal_id}", json=edit_payload, headers=emp_a_headers)
    assert r_emp_a_edit.status_code == 200, f"Employer A edit failed: {r_emp_a_edit.text}"
    assert r_emp_a_edit.json()["title"] == "Tampered Title by Employer B"

    r_emp_a_del = client.delete(f"/api/v1/micro-challenges/{chal_id}", headers=emp_a_headers)
    assert r_emp_a_del.status_code == 200, f"Employer A delete failed: {r_emp_a_del.text}"


# ==============================================================================
# TEST 3: SESSION TIMEOUT TEST
# ==============================================================================
def test_session_timeout_expiration_returns_410_gone(client: TestClient):
    """
    Empirical Timeout Test:
    Candidate creates session.
    Database timestamp expires_at is set to the past.
    Candidate attempts to submit an answer via POST /submit-task.
    VERIFICATION:
    - Must return HTTP 410 Gone.
    - Error detail must be 'Время тестирования истекло'.
    """
    headers = _register_and_auth(client, "timeout_cand@fsp.ru", role="candidate")

    client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        json={
            "specialization_id": 1,
            "claimed_grade_id": 2,
            "work_format": "remote",
            "salary_min": 160000,
            "salary_max": 230000,
            "consent_personal_data": True,
            "consent_profile_publish": True,
            "skills": ["Go", "Docker"],
        },
        headers=headers,
    )

    start_res = client.post(
        "/api/v1/assessment/sessions/start",
        json={"specialization_id": 1, "claimed_grade_id": 2, "session_type": "initial"},
        headers=headers,
    )
    assert start_res.status_code == 201
    sess_id = start_res.json()["session_id"]

    # Manually expire the session in DB
    async def _expire_session():
        async with test_session_factory() as db:
            past_time = datetime.now(timezone.utc) - timedelta(minutes=15)
            await db.execute(
                update(AssessmentSession)
                .where(AssessmentSession.id == sess_id)
                .values(expires_at=past_time)
            )
            await db.commit()

    asyncio.run(_expire_session())

    # Candidate attempts to submit answer to expired session
    sub_res = client.post(
        f"/api/v1/assessment/sessions/{sess_id}/submit-task",
        json={
            "task_index": 0,
            "answer_payload": {"selected_option": "A", "code": "def solution(): return 42"},
            "time_spent_seconds": 25,
        },
        headers=headers,
    )
    assert sub_res.status_code == 410, f"Expected 410 Gone for expired session, got {sub_res.status_code}: {sub_res.text}"
    detail = sub_res.json().get("detail") or sub_res.json().get("message")
    assert "Время тестирования истекло" in detail


# ==============================================================================
# TEST 4: CANDIDATE CATEGORIZATION PERSISTENCE TEST
# ==============================================================================
def test_candidate_categorization_persisted_on_finish(client: TestClient):
    """
    Empirical Categorization Test:
    Candidate completes an assessment session via POST /sessions/{id}/finish.
    VERIFICATION:
    - CandidateCategorization table has a record with:
      - is_current = True
      - confirmed_grade_id is set
      - test_score matches session.theta_score
      - source_session_id == session.id
    - On a subsequent completed session:
      - Previous record becomes is_current = False
      - New record becomes is_current = True
    """
    headers = _register_and_auth(client, "cat_cand@fsp.ru", role="candidate")

    # Onboarding
    survey_res = client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        json={
            "specialization_id": 1,
            "claimed_grade_id": 2,
            "work_format": "remote",
            "salary_min": 170000,
            "salary_max": 250000,
            "consent_personal_data": True,
            "consent_profile_publish": True,
            "skills": ["Python", "AsyncIO"],
        },
        headers=headers,
    )
    assert survey_res.status_code == 201

    # Start first session
    start_1 = client.post(
        "/api/v1/assessment/sessions/start",
        json={"specialization_id": 1, "claimed_grade_id": 2, "session_type": "initial"},
        headers=headers,
    )
    assert start_1.status_code == 201
    sess_1_id = start_1.json()["session_id"]

    # Submit answers
    for i in range(12):
        client.post(
            f"/api/v1/assessment/sessions/{sess_1_id}/submit-task",
            json={
                "task_index": i,
                "answer_payload": {"selected_option": "A", "code": "def solve(): return 1"},
                "time_spent_seconds": 20,
            },
            headers=headers,
        )

    # Finish session 1
    fin_1 = client.post(f"/api/v1/assessment/sessions/{sess_1_id}/finish", headers=headers)
    assert fin_1.status_code == 200, f"Finish 1 failed: {fin_1.text}"
    fin_1_data = fin_1.json()
    assert fin_1_data["status"] == "completed"
    score_1 = fin_1_data["theta_score"]

    # Verify CandidateCategorization table in DB
    async def _check_first_categorization():
        async with test_session_factory() as db:
            sess_obj = await db.scalar(select(AssessmentSession).where(AssessmentSession.id == sess_1_id))
            assert sess_obj is not None

            cats = (await db.execute(
                select(CandidateCategorization)
                .where(CandidateCategorization.candidate_profile_id == sess_obj.candidate_profile_id)
            )).scalars().all()

            assert len(cats) == 1, f"Expected 1 categorization record, found {len(cats)}"
            cat_rec = cats[0]
            assert cat_rec.is_current is True
            assert cat_rec.source_session_id == sess_1_id
            assert cat_rec.confirmed_grade_id is not None
            assert abs(cat_rec.test_score - score_1) < 1e-4

    asyncio.run(_check_first_categorization())

    # Expire 90-day cooldown on session 1 in DB so second session can start without 409
    async def _expire_first_session_cooldown():
        async with test_session_factory() as db:
            past_time = datetime.now(timezone.utc) - timedelta(days=95)
            await db.execute(
                update(AssessmentSession)
                .where(AssessmentSession.id == sess_1_id)
                .values(completed_at=past_time)
            )
            await db.commit()

    asyncio.run(_expire_first_session_cooldown())

    # Start second session
    start_2 = client.post(
        "/api/v1/assessment/sessions/start",
        json={"specialization_id": 1, "claimed_grade_id": 2, "session_type": "initial"},
        headers=headers,
    )
    assert start_2.status_code == 201, f"Start 2 failed: {start_2.text}"
    sess_2_id = start_2.json()["session_id"]
    assert sess_2_id != sess_1_id

    # Finish second session
    fin_2 = client.post(f"/api/v1/assessment/sessions/{sess_2_id}/finish", headers=headers)
    assert fin_2.status_code == 200, f"Finish 2 failed: {fin_2.text}"

    # Verify DB: old record has is_current=False, new record has is_current=True
    async def _check_second_categorization():
        async with test_session_factory() as db:
            sess_2_obj = await db.scalar(select(AssessmentSession).where(AssessmentSession.id == sess_2_id))
            cats = (await db.execute(
                select(CandidateCategorization)
                .where(CandidateCategorization.candidate_profile_id == sess_2_obj.candidate_profile_id)
                .order_by(CandidateCategorization.id.asc())
            )).scalars().all()

            assert len(cats) == 2, f"Expected 2 categorization records, found {len(cats)}"
            old_cat, new_cat = cats[0], cats[1]

            assert old_cat.source_session_id == sess_1_id
            assert old_cat.is_current is False, "Old categorization must have is_current=False"

            assert new_cat.source_session_id == sess_2_id
            assert new_cat.is_current is True, "New categorization must have is_current=True"

    asyncio.run(_check_second_categorization())


# ==============================================================================
# TEST 5: IRT 3PL PARAMETERS FROM DATABASE TEST
# ==============================================================================
def test_irt_3pl_loads_calibrated_item_parameters_from_db(client: TestClient):
    """
    Empirical IRT 3PL Parameter Loading Test:
    Verifies that finish_assessment_session loads item params (param_a, param_b, param_c)
    from CanonicalItemFamily in the database, and does NOT hardcode 1.5, 0.5, 0.2.
    """
    headers = _register_and_auth(client, "irt_cand@fsp.ru", role="candidate")

    client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        json={
            "specialization_id": 1,
            "claimed_grade_id": 2,
            "work_format": "remote",
            "salary_min": 180000,
            "salary_max": 260000,
            "consent_personal_data": True,
            "consent_profile_publish": True,
            "skills": ["Psychometrics", "IRT"],
        },
        headers=headers,
    )

    # Distinct test parameters injected into CanonicalItemFamily for Backend Middle
    DISTINCT_A = 2.75
    DISTINCT_B = -1.35
    DISTINCT_C = 0.12

    async def _update_item_parameters():
        async with test_session_factory() as db:
            await db.execute(
                update(CanonicalItemFamily)
                .where(
                    CanonicalItemFamily.specialization_id == 1,
                    CanonicalItemFamily.grade_id == 2,
                )
                .values(
                    param_a=DISTINCT_A,
                    param_b=DISTINCT_B,
                    param_c=DISTINCT_C,
                )
            )
            await db.commit()

    asyncio.run(_update_item_parameters())

    start_res = client.post(
        "/api/v1/assessment/sessions/start",
        json={"specialization_id": 1, "claimed_grade_id": 2, "session_type": "initial"},
        headers=headers,
    )
    assert start_res.status_code == 201
    sess_id = start_res.json()["session_id"]

    # Finish session
    fin_res = client.post(f"/api/v1/assessment/sessions/{sess_id}/finish", headers=headers)
    assert fin_res.status_code == 200
    actual_theta = fin_res.json()["theta_score"]

    # Calculate theoretical theta with the DISTINCT parameters vs with OLD constants (1.5, 0.5, 0.2)
    custom_items = [IRT3PLItem(item_id=i+1, a=DISTINCT_A, b=DISTINCT_B, c=DISTINCT_C) for i in range(12)]
    old_const_items = [IRT3PLItem(item_id=i+1, a=1.5, b=0.5, c=0.2) for i in range(12)]

    estimator = BayesianEAPEstimator(num_nodes=61, theta_min=-4.0, theta_max=4.0, prior_sd=1.0)
    theta_star_custom, _ = estimator.estimate_theta_star(custom_items, [0]*12)
    score_custom = BayesianEAPEstimator.scale_theta_linear_8(theta_star_custom)

    theta_star_old, _ = estimator.estimate_theta_star(old_const_items, [0]*12)
    score_old = BayesianEAPEstimator.scale_theta_linear_8(theta_star_old)

    # Empirically confirm that score computed with custom items matches actual_theta
    # and diverges significantly from score computed with old constants (1.5, 0.5, 0.2)
    assert abs(actual_theta - score_custom) < 0.1, (
        f"actual_theta ({actual_theta}) did not match score_custom ({score_custom})"
    )
    assert abs(actual_theta - score_old) > 10.0, (
        f"actual_theta ({actual_theta}) matched old constants ({score_old}), meaning constants are still used!"
    )
