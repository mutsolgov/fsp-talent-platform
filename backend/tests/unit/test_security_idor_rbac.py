"""
Unit tests for Backend Security Hardening (M1):
- DRY get_or_create_candidate_profile in app.api.deps
- IDOR elimination in assessment session ownership (verify_session_ownership)
- RBAC in candidate_profile.py (submit_onboarding_survey restricted to candidate)
- RBAC and creator ownership in micro_challenges.py (create, update, delete)
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
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.api.deps import get_or_create_candidate_profile
from app.api.v1.assessment import verify_session_ownership
from app.api.v1.candidate_profile import submit_onboarding_survey
from app.api.v1.micro_challenges import (
    create_micro_challenge,
    delete_micro_challenge,
    update_micro_challenge,
)
from app.models.assessment_sessions import AssessmentSession
from app.models.base import Base
from app.models.candidate_profiles import CandidateProfile
from app.models.categories import Category
from app.models.employer_profiles import EmployerProfile
from app.models.grades import Grade
from app.models.micro_challenges import MicroChallenge
from app.models.specializations import Specialization
from app.models.users import User
from app.schemas.candidate_profile import OnboardingSurveyRequest, WorkFormatEnum
from app.schemas.micro_challenges import (
    CreateMicroChallengeRequest,
    TestCaseItem,
    UpdateMicroChallengeRequest,
)


def test_deps_get_or_create_candidate_profile():
    async def _run():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as db:
            # 1. Create user
            user = User(
                id=101,
                email="cand1@fsp.ru",
                hashed_password="hash",
                role="candidate",
            )
            db.add(user)
            await db.flush()

            # 2. First call: creates profile lazily
            prof1 = await get_or_create_candidate_profile(user.id, db)
            assert prof1 is not None
            assert prof1.user_id == 101
            assert prof1.first_name == "Соискатель"
            assert prof1.last_name == "ФСП"

            # 3. Second call: returns existing profile
            prof2 = await get_or_create_candidate_profile(user.id, db)
            assert prof2.id == prof1.id

        await engine.dispose()

    asyncio.run(_run())


def test_verify_session_ownership_idor():
    async def _run():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as db:
            # Seed spec, grade, category
            spec = Specialization(id=1, code="backend", name="Backend")
            grade = Grade(id=1, code="junior", name="Junior", rank_order=1)
            db.add_all([spec, grade])
            await db.flush()

            cat = Category(id=1, specialization_id=1, grade_id=1, slug="backend-junior", title="Backend Junior")
            db.add(cat)
            await db.flush()

            # User 1 (candidate, owner)
            user1 = User(id=1, email="cand1@fsp.ru", hashed_password="h", role="candidate")
            # User 2 (candidate, attacker / other user)
            user2 = User(id=2, email="cand2@fsp.ru", hashed_password="h", role="candidate")
            # User 3 (admin)
            user_admin = User(id=3, email="admin@fsp.ru", hashed_password="h", role="admin")

            db.add_all([user1, user2, user_admin])
            await db.flush()

            prof1 = await get_or_create_candidate_profile(user1.id, db)
            prof2 = await get_or_create_candidate_profile(user2.id, db)
            await db.flush()

            # Session belonging to User 1
            sess = AssessmentSession(
                id=10,
                candidate_profile_id=prof1.id,
                category_id=cat.id,
                session_type="initial",
                seed_hash="dummy_seed",
                status="in_progress",
                expires_at=datetime.now(timezone.utc) + timedelta(hours=1),
            )
            db.add(sess)
            await db.flush()

            # 1. Owner access: User 1 passes verification
            await verify_session_ownership(sess, user1, db)

            # 2. Admin access: Admin passes verification
            await verify_session_ownership(sess, user_admin, db)

            # 3. IDOR: User 2 must be rejected with 403 Forbidden
            with pytest.raises(HTTPException) as exc_info:
                await verify_session_ownership(sess, user2, db)

            assert exc_info.value.status_code == 403
            assert exc_info.value.detail == "Нет доступа к чужой тест-сессии"

        await engine.dispose()

    asyncio.run(_run())


def test_candidate_onboarding_rbac():
    async def _run():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as db:
            # Seed specialization and grade
            spec = Specialization(id=1, code="backend", name="Backend")
            grade = Grade(id=1, code="junior", name="Junior", rank_order=1)
            db.add_all([spec, grade])
            await db.flush()

            emp_user = User(id=201, email="hr@company.ru", hashed_password="h", role="employer")
            cand_user = User(id=202, email="c@fsp.ru", hashed_password="h", role="candidate")
            db.add_all([emp_user, cand_user])
            await db.flush()

            req = OnboardingSurveyRequest(
                specialization_id=1,
                claimed_grade_id=1,
                city="Москва",
                work_format=WorkFormatEnum.REMOTE,
                relocation_ready=False,
                skills=["Python", "FastAPI"],
                consent_personal_data=True,
                consent_profile_publish=True,
            )

            # 1. Employer submitting survey -> 403 Forbidden
            with pytest.raises(HTTPException) as exc_info:
                await submit_onboarding_survey(req, current_user=emp_user, db=db)

            assert exc_info.value.status_code == 403
            assert exc_info.value.detail == "Только соискатели могут заполнять анкету онбординга"

            # 2. Candidate submitting survey -> 201 Created
            res = await submit_onboarding_survey(req, current_user=cand_user, db=db)
            assert res.profile_id is not None
            assert res.status == "onboarding_completed"

        await engine.dispose()

    asyncio.run(_run())


def test_micro_challenge_rbac_and_ownership():
    async def _run():
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
        async with session_factory() as db:
            # Seed spec and grade
            spec = Specialization(id=1, code="backend", name="Backend")
            grade = Grade(id=2, code="middle", name="Middle", rank_order=2)
            db.add_all([spec, grade])
            await db.flush()

            # Create users
            cand_user = User(id=301, email="cand@fsp.ru", hashed_password="h", role="candidate")
            emp_user_a = User(id=302, email="emp_a@tech.ru", hashed_password="h", role="employer")
            emp_user_b = User(id=303, email="emp_b@fin.ru", hashed_password="h", role="employer")
            admin_user = User(id=304, email="admin@fsp.ru", hashed_password="h", role="admin")

            db.add_all([cand_user, emp_user_a, emp_user_b, admin_user])
            await db.flush()

            create_req = CreateMicroChallengeRequest(
                title="Оптимизация SQL-запроса",
                description_markdown="Напишите оптимальный запрос",
                specialization_id=1,
                grade_id=2,
                test_cases=[TestCaseItem(input="SELECT 1", expected_output="1", is_public=True)],
                points=30,
            )

            # 1. Candidate creating challenge -> 403 Forbidden
            with pytest.raises(HTTPException) as exc_cand:
                await create_micro_challenge(create_req, current_user=cand_user, db=db)
            assert exc_cand.value.status_code == 403
            assert "работодатели и администраторы" in exc_cand.value.detail

            # 2. Employer A creating challenge -> success, sets employer_profile_id
            created = await create_micro_challenge(create_req, current_user=emp_user_a, db=db)
            assert created.id is not None

            # Verify challenge is linked to Employer A's profile
            challenge = await db.get(MicroChallenge, created.id)
            assert challenge is not None
            assert challenge.employer_profile_id is not None

            emp_a_profile = await db.scalar(
                select(EmployerProfile).where(EmployerProfile.user_id == emp_user_a.id)
            )
            assert challenge.employer_profile_id == emp_a_profile.id

            # 3. Employer B attempting to update challenge -> 403 Forbidden
            update_req = UpdateMicroChallengeRequest(title="Измененный заголовок от B")
            with pytest.raises(HTTPException) as exc_upd:
                await update_micro_challenge(created.id, update_req, current_user=emp_user_b, db=db)
            assert exc_upd.value.status_code == 403
            assert "создавший его работодатель или администратор" in exc_upd.value.detail

            # 4. Employer B attempting to delete challenge -> 403 Forbidden
            with pytest.raises(HTTPException) as exc_del:
                await delete_micro_challenge(created.id, current_user=emp_user_b, db=db)
            assert exc_del.value.status_code == 403
            assert "создавший его работодатель или администратор" in exc_del.value.detail

            # 5. Employer A (creator) updating challenge -> success
            updated = await update_micro_challenge(created.id, update_req, current_user=emp_user_a, db=db)
            assert updated.title == "Измененный заголовок от B"

            # 6. Admin updating challenge -> success
            admin_upd_req = UpdateMicroChallengeRequest(title="Заголовок от Admin")
            admin_updated = await update_micro_challenge(created.id, admin_upd_req, current_user=admin_user, db=db)
            assert admin_updated.title == "Заголовок от Admin"

            # 7. Admin deleting challenge -> success
            del_res = await delete_micro_challenge(created.id, current_user=admin_user, db=db)
            assert del_res.status == "ok"
            assert challenge.is_active is False

        await engine.dispose()

    asyncio.run(_run())
