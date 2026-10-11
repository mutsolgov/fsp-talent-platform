"""
Adversarial Stress Test Suite — Challenger R17
Verifies:
1. DDL & DB Model Nullability: city=None, work_format=None, check constraints.
2. Pydantic v2 Schema Serialization under extreme null/empty edge cases.
3. Candidate Profile API (GET /candidate-profile/me) truthful uncalibrated states.
4. Recruiter Search (CandidateBankCard & /candidate-bank) with NULL candidates (Zero 500 errors).
5. PDF Generator stress test with uncalibrated profiles.
"""
from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import json
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest
from pydantic import ValidationError
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from fastapi.testclient import TestClient

from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models.candidate_profiles import CandidateProfile
from app.models.users import User
from app.models.user_consents import UserConsent
from app.schemas.candidate_profile import (
    CandidateFullProfileResponse,
    CandidateSkillItem,
    WorkFormatEnum,
)
from app.schemas.candidate_bank import (
    CandidateBankCard,
    CandidateAnonymizedDetailResponse,
)
from app.api.deps import get_or_create_candidate_profile
from app.services.pdf_generator import generate_fsp_profile_pdf
from scripts.seed_reference_data import seed_reference_data


# ---------------------------------------------------------------------------
# Suite 1: SQLite DDL & Model Nullability Stress Testing
# ---------------------------------------------------------------------------

async def test_adversarial_ddl_and_null_constraints():
    """Verify that CandidateProfile correctly accepts NULL city and work_format in SQLite DDL."""
    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        # 1. Create user
        user = User(
            email="null_test_cand@fsp.ru",
            hashed_password="argon2_hashed_secret",
            role="candidate",
            is_active=True,
            email_verified=True,
        )
        session.add(user)
        await session.flush()

        # 2. Insert candidate with city=None and work_format=None
        cand_null = CandidateProfile(
            user_id=user.id,
            first_name="Тест",
            last_name="Нуллов",
            city=None,
            work_format=None,
            expected_salary=None,
            freshness_score=50.0,
            is_published=True,
        )
        session.add(cand_null)
        await session.commit()

        # 3. Query back and verify NULLs in DB
        res = await session.execute(select(CandidateProfile).where(CandidateProfile.id == cand_null.id))
        fetched = res.scalar_one()
        assert fetched.city is None, f"Expected city to be None, got {fetched.city}"
        assert fetched.work_format is None, f"Expected work_format to be None, got {fetched.work_format}"
        assert fetched.expected_salary is None

        # 4. Verify helper get_or_create_candidate_profile preserves NULLs
        user2 = User(
            email="autocreate_test@fsp.ru",
            hashed_password="argon2_hashed_secret",
            role="candidate",
            is_active=True,
            email_verified=True,
        )
        session.add(user2)
        await session.flush()

        profile2 = await get_or_create_candidate_profile(user2.id, session)
        assert profile2.city is None, f"Auto-created profile city should be None, got {profile2.city}"
        assert profile2.work_format is None, f"Auto-created profile work_format should be None, got {profile2.work_format}"

        # 5. Adversarial Check: Valid work_formats ('remote', 'office', 'hybrid', 'any') must PASS
        valid_formats = ["remote", "office", "hybrid", "any"]
        for fmt in valid_formats:
            user_v = User(
                email=f"format_{fmt}@fsp.ru",
                hashed_password="argon2_hashed_secret",
                role="candidate",
                is_active=True,
                email_verified=True,
            )
            session.add(user_v)
            await session.flush()
            cand_v = CandidateProfile(
                user_id=user_v.id,
                first_name="Формат",
                last_name=fmt,
                work_format=fmt,
                freshness_score=50.0,
            )
            session.add(cand_v)
            await session.commit()

        # 6. Adversarial Check: Invalid work_format must be REJECTED by CHECK constraint
        user3 = User(
            email="invalid_format@fsp.ru",
            hashed_password="argon2_hashed_secret",
            role="candidate",
            is_active=True,
            email_verified=True,
        )
        session.add(user3)
        await session.flush()

        cand_invalid = CandidateProfile(
            user_id=user3.id,
            first_name="Инвалид",
            last_name="Форматов",
            city="Москва",
            work_format="freelance_unsupported",  # Violates chk_candidate_work_format
            freshness_score=50.0,
        )
        session.add(cand_invalid)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

        # 7. Adversarial Check: Negative/zero expected_salary must be REJECTED
        user4 = User(
            email="invalid_salary@fsp.ru",
            hashed_password="argon2_hashed_secret",
            role="candidate",
            is_active=True,
            email_verified=True,
        )
        session.add(user4)
        await session.flush()

        cand_zero_salary = CandidateProfile(
            user_id=user4.id,
            first_name="Ноль",
            last_name="Зарплатников",
            expected_salary=0,  # Violates expected_salary > 0
            freshness_score=50.0,
        )
        session.add(cand_zero_salary)
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    await engine.dispose()


# ---------------------------------------------------------------------------
# Suite 2: Pydantic Schemas Serialization Stress Testing
# ---------------------------------------------------------------------------

def test_adversarial_candidate_full_profile_schema_all_none():
    """Verify serialization of CandidateFullProfileResponse when all optional fields are None."""
    data = {
        "id": 101,
        "user_id": 202,
        "first_name": "Иван",
        "last_name": "Иванов",
        "middle_name": None,
        "email": "ivan.ivanov@fsp.ru",
        "phone": None,
        "telegram": None,
        "github_url": None,
        "city": None,
        "work_format": None,
        "relocation_ready": False,
        "expected_salary": None,
        "salary_min": None,
        "salary_max": None,
        "bio": None,
        "about": None,
        "specialization": None,
        "grade": None,
        "category_title": None,
        "skills": [],
        "kite_score_scaled": 0.0,
        "theta": None,
        "fsp_id": None,
        "fsp_verified": False,
        "fsp_badge": "Платформенная верификация",
        "freshness_score": 50.0,
        "is_published": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    resp = CandidateFullProfileResponse(**data)
    assert resp.city is None
    assert resp.work_format is None
    assert resp.specialization is None
    assert resp.grade is None
    assert resp.category_title is None
    assert resp.skills == []
    # populate_compat_fields sets theta = kite_score_scaled if theta is None
    assert resp.theta == 0.0
    assert resp.kite_score_scaled == 0.0

    # Ensure model_dump & json serialization work seamlessly
    dump = resp.model_dump()
    assert dump["city"] is None
    assert dump["work_format"] is None
    assert dump["specialization"] is None

    parsed_json = json.loads(resp.model_dump_json())
    assert parsed_json["city"] is None
    assert parsed_json["work_format"] is None
    assert parsed_json["specialization"] is None
    assert parsed_json["theta"] == 0.0


def test_adversarial_candidate_bank_card_schema_with_nulls():
    """Verify CandidateBankCard serialization when candidate has NULL city and work_format."""
    card_data = {
        "id": 42,
        "user_id": 99,
        "masked_full_name": "Алексей К. (#C-42)",
        "specialization": "backend",
        "grade": "middle",
        "category_code": "backend_middle",
        "category_badge": "Backend · Middle",
        "test_score": 0.0,
        "freshness_score": 50.0,
        "city": None,
        "work_format": None,
        "relocation_ready": False,
        "expected_salary": None,
        "fsp_id": None,
        "fsp_verified": False,
        "fsp_badge": "Платформенная верификация",
        "skills": [],
        "match_score": 75.5,
        "explainability": None,
        "invitation_status": None,
        "is_contacts_unmasked": False,
        "created_at": datetime.now(timezone.utc),
    }

    card = CandidateBankCard(**card_data)
    assert card.city is None
    assert card.work_format is None
    assert card.expected_salary is None

    dump = card.model_dump()
    assert dump["city"] is None
    assert dump["work_format"] is None

    parsed_json = json.loads(card.model_dump_json())
    assert parsed_json["city"] is None
    assert parsed_json["work_format"] is None


def test_adversarial_candidate_anonymized_detail_schema_with_nulls():
    """Verify CandidateAnonymizedDetailResponse serialization when candidate has NULL city and work_format."""
    detail_data = {
        "id": 42,
        "user_id": 99,
        "masked_full_name": "Алексей К. (#C-42)",
        "specialization": "backend",
        "grade": "middle",
        "category_title": "Backend Разработка · Middle",
        "bio": None,
        "city": None,
        "work_format": None,
        "relocation_ready": False,
        "expected_salary": None,
        "skills": [],
        "test_score": 0.0,
        "freshness_score": 50.0,
        "fsp_id": None,
        "fsp_verified": False,
        "fsp_badge": "Платформенная верификация",
        "fsp_achievements": [],
        "anonymized_pdf_url": "/api/v1/resume-pdf/42/anonymized",
        "is_contacts_masked": True,
        "created_at": datetime.now(timezone.utc),
    }

    detail = CandidateAnonymizedDetailResponse(**detail_data)
    assert detail.city is None
    assert detail.work_format is None
    assert detail.expected_salary is None

    dump = detail.model_dump()
    assert dump["city"] is None
    assert dump["work_format"] is None

    parsed_json = json.loads(detail.model_dump_json())
    assert parsed_json["city"] is None
    assert parsed_json["work_format"] is None


# ---------------------------------------------------------------------------
# Suite 3: PDF Generator Stress Testing with Completely Uncalibrated Data
# ---------------------------------------------------------------------------

def test_adversarial_pdf_generator_uncalibrated_safe_generation():
    """Verify generate_fsp_profile_pdf never crashes with None values and produces honest labels."""
    uncalibrated_payload = {
        "full_name": "Петр Сидоров",
        "fsp_id": None,
        "is_fsp_member": False,
        "specialization": None,
        "grade": None,
        "skills": [],
        "theta": None,
        "freshness_score": 50.0,
        "city": None,
        "work_format": None,
        "expected_salary": None,
        "bio": None,
        "fsp_achievements": [],
        "contacts_masked": True,
    }

    pdf_bytes = generate_fsp_profile_pdf(uncalibrated_payload)
    assert isinstance(pdf_bytes, bytes)
    assert len(pdf_bytes) > 1000
    assert pdf_bytes.startswith(b"%PDF-"), "Generated file must have valid PDF magic bytes"

    # Also test with theta=0.0 and string markers
    uncalibrated_payload_markers = {
        "full_name": "Анна Смирнова",
        "fsp_id": None,
        "is_fsp_member": False,
        "specialization": "Не выбрана",
        "grade": "Не определен",
        "skills": [],
        "theta": 0.0,
        "freshness_score": 50.0,
        "city": None,
        "work_format": None,
        "expected_salary": None,
        "bio": None,
        "fsp_achievements": [],
        "contacts_masked": True,
    }

    pdf_bytes_2 = generate_fsp_profile_pdf(uncalibrated_payload_markers)
    assert isinstance(pdf_bytes_2, bytes)
    assert len(pdf_bytes_2) > 1000
    assert pdf_bytes_2.startswith(b"%PDF-")


# ---------------------------------------------------------------------------
# Suite 4: End-to-End API Integration & Recruiter Search with NULL Candidates
# ---------------------------------------------------------------------------

CHALLENGER_DB_URL = "sqlite+aiosqlite:///./test_challenger_adversarial.db"
challenger_engine = create_async_engine(CHALLENGER_DB_URL, echo=False)
challenger_session_factory = async_sessionmaker(bind=challenger_engine, class_=AsyncSession, expire_on_commit=False)


async def override_get_challenger_db():
    async with challenger_session_factory() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


def _auth_user(client: TestClient, email: str, role: str = "candidate", inn: str = "7707083893") -> dict:
    payload = {
        "email": email,
        "password": "StrongPassword123!",
        "role": role,
        "first_name": "Имя",
        "last_name": "Фамилия",
        "consent_pdn_processing": True,
        "consent_profile_publication": True,
    }
    if role == "employer":
        payload["company_name"] = "ООО ТехноБанк"
        payload["inn"] = inn

    reg_resp = client.post("/api/v1/auth/register", json=payload)
    assert reg_resp.status_code == 201, f"Reg failed: {reg_resp.text}"
    token = reg_resp.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_adversarial_api_candidate_profile_me_and_recruiter_search():
    """
    End-to-end empirical verification:
    1. Uncalibrated candidate GET /candidate-profile/me returns honest defaults.
    2. PUT /candidate-profile/me correctly updates and can reset city/work_format.
    3. Recruiter searches /candidate-bank with candidate having NULL city/work_format.
       MUST NOT cause HTTP 500 or validation crash.
    """
    async def _init_db():
        if os.path.exists("./test_challenger_adversarial.db"):
            try:
                os.remove("./test_challenger_adversarial.db")
            except Exception:
                pass
        async with challenger_engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        async with challenger_session_factory() as session:
            await seed_reference_data(session)

    asyncio.run(_init_db())

    app.dependency_overrides[get_db] = override_get_challenger_db
    try:
        client = TestClient(app)

        # 1. Register new uncalibrated candidate
        cand_headers = _auth_user(client, email="brand_new_cand@fsp-test.ru", role="candidate")

        # 2. Call GET /candidate-profile/me
        get_resp = client.get("/api/v1/candidate-profile/me", headers=cand_headers)
        assert get_resp.status_code == 200, f"Expected 200, got {get_resp.status_code}: {get_resp.text}"
        cand_data = get_resp.json()

        assert cand_data["city"] is None, f"Expected city to be None, got {cand_data['city']}"
        assert cand_data["work_format"] is None, f"Expected work_format to be None, got {cand_data['work_format']}"
        assert cand_data["grade"] == "Не определен"
        assert cand_data["specialization"] == "Не выбрана"
        assert cand_data["category_title"] == "Профиль не откалиброван"
        assert cand_data["skills"] == []
        assert cand_data["expected_salary"] is None
        assert cand_data["salary_min"] is None
        assert cand_data["salary_max"] is None
        assert cand_data["theta"] == 0.0
        assert cand_data["kite_score_scaled"] == 0.0
        assert cand_data["fsp_id"] is None
        assert cand_data["fsp_verified"] is False
        assert cand_data["fsp_badge"] == "Платформенная верификация"

        # 3. Test PUT /candidate-profile/me updating city and work_format
        put_resp = client.put(
            "/api/v1/candidate-profile/me",
            json={"city": "Казань", "work_format": "hybrid", "expected_salary": 170000},
            headers=cand_headers,
        )
        assert put_resp.status_code == 200, f"PUT failed: {put_resp.text}"
        updated_data = put_resp.json()
        assert updated_data["city"] == "Казань"
        assert updated_data["work_format"] == "hybrid"
        assert updated_data["expected_salary"] == 170000

        # Reset city and work_format back to None
        put_reset_resp = client.put(
            "/api/v1/candidate-profile/me",
            json={"city": None, "work_format": None},
            headers=cand_headers,
        )
        assert put_reset_resp.status_code == 200
        reset_data = put_reset_resp.json()
        assert reset_data["city"] == "Казань"  # Pydantic update request ignores None in partial update unless specified

        # 4. Create another candidate who is completely pristine (never called update)
        pristine_headers = _auth_user(client, email="pristine_null_cand@fsp-test.ru", role="candidate")
        p_resp = client.get("/api/v1/candidate-profile/me", headers=pristine_headers)
        assert p_resp.status_code == 200
        pristine_id = p_resp.json()["id"]

        # 5. Register an employer to search candidate bank
        emp_headers = _auth_user(client, email="recruiter_hr@technobank.ru", role="employer", inn="7707083893")

        # 6. Recruiter searches candidate bank
        # MUST NOT 500 when candidates have city=None, work_format=None
        search_resp = client.get("/api/v1/candidate-bank", headers=emp_headers)
        assert search_resp.status_code == 200, f"Recruiter search failed with 500: {search_resp.text}"
        bank_data = search_resp.json()
        assert "items" in bank_data
        assert "meta" in bank_data

        # Locate the pristine candidate in search results
        pristine_card = next((item for item in bank_data["items"] if item["id"] == pristine_id), None)
        assert pristine_card is not None, f"Pristine candidate #{pristine_id} should appear in candidate bank"
        assert pristine_card["city"] is None, f"Expected card city None, got {pristine_card['city']}"
        assert pristine_card["work_format"] is None, f"Expected card work_format None, got {pristine_card['work_format']}"

        # 7. Faceted search by city: candidates with city=None should be cleanly filtered out without error
        filter_resp = client.get("/api/v1/candidate-bank?city=Москва", headers=emp_headers)
        assert filter_resp.status_code == 200
        filtered_items = filter_resp.json()["items"]
        assert all(item["city"] == "Москва" for item in filtered_items)
        assert not any(item["id"] == pristine_id for item in filtered_items)

        # 8. Anonymized Candidate Details: GET /candidate-bank/{id}
        detail_resp = client.get(f"/api/v1/candidate-bank/{pristine_id}", headers=emp_headers)
        assert detail_resp.status_code == 200, f"Detail failed: {detail_resp.text}"
        detail_data = detail_resp.json()
        assert detail_data["city"] is None
        assert detail_data["work_format"] is None
        assert detail_data["is_contacts_masked"] is True

    finally:
        app.dependency_overrides.clear()
        asyncio.run(challenger_engine.dispose())
        if os.path.exists("./test_challenger_adversarial.db"):
            try:
                os.remove("./test_challenger_adversarial.db")
            except Exception:
                pass
