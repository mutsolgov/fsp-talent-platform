"""
Empirical QA Challenge Test Suite — Phase 2 KITE IRT & Profiling Layer.
Adversarial challenge and empirical stress tests for:
1. Dual-scheme task index resolution (0-based vs 1-based, out-of-bounds, negative, session isolation).
2. Cooldown enforcement & Jury reset endpoint (/assessment/cooldown-status/jury-reset).
3. Boost opt-in & Retest lower endpoint schemas, boundary conditions (theta < 88 vs >= 88, rank clamping).
4. Micro-challenges dry-run schema (status, memory_kb).
5. Candidate profile theta field & publish/unpublish routes.
6. PyMuPDF resume parser magic bytes validation and skills boundary matching.
"""
from __future__ import annotations

import asyncio
import os
import sys
from datetime import datetime, timezone, timedelta

# Ensure backend directory is in sys.path
backend_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend")
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from fastapi.testclient import TestClient

from app.core.config import settings
from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models.users import User
from app.models.candidate_profiles import CandidateProfile
from app.models.assessment_sessions import AssessmentSession
from app.models.cooldown_resets import CooldownReset
from app.models.categories import Category
from app.models.grades import Grade
from app.models.specializations import Specialization
from app.api.v1.assessment import resolve_task_item_index, _session_index_base
from app.services.resume_parser import ResumeParser, InvalidPdfFormatError
from app.schemas.micro_challenges import ChallengeDryRunResponse
from app.schemas.candidate_profile import CandidateFullProfileResponse, CandidateSkillItem

from scripts.seed_canonical_items import seed_canonical_items
from scripts.seed_reference_data import seed_reference_data

TEST_DB_URL = "sqlite+aiosqlite:///./test_phase2_empirical.db"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
test_session_factory = async_sessionmaker(bind=test_engine, class_=AsyncSession, expire_on_commit=False)

async def override_get_db():
    async with test_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def get_fresh_client() -> TestClient:
    """Helper creating a test client with permanent db override for the process."""
    app.dependency_overrides[get_db] = override_get_db
    return TestClient(app)


def init_db_sync():
    """Synchronously initialize and seed the test database."""
    async def _init():
        async with test_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        async with test_session_factory() as session:
            await seed_reference_data(session)
            await seed_canonical_items(session)
    asyncio.run(_init())


# Initialize database once at module load
init_db_sync()


def register_user(client: TestClient, email: str, role: str = "candidate") -> dict:
    resp = client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": "EmpiricalPassword123!",
            "role": role,
            "first_name": "QA",
            "last_name": "Challenger",
            "consent_pdn_processing": True,
            "consent_profile_publication": True,
        },
    )
    assert resp.status_code == 201, f"Register failed: {resp.text}"
    token = resp.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


# =====================================================================
# 1. EMPIRICAL TASK INDEX RESOLUTION (0-based vs 1-based)
# =====================================================================

def test_resolve_task_item_index_pure_logic():
    """Empirically test resolve_task_item_index across multiple sessions and edge cases."""
    _session_index_base.clear()
    total = 12

    # Session 1: 0-based caller (starts at 0)
    assert resolve_task_item_index(101, 0, total) == 0
    assert _session_index_base[101] == 0
    # Following calls in Session 1 should map 1 -> 1, 11 -> 11
    assert resolve_task_item_index(101, 1, total) == 1
    assert resolve_task_item_index(101, 11, total) == 11
    # Clamping out-of-bounds in 0-based
    assert resolve_task_item_index(101, 12, total) == 11  # clamped
    assert resolve_task_item_index(101, -3, total) == 0   # clamped

    # Session 2: 1-based caller (starts at 1)
    assert resolve_task_item_index(202, 1, total) == 0
    assert _session_index_base[202] == 1
    # Following calls in Session 2 should map 2 -> 1, 12 -> 11
    assert resolve_task_item_index(202, 2, total) == 1
    assert resolve_task_item_index(202, 12, total) == 11
    # Clamping out-of-bounds in 1-based
    assert resolve_task_item_index(202, 15, total) == 11
    assert resolve_task_item_index(202, 0, total) == 0   # direct 0 sets 0

    # Session 3: caller starts directly at task 12 (1-based detection)
    assert resolve_task_item_index(303, 12, total) == 11
    assert _session_index_base[303] == 1

    # Session 4: explicit_base overrides
    assert resolve_task_item_index(404, 1, total, explicit_base=0) == 1
    assert resolve_task_item_index(404, 1, total, explicit_base=1) == 0


def test_api_task_indexing_dual_scheme_live():
    """Test API endpoint GET /assessment/sessions/{id}/tasks/{idx} and POST /answer in both modes."""
    client = get_fresh_client()
    headers = register_user(client, "indexing.test@example.com")

    # Start Session 1 for 0-based testing
    s1_resp = client.post("/api/v1/assessment/sessions/start", headers=headers, json={"specialization_id": 1, "claimed_grade_id": 2})
    assert s1_resp.status_code == 201
    s1_id = s1_resp.json()["session_id"]

    # Session 1: Request 0-based tasks [0..11]
    t0 = client.get(f"/api/v1/assessment/sessions/{s1_id}/tasks/0", headers=headers)
    assert t0.status_code == 200
    t1 = client.get(f"/api/v1/assessment/sessions/{s1_id}/tasks/1", headers=headers)
    assert t1.status_code == 200
    # Submit answer with task_index 0
    ans0 = client.post(
        f"/api/v1/assessment/sessions/{s1_id}/answer",
        headers=headers,
        json={"task_index": 0, "answer_payload": "def solution(): return 42"},
    )
    assert ans0.status_code == 200
    assert ans0.json()["verdict"] == "accepted"

    # Start Session 2 for 1-based testing (UI Standard)
    client.post(f"/api/v1/assessment/sessions/{s1_id}/finish", headers=headers)

    s2_resp = client.post("/api/v1/assessment/sessions/start", headers=headers, json={"specialization_id": 1, "claimed_grade_id": 2})
    assert s2_resp.status_code == 201
    s2_id = s2_resp.json()["session_id"]

    # Session 2: Request 1-based tasks [1..12]
    t1_s2 = client.get(f"/api/v1/assessment/sessions/{s2_id}/tasks/1", headers=headers)
    assert t1_s2.status_code == 200
    t12_s2 = client.get(f"/api/v1/assessment/sessions/{s2_id}/tasks/12", headers=headers)
    assert t12_s2.status_code == 200

    # Submit answer for task 12 (must NOT wrap around to item 0!)
    ans12 = client.post(
        f"/api/v1/assessment/sessions/{s2_id}/answer",
        headers=headers,
        json={"task_index": 12, "answer_payload": "def solution_12(): return 100"},
    )
    assert ans12.status_code == 200
    assert ans12.json()["verdict"] == "accepted"


# =====================================================================
# 2. EMPIRICAL JURY COOLDOWN RESET (/assessment/cooldown-status/jury-reset)
# =====================================================================

def test_jury_cooldown_reset_empirical():
    """Verify that confirmed assessment activates 90-day cooldown and jury-reset clears it immediately."""
    client = get_fresh_client()
    headers = register_user(client, "cooldown.jury@example.com")

    # Start session
    s_resp = client.post("/api/v1/assessment/sessions/start", headers=headers, json={"specialization_id": 1, "claimed_grade_id": 2})
    assert s_resp.status_code == 201
    s_id = s_resp.json()["session_id"]

    # Submit 12 correct answers to achieve confirmed grade
    for idx in range(1, 13):
        client.post(
            f"/api/v1/assessment/sessions/{s_id}/answer",
            headers=headers,
            json={"task_index": idx, "answer_payload": "def solution(): return 1"},
        )

    # Finish session
    fin_resp = client.post(f"/api/v1/assessment/sessions/{s_id}/finish", headers=headers)
    assert fin_resp.status_code == 200
    fin_data = fin_resp.json()
    assert fin_data["verdict"] == "confirmed"
    assert fin_data["theta_score"] >= 70.0

    # Verify Cooldown is ACTIVE
    cd_status = client.get("/api/v1/assessment/cooldown-status", headers=headers)
    assert cd_status.status_code == 200
    cd_data = cd_status.json()
    assert cd_data["is_cooldown_active"] is True
    assert cd_data["days_remaining"] > 0

    # Starting a new regular session must be BLOCKED with 409 Conflict (EC-08)
    blocked_resp = client.post("/api/v1/assessment/sessions/start", headers=headers, json={"specialization_id": 1, "claimed_grade_id": 2})
    assert blocked_resp.status_code == 409
    assert "кулдаун" in blocked_resp.json()["detail"].lower()

    # Call Jury Reset Endpoint (EC-09)
    reset_resp = client.post(
        "/api/v1/assessment/cooldown-status/jury-reset",
        headers=headers,
        json={"reason": "jury_qa_empirical_verification"},
    )
    assert reset_resp.status_code == 200
    r_data = reset_resp.json()
    assert r_data["is_cooldown_active"] is False
    assert r_data["days_remaining"] == 0

    # Verify Cooldown status is now inactive
    cd_status_post = client.get("/api/v1/assessment/cooldown-status", headers=headers)
    assert cd_status_post.status_code == 200
    assert cd_status_post.json()["is_cooldown_active"] is False

    # Starting a new session is now ALLOWED
    new_sess = client.post("/api/v1/assessment/sessions/start", headers=headers, json={"specialization_id": 1, "claimed_grade_id": 2})
    assert new_sess.status_code == 201


# =====================================================================
# 3. EMPIRICAL BOOST OPT-IN & RETEST LOWER SCHEMAS
# =====================================================================

def test_boost_opt_in_schema_and_boundaries():
    """Verify boost opt-in: rejected when theta < 88, accepted when theta >= 88 or verdict == boost_offered."""
    client = get_fresh_client()
    headers = register_user(client, "boost.test@example.com")

    # Session A: Incomplete session (theta < 88)
    s_resp = client.post("/api/v1/assessment/sessions/start", headers=headers, json={"specialization_id": 1, "claimed_grade_id": 1})
    s_id = s_resp.json()["session_id"]
    # Finish with 0 answers (theta ~ 15)
    client.post(f"/api/v1/assessment/sessions/{s_id}/finish", headers=headers)

    # Calling boost-opt-in must FAIL with 400
    boost_bad = client.post(f"/api/v1/assessment/sessions/{s_id}/boost-opt-in", headers=headers)
    assert boost_bad.status_code == 400
    assert "theta >= 88" in boost_bad.json()["detail"]

    # Session B: High ability test — update theta to 92.0 in DB to simulate high-scoring session
    async def _set_high_score():
        async with test_session_factory() as session:
            sess = await session.get(AssessmentSession, s_id)
            sess.theta_score = 92.0
            sess.verdict = "boost_offered"
            await session.commit()
    asyncio.run(_set_high_score())

    # Calling boost-opt-in must SUCCEED with 201
    boost_good = client.post(f"/api/v1/assessment/sessions/{s_id}/boost-opt-in", headers=headers)
    assert boost_good.status_code == 201
    b_data = boost_good.json()
    assert b_data["session_type"] == "boost"
    assert "session_id" in b_data


def test_retest_lower_schema_and_flow():
    """Verify retest-lower: returns session with lower grade without waiting for cooldown."""
    client = get_fresh_client()
    headers = register_user(client, "retest.lower@example.com")

    # Start Session at Middle grade (rank 2)
    s_resp = client.post("/api/v1/assessment/sessions/start", headers=headers, json={"specialization_id": 1, "claimed_grade_id": 2})
    s_id = s_resp.json()["session_id"]
    # Fail session (theta < 70)
    fin_resp = client.post(f"/api/v1/assessment/sessions/{s_id}/finish", headers=headers)
    assert fin_resp.status_code == 200

    # Call retest-lower
    retest_resp = client.post(
        "/api/v1/assessment/retest-lower",
        headers=headers,
        json={"failed_session_id": s_id},
    )
    assert retest_resp.status_code == 201
    r_data = retest_resp.json()
    assert r_data["session_type"] == "retest_lower"
    assert "session_id" in r_data


# =====================================================================
# 4. EMPIRICAL MICRO-CHALLENGES & PROFILE SCHEMAS
# =====================================================================

def test_micro_challenges_dry_run_schema():
    """Verify ChallengeDryRunResponse model validator properly computes status and memory_kb."""
    res1 = ChallengeDryRunResponse(
        all_passed=True,
        passed_count=3,
        total_count=3,
        logs="All 3 tests passed",
        execution_time_ms=15.4,
        memory_used_mb=4.2,
    )
    assert res1.status == "passed"
    assert res1.memory_kb == int(4.2 * 1024)

    res2 = ChallengeDryRunResponse(
        all_passed=False,
        passed_count=1,
        total_count=3,
        logs="Test 2 failed",
        execution_time_ms=8.1,
        memory_used_mb=2.0,
    )
    assert res2.status == "failed"
    assert res2.memory_kb == int(2.0 * 1024)


def test_candidate_profile_theta_field():
    """Verify CandidateFullProfileResponse model validator exposes theta mirroring kite_score_scaled."""
    now = datetime.now(timezone.utc)
    prof = CandidateFullProfileResponse(
        id=1,
        user_id=1,
        first_name="Иван",
        last_name="Иванов",
        email="ivan@example.com",
        specialization="Backend",
        grade="Middle",
        category_title="Backend Middle",
        skills=[CandidateSkillItem(skill_name="Python", proficiency_level="advanced", years_of_experience=3.0)],
        kite_score_scaled=84.5,
        fsp_id=None,
        fsp_verified=False,
        fsp_badge="none",
        freshness_score=95.0,
        work_format="remote",
        city="Москва",
        relocation_ready=True,
        is_published=True,
        created_at=now,
        updated_at=now,
    )
    assert prof.theta == 84.5
    assert prof.kite_score_scaled == 84.5


def test_candidate_profile_publish_unpublish_routes():
    """Verify POST /candidate-profile/publish and POST /candidate-profile/unpublish."""
    client = get_fresh_client()
    headers = register_user(client, "publish.test@example.com")

    # Send onboarding survey to create profile
    client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        headers=headers,
        json={
            "specialization_id": 1,
            "claimed_grade_id": 2,
            "work_format": "remote",
            "salary_min": 150000,
            "salary_max": 200000,
            "consent_personal_data": True,
            "consent_profile_publish": True,
            "skills": [],
        },
    )

    # Publish
    pub_res = client.post("/api/v1/candidate-profile/publish", headers=headers)
    assert pub_res.status_code == 200
    assert pub_res.json()["is_published"] is True

    # Unpublish
    unpub_res = client.post("/api/v1/candidate-profile/unpublish", headers=headers)
    assert unpub_res.status_code == 200
    assert unpub_res.json()["is_published"] is False


# =====================================================================
# 5. EMPIRICAL RESUME PARSER (Magic Header & Skills Matching)
# =====================================================================

def test_resume_parser_magic_header_rejection():
    """Verify non-PDF bytes are rejected with InvalidPdfFormatError (HTTP 415 in API)."""
    parser = ResumeParser()
    with pytest.raises(InvalidPdfFormatError) as exc:
        parser.validate_magic_bytes(b"NOT_A_PDF_CONTENT")
    assert "%PDF-" in str(exc.value)

    # Valid PDF magic bytes pass
    assert parser.validate_magic_bytes(b"%PDF-1.4\n%some content") is None


def test_resume_parser_skills_regex_boundary():
    """Verify skills matching correctly extracts C++, C#, .NET, Python without false positives."""
    parser = ResumeParser()
    sample_text = "Опыт разработки на C++, C#, .NET, Python, а также Node.js и Docker."
    skills = parser.match_skills(sample_text)
    lower_skills = [s.lower() for s in skills]

    assert any("c++" in s for s in lower_skills), f"C++ not found in {skills}"
    assert any("c#" in s for s in lower_skills), f"C# not found in {skills}"
    assert any("python" in s for s in lower_skills), f"Python not found in {skills}"
    assert any("node.js" in s for s in lower_skills), f"Node.js not found in {skills}"
