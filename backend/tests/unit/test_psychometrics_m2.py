"""
Unit tests for Psychometrics & IRT, Session Scoring, Dynamic Filtering (Milestone 2):
- R5: Live 3PL Birnbaum Parameters from DB in finish_assessment_session
- R6: Session Timeout check, honest answer evaluation, real execution_time_ms
- R7: CandidateCategorization persistence upon session finish with atomic is_current update
- R8: Candidate bank salary filtering (min_salary, max_salary) and zero theta for untested
- R10: Onboarding survey skill years_experience and proficiency_level persistence
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
from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.v1.assessment import finish_assessment_session, submit_task_answer
from app.api.v1.candidate_bank import _build_candidate_card, search_candidate_bank
from app.api.v1.candidate_profile import submit_onboarding_survey
from app.models.assessment_answers import AssessmentAnswer
from app.models.assessment_sessions import AssessmentSession
from app.models.base import Base
from app.models.candidate_categorizations import CandidateCategorization
from app.models.candidate_profiles import CandidateProfile
from app.models.candidate_skills import CandidateSkill
from app.models.canonical_item_families import CanonicalItemFamily
from app.models.categories import Category
from app.models.employer_profiles import EmployerProfile
from app.models.grades import Grade
from app.models.skills import Skill
from app.models.specializations import Specialization
from app.models.users import User
from app.schemas.assessment import SubmitTaskAnswerRequest
from app.schemas.candidate_profile import OnboardingSurveyRequest, WorkFormatEnum


async def _create_test_db():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    return engine, session_factory


def test_session_timeout_check():
    """R6: submit_task_answer raises HTTP 410 when now > expires_at."""
    async def _run():
        engine, session_factory = await _create_test_db()
        async with session_factory() as db:
            user = User(id=1, email="cand@test.com", hashed_password="x", role="candidate")
            cand = CandidateProfile(id=1, user_id=1, first_name="A", last_name="B")
            spec = Specialization(id=1, name="Backend", code="backend")
            grade = Grade(id=2, name="Middle", code="middle", rank_order=2)
            cat = Category(id=1, specialization_id=1, grade_id=2, title="Backend Middle", slug="backend_middle")
            db.add_all([user, cand, spec, grade, cat])
            await db.flush()

            # Create an expired session
            now = datetime.now(timezone.utc)
            sess = AssessmentSession(
                id=1,
                candidate_profile_id=1,
                category_id=1,
                session_type="initial",
                seed_hash="abcdef0123456789",
                status="in_progress",
                started_at=now - timedelta(minutes=100),
                expires_at=now - timedelta(minutes=10),
            )
            db.add(sess)
            await db.commit()

            req = SubmitTaskAnswerRequest(task_index=0, answer_payload="A", time_spent_seconds=10)
            with pytest.raises(HTTPException) as exc_info:
                await submit_task_answer(session_id=1, payload=req, current_user=user, db=db)
            assert exc_info.value.status_code == 410
            assert "Время тестирования истекло" in str(exc_info.value.detail)

    asyncio.run(_run())


def test_honest_answer_evaluation_and_real_timing():
    """R6: Evaluates MCQ against variant seed and coding against public tests with real execution_time_ms."""
    async def _run():
        engine, session_factory = await _create_test_db()
        async with session_factory() as db:
            user = User(id=2, email="cand2@test.com", hashed_password="x", role="candidate")
            cand = CandidateProfile(id=2, user_id=2, first_name="A", last_name="B")
            spec = Specialization(id=1, name="Backend", code="backend")
            grade = Grade(id=2, name="Middle", code="middle", rank_order=2)
            cat = Category(id=1, specialization_id=1, grade_id=2, title="Backend Middle", slug="backend_middle")
            # Create MCQ item and Coding item
            mcq_item = CanonicalItemFamily(
                id=1,
                specialization_id=1,
                grade_id=2,
                family_code="mcq_fam_1",
                task_type="mcq",
                title="MCQ Question",
                template_text="Question text",
                param_matrix_json={},
                test_generator_code="def gen(): pass",
                param_a=1.4,
                param_b=0.2,
                param_c=0.2,
                is_active=True,
            )
            code_item = CanonicalItemFamily(
                id=2,
                specialization_id=1,
                grade_id=2,
                family_code="code_fam_2",
                task_type="algorithmic",
                title="Coding Question",
                template_text="Code question {{window_size}}",
                param_matrix_json={"window_size": {"type": "range_int", "min": 3, "max": 5, "step": 1}},
                test_generator_code="def gen(): pass",
                param_a=2.0,
                param_b=0.5,
                param_c=0.0,
                is_active=True,
            )
            now = datetime.now(timezone.utc)
            sess = AssessmentSession(
                id=2,
                candidate_profile_id=2,
                category_id=1,
                session_type="initial",
                seed_hash="feedbeef12345678",
                status="in_progress",
                started_at=now,
                expires_at=now + timedelta(minutes=90),
            )
            db.add_all([user, cand, spec, grade, cat, mcq_item, code_item, sess])
            await db.commit()

            # Submit answer to MCQ item (task_index=0)
            from app.services.isomorphic_generator import IsomorphicGenerator
            gen = IsomorphicGenerator()
            variant = gen.generate_variant(2, 2, 1, mcq_item.template_text, {})
            correct_opt = ["A", "B", "C", "D"][variant["seed_int"] % 4]
            wrong_opt = "B" if correct_opt != "B" else "C"

            # 1. Correct MCQ option
            req_correct = SubmitTaskAnswerRequest(task_index=0, answer_payload=correct_opt)
            res_correct = await submit_task_answer(session_id=2, payload=req_correct, current_user=user, db=db)
            assert res_correct.verdict == "accepted"
            assert res_correct.passed_public_tests == 3
            assert res_correct.execution_time_ms > 0.0

            # 2. Wrong MCQ option
            req_wrong = SubmitTaskAnswerRequest(task_index=0, answer_payload=wrong_opt)
            res_wrong = await submit_task_answer(session_id=2, payload=req_wrong, current_user=user, db=db)
            assert res_wrong.verdict == "wrong_answer"
            assert res_wrong.passed_public_tests == 0

            # 3. Coding task with valid code
            code_variant = gen.generate_variant(2, 2, 2, code_item.template_text, code_item.param_matrix_json)
            # Submit correct code: max of first window_size elements
            correct_code = "def solution(records):\n    return max(records[:3])\n"
            req_code = SubmitTaskAnswerRequest(task_index=1, answer_payload={"code": correct_code})
            res_code = await submit_task_answer(session_id=2, payload=req_code, current_user=user, db=db)
            assert res_code.execution_time_ms > 0.0
            assert res_code.execution_time_ms != 18.5  # Real measurement, not stub

    asyncio.run(_run())


def test_live_3pl_parameters_and_categorization_persistence():
    """R5 & R7: finish_assessment_session uses DB 3PL parameters and persists CandidateCategorization."""
    async def _run():
        engine, session_factory = await _create_test_db()
        async with session_factory() as db:
            user = User(id=3, email="cand3@test.com", hashed_password="x", role="candidate")
            cand = CandidateProfile(id=3, user_id=3, first_name="A", last_name="B")
            spec = Specialization(id=1, name="Backend", code="backend")
            grade_middle = Grade(id=2, name="Middle", code="middle", rank_order=2)
            cat_middle = Category(id=1, specialization_id=1, grade_id=2, title="Backend Middle", slug="backend_middle")
            db.add_all([user, cand, spec, grade_middle, cat_middle])

            # Seed 12 canonical item families with calibrated parameters
            items = []
            for i in range(1, 13):
                item = CanonicalItemFamily(
                    id=i,
                    specialization_id=1,
                    grade_id=2,
                    family_code=f"family_kite_{i}",
                    task_type="mcq" if i <= 4 else "algorithmic",
                    title=f"Task {i}",
                    template_text=f"Template {i}",
                    param_matrix_json={},
                    test_generator_code="def gen(): pass",
                    param_a=1.2 + (i * 0.1),
                    param_b=-0.5 + (i * 0.2),
                    param_c=0.15 if i <= 4 else 0.0,
                    is_active=True,
                )
                items.append(item)
                db.add(item)

            now = datetime.now(timezone.utc)
            # Prior existing categorization that should be deactivated
            old_cat = CandidateCategorization(
                candidate_profile_id=3,
                category_id=1,
                confirmed_grade_id=2,
                test_score=60.0,
                assigned_at=now - timedelta(days=10),
                cooldown_until=now - timedelta(days=1),
                is_current=True,
                source_session_id=100,
            )
            db.add(old_cat)

            # Session to finish
            sess = AssessmentSession(
                id=3,
                candidate_profile_id=3,
                category_id=1,
                session_type="initial",
                seed_hash="1122334455667788",
                status="in_progress",
                started_at=now - timedelta(minutes=30),
                expires_at=now + timedelta(minutes=60),
            )
            db.add(sess)
            await db.flush()

            # Add answers for all 12 items as correct
            for item in items:
                ans = AssessmentAnswer(
                    session_id=3,
                    item_family_id=item.id,
                    candidate_answer_text="A",
                    submitted_code="A",
                    is_correct=True,
                    points_awarded=1.0,
                    time_taken_sec=30,
                )
                db.add(ans)
            await db.commit()

            # Call finish_assessment_session
            res = await finish_assessment_session(session_id=3, current_user=user, db=db)
            assert res.status == "completed"
            assert res.theta_score > 70.0

            # Verify CandidateCategorization in DB
            cat_stmt = select(CandidateCategorization).where(
                CandidateCategorization.candidate_profile_id == 3
            ).order_by(CandidateCategorization.id.asc())
            cats = list((await db.execute(cat_stmt)).scalars().all())
            assert len(cats) == 2

            # Prior categorization must now be is_current=False
            assert cats[0].id == old_cat.id
            assert cats[0].is_current is False

            # New categorization must be is_current=True with the test score
            new_cat = cats[1]
            assert new_cat.is_current is True
            assert new_cat.source_session_id == 3
            assert new_cat.category_id == 1
            assert new_cat.confirmed_grade_id == 2
            assert round(new_cat.test_score, 1) == round(res.theta_score, 1)
            assert new_cat.cooldown_until is not None

    asyncio.run(_run())


def test_candidate_bank_salary_filters_and_zero_theta():
    """R8: Candidate bank SQL salary filters and zero theta for untested candidates."""
    async def _run():
        engine, session_factory = await _create_test_db()
        async with session_factory() as db:
            emp_user = User(id=10, email="emp@company.com", hashed_password="x", role="employer")
            emp = EmployerProfile(id=1, user_id=10, company_name="TechCorp", inn="7701234567", domain="techcorp.ru")
            db.add_all([emp_user, emp])

            # Candidate 1: salary 150_000, untested
            c1_u = User(id=11, email="c1@test.com", hashed_password="x", role="candidate")
            c1 = CandidateProfile(id=11, user_id=11, first_name="Low", last_name="Sal", expected_salary=150_000, is_published=True)

            # Candidate 2: salary 250_000, untested
            c2_u = User(id=12, email="c2@test.com", hashed_password="x", role="candidate")
            c2 = CandidateProfile(id=12, user_id=12, first_name="Mid", last_name="Sal", expected_salary=250_000, is_published=True)

            # Candidate 3: salary 400_000, untested
            c3_u = User(id=13, email="c3@test.com", hashed_password="x", role="candidate")
            c3 = CandidateProfile(id=13, user_id=13, first_name="High", last_name="Sal", expected_salary=400_000, is_published=True)

            db.add_all([c1_u, c1, c2_u, c2, c3_u, c3])
            await db.commit()

            # 1. Test salary filter min_salary=200_000, max_salary=300_000
            res = await search_candidate_bank(
                specialization=None,
                grade=None,
                need_id=None,
                city=None,
                work_format=None,
                relocation_ready=None,
                skills=None,
                min_salary=200_000,
                max_salary=300_000,
                fsp_only=False,
                page=1,
                page_size=20,
                current_user=emp_user,
                db=db,
            )
            cands = res.items
            assert len(cands) == 1
            assert cands[0].id == 12

            # Untested candidate card must have test_score = 0.0 (not 75.0)
            assert cands[0].test_score == 0.0

            # 2. Test card builder standalone
            card = _build_candidate_card(c1)
            assert card.test_score == 0.0

    asyncio.run(_run())


def test_onboarding_survey_skills_experience_and_proficiency():
    """R10: Parse years_experience and proficiency_level and save in CandidateSkill."""
    async def _run():
        engine, session_factory = await _create_test_db()
        async with session_factory() as db:
            cand_user = User(id=20, email="onboarding@test.com", hashed_password="x", role="candidate")
            cand = CandidateProfile(id=20, user_id=20, first_name="Dev", last_name="Tester")
            spec = Specialization(id=1, name="Backend", code="backend")
            grade = Grade(id=2, name="Middle", code="middle", rank_order=2)
            sk1 = Skill(id=1, name="FastAPI", slug="fastapi", specialization_id=1)
            sk2 = Skill(id=2, name="PostgreSQL", slug="postgresql", specialization_id=1)
            db.add_all([cand_user, cand, spec, grade, sk1, sk2])
            await db.commit()

            # Submit survey with custom experience and proficiency
            payload = OnboardingSurveyRequest(
                specialization_id=1,
                claimed_grade_id=2,
                skills=[
                    {"skill_id": 1, "years_experience": 4.5, "proficiency_level": "advanced", "is_core": True},
                    {"skill_name": "PostgreSQL", "years_experience": 3.0, "proficiency_level": "expert", "is_core": False},
                ],
                city="Москва",
                work_format=WorkFormatEnum.REMOTE,
                salary_min=200_000,
                salary_max=280_000,
            )

            res = await submit_onboarding_survey(payload=payload, current_user=cand_user, db=db)
            assert res.status == "onboarding_completed"

            # Check CandidateSkill in DB
            skills_stmt = select(CandidateSkill).where(CandidateSkill.candidate_profile_id == 20)
            skills = list((await db.execute(skills_stmt)).scalars().all())
            assert len(skills) == 2

            skill_map = {s.skill_id: s for s in skills}
            assert skill_map[1].years_experience == 4.5
            assert skill_map[1].proficiency_level == "advanced"
            assert skill_map[1].is_core is True

            assert skill_map[2].years_experience == 3.0
            assert skill_map[2].proficiency_level == "expert"
            assert skill_map[2].is_core is False

    asyncio.run(_run())
