"""
Unit tests for 152-ФЗ Anonymizer & Multi-Tenant Access Controller.
Defined in app/services/anonymizer.py.
"""
from __future__ import annotations

import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models.applications import Application
from app.models.base import Base
from app.models.candidate_profiles import CandidateProfile
from app.models.employer_profiles import EmployerProfile
from app.models.invitations import Invitation
from app.models.users import User
from app.models.vacancies import Vacancy
from app.services.anonymizer import (
    check_contact_access,
    format_full_name,
    format_masked_name,
    mask_candidate_profile,
)


def test_format_masked_name():
    res = format_masked_name("Алексей", "Кузнецов", 1042)
    assert res == "Алексей К. (#C-1042)"

    res_no_last = format_masked_name("Иван", "", 55)
    assert res_no_last == "Иван (#C-55)"


def test_format_full_name():
    res = format_full_name("Алексей", "Кузнецов", "Игоревич")
    assert res == "Алексей Кузнецов Игоревич"

    res_no_middle = format_full_name("Мария", "Соколова", None)
    assert res_no_middle == "Мария Соколова"


def test_mask_candidate_profile_masked():
    class DummyCandidate:
        id = 42
        first_name = "Дмитрий"
        last_name = "Петров"
        middle_name = "Сергеевич"
        phone = "+79991234567"
        telegram = "@dmitry"
        github_url = "https://github.com/dmitry"
        raw_resume_pdf_path = "/storage/resumes/42.pdf"
        user = None

    cand = DummyCandidate()
    masked = mask_candidate_profile(cand, is_unmasked=False)

    assert masked["is_contacts_masked"] is True
    assert masked["email"] is None
    assert masked["phone"] is None
    assert masked["telegram"] is None
    assert masked["github_url"] is None
    assert masked["raw_resume_pdf_path"] is None
    assert masked["full_name"] == "Дмитрий П. (#C-42)"


def test_mask_candidate_profile_unmasked():
    class DummyCandidate:
        id = 42
        first_name = "Дмитрий"
        last_name = "Петров"
        middle_name = "Сергеевич"
        phone = "+79991234567"
        telegram = "@dmitry"
        github_url = "https://github.com/dmitry"
        raw_resume_pdf_path = "/storage/resumes/42.pdf"
        user = None

    cand = DummyCandidate()
    unmasked = mask_candidate_profile(cand, is_unmasked=True, user_email="dmitry@corp.ru")

    assert unmasked["is_contacts_masked"] is False
    assert unmasked["email"] == "dmitry@corp.ru"
    assert unmasked["phone"] == "+79991234567"
    assert unmasked["telegram"] == "@dmitry"
    assert unmasked["github_url"] == "https://github.com/dmitry"
    assert unmasked["raw_resume_pdf_path"] == "/storage/resumes/42.pdf"
    assert unmasked["full_name"] == "Дмитрий Петров Сергеевич"


import asyncio

def test_check_contact_access_rules():
    async def _run():
        # Setup in-memory sqlite db for async test
        engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
        session_factory = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

        async with session_factory() as db:
            # 1. Users
            admin_user = User(email="admin@fsp.ru", hashed_password="x", role="admin", is_active=True)
            cand_user_1 = User(email="cand1@fsp.ru", hashed_password="x", role="candidate", is_active=True)
            cand_user_2 = User(email="cand2@fsp.ru", hashed_password="x", role="candidate", is_active=True)
            emp_user_a = User(email="emp_a@corp.ru", hashed_password="x", role="employer", is_active=True)
            emp_user_b = User(email="emp_b@corp.ru", hashed_password="x", role="employer", is_active=True)
            db.add_all([admin_user, cand_user_1, cand_user_2, emp_user_a, emp_user_b])
            await db.flush()

            # 2. Profiles
            cand_prof_1 = CandidateProfile(user_id=cand_user_1.id, first_name="Алексей", last_name="Кузнецов")
            cand_prof_2 = CandidateProfile(user_id=cand_user_2.id, first_name="Ольга", last_name="Смирнова")
            emp_prof_a = EmployerProfile(user_id=emp_user_a.id, company_name="Компани А", inn="7701234567", domain="comp-a.ru")
            emp_prof_b = EmployerProfile(user_id=emp_user_b.id, company_name="Компани Б", inn="7702345678", domain="comp-b.ru")
            db.add_all([cand_prof_1, cand_prof_2, emp_prof_a, emp_prof_b])
            await db.flush()

            # Rule 1: Admin has full access
            assert await check_contact_access(db, cand_prof_1.id, admin_user) is True

            # Rule 2: Candidate has access to own profile
            assert await check_contact_access(db, cand_prof_1.id, cand_user_1) is True

            # Rule 3: Candidate does NOT have access to other candidate
            assert await check_contact_access(db, cand_prof_1.id, cand_user_2) is False

            # Rule 4: Employer A initially has NO access
            assert await check_contact_access(db, cand_prof_1.id, emp_user_a, emp_prof_a.id) is False

            # Rule 5: Pending invitation (status='sent') does NOT grant access
            inv_pending = Invitation(
                employer_profile_id=emp_prof_a.id,
                candidate_profile_id=cand_prof_1.id,
                proposal_text="Предлагаем оффер",
                salary_min=150000,
                salary_max=200000,
                status="sent",
            )
            db.add(inv_pending)
            await db.flush()
            assert await check_contact_access(db, cand_prof_1.id, emp_user_a, emp_prof_a.id) is False

            # Rule 6: Accepted invitation (status='accepted') grants access to Employer A
            inv_pending.status = "accepted"
            await db.flush()
            assert await check_contact_access(db, cand_prof_1.id, emp_user_a, emp_prof_a.id) is True

            # Rule 7: Multi-tenant isolation: Employer B STILL does NOT have access!
            assert await check_contact_access(db, cand_prof_1.id, emp_user_b, emp_prof_b.id) is False

            # Rule 8: Direct application to Employer B's vacancy grants access to Employer B
            vac_b = Vacancy(
                employer_profile_id=emp_prof_b.id,
                specialization_id=1,
                grade_id=1,
                title="Senior Go Developer",
                description="Developing high load services",
                required_skills_json=["Go", "PostgreSQL"],
                salary_min=250000,
                salary_max=350000,
                status="published",
            )
            db.add(vac_b)
            await db.flush()

            app_b = Application(
                vacancy_id=vac_b.id,
                candidate_profile_id=cand_prof_1.id,
                status="applied",
            )
            db.add(app_b)
            await db.flush()

            assert await check_contact_access(db, cand_prof_1.id, emp_user_b, emp_prof_b.id) is True

        await engine.dispose()

    asyncio.run(_run())
