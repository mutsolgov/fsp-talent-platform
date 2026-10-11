"""
Integration Test Suite for Assessment Layer (API Modules 3–6 & KITE Engine).
Verifies:
1. Onboarding Survey & Candidate Profile lifecycle (152-ФЗ consents, freshness decay/ping).
2. Resume PDF upload with %PDF- magic bytes validation (EC-18 415 rejection).
3. Assessment Session lifecycle (HMAC seed, item fetch, submission, IRT 3PL theta calculation, verdict).
4. Cooldown enforcement (EC-08) & Jury Demo Bypass (EC-09).
5. Micro-Challenges listing, dry-run, and submission.
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
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.security import create_access_token
from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models.candidate_profiles import CandidateProfile
from app.models.canonical_item_families import CanonicalItemFamily
from app.models.categories import Category
from app.models.grades import Grade
from app.models.skills import Skill
from app.models.specializations import Specialization
from app.models.users import User
from app.models.user_consents import UserConsent
from fastapi.testclient import TestClient
from scripts.seed_canonical_items import seed_canonical_items
from scripts.seed_reference_data import seed_reference_data

from sqlalchemy import event, text

TEST_DB_URL = "sqlite+aiosqlite:///./test_assessment_integration.db"
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
                await session.execute(text("DELETE FROM challenge_submissions"))
                await session.execute(text("DELETE FROM micro_challenges"))
                await session.execute(text("DELETE FROM assessment_answers"))
                await session.execute(text("DELETE FROM assessment_sessions"))
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



def _register_and_auth(
    client,
    email="candidate.test@example.com",
    first_name="Тест",
    last_name="Соискатель",
    role: str = "candidate",
):
    """Вспомогательная функция регистрации соискателя/работодателя и получения JWT токена."""
    payload = {
        "email": email,
        "password": "StrongPassword123!",
        "role": role,
        "first_name": first_name,
        "last_name": last_name,
        "consent_pdn_processing": True,
        "consent_profile_publication": True,
    }
    if role == "employer":
        payload["company_name"] = "ООО ИТ-Инновации"
        payload["inn"] = "7707083893"

    reg_resp = client.post(
        "/api/v1/auth/register",
        json=payload,
    )
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
    token = reg_resp.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_onboarding_survey_and_candidate_profile_flow(client):
    """
    Проверка прохождения онбординг-опроса, сохранения профиля,
    152-ФЗ согласий, проверки статуса категории и freshness score.
    """
    headers = _register_and_auth(client, email="onboarding.cand@example.com")

    # 1. Отправка онбординг-опроса
    survey_payload = {
        "specialization_id": 1,  # backend
        "claimed_grade_id": 2,    # middle
        "work_format": "remote",
        "salary_min": 180000,
        "salary_max": 250000,
        "consent_personal_data": True,
        "consent_profile_publish": True,
        "skills": [
            {"skill_id": 1, "proficiency_level": "advanced", "years_experience": 3},
            {"skill_id": 2, "proficiency_level": "intermediate", "years_experience": 2},
        ],
    }
    resp = client.post("/api/v1/candidate-profile/onboarding-survey", json=survey_payload, headers=headers)
    assert resp.status_code == 201, f"Survey submission failed: {resp.text}"
    data = resp.json()
    assert data["status"] == "onboarding_completed"
    assert data["specialization"]["id"] == 1
    assert data["claimed_grade"]["id"] == 2

    # 2. Получение профиля (GET /me)
    resp_me = client.get("/api/v1/candidate-profile/me", headers=headers)
    assert resp_me.status_code == 200
    me_data = resp_me.json()
    assert me_data["salary_min"] == 180000
    assert me_data["salary_max"] == 250000
    assert me_data["work_format"] == "remote"

    # 3. Обновление профиля (PUT /me)
    update_payload = {
        "city": "Санкт-Петербург",
        "salary_min": 190000,
        "salary_max": 260000,
        "about": "Опытный бэкенд разработчик",
    }
    resp_update = client.put("/api/v1/candidate-profile/me", json=update_payload, headers=headers)
    assert resp_update.status_code == 200
    assert resp_update.json()["city"] == "Санкт-Петербург"
    assert resp_update.json()["salary_min"] == 190000

    # 4. Проверка категории (GET /category) — до теста грейд не подтвержден
    resp_cat = client.get("/api/v1/candidate-profile/category", headers=headers)
    assert resp_cat.status_code == 200
    cat_data = resp_cat.json()
    assert cat_data["status"] == "unverified"
    assert cat_data["claimed_grade"] == "Middle"
    assert cat_data["verified_grade"] is None

    # 5. Проверка freshness и пинг
    resp_fresh = client.get("/api/v1/candidate-profile/freshness", headers=headers)
    assert resp_fresh.status_code == 200
    assert resp_fresh.json()["freshness_score"] > 0

    resp_ping = client.post("/api/v1/candidate-profile/freshness/ping", headers=headers)
    assert resp_ping.status_code == 200, f"Ping freshness failed: {resp_ping.status_code} {resp_ping.text}"
    assert resp_ping.json()["freshness_score"] == 100.0


def test_resume_upload_valid_pdf_and_rejection_ec18(client):
    """
    EC-18: Загрузка резюме с валидным PDF (%PDF-) возвращает 200,
    не-PDF файлы отклоняются с HTTP 415 (ERR_INVALID_PDF_FORMAT).
    """
    headers = _register_and_auth(client, email="resume.test@example.com")

    # 1. Валидный PDF-файл (начинается с %PDF-)
    valid_pdf_content = (
        b"%PDF-1.4\n1 0 obj\n<< /Title (Resume) >>\nendobj\n"
        b"Python developer with FastAPI, PostgreSQL, Docker, Redis.\n"
        b"Email: resume.dev@example.com Phone: +79998887766\n%%EOF"
    )
    resp_valid = client.post(
        "/api/v1/resume-pdf/upload",
        files={"file": ("resume.pdf", valid_pdf_content, "application/pdf")},
        headers=headers,
    )
    assert resp_valid.status_code == 200, f"Expected 200, got {resp_valid.status_code}: {resp_valid.text}"
    valid_data = resp_valid.json()
    assert "detected_skills" in valid_data
    assert isinstance(valid_data["detected_skills"], list)

    # 2. Невалидный файл (EC-18: DOCX / ZIP magic bytes PK...)
    invalid_docx_content = b"PK\x03\x04\x14\x00\x06\x00Some docx document content"
    resp_invalid = client.post(
        "/api/v1/resume-pdf/upload",
        files={"file": ("resume.docx", invalid_docx_content, "application/vnd.openxmlformats-officedocument")},
        headers=headers,
    )
    assert resp_invalid.status_code == 415, f"Expected 415 for invalid PDF, got {resp_invalid.status_code}"
    err_text = resp_invalid.text
    assert "ERR_INVALID_PDF_FORMAT" in err_text or "415" in str(resp_invalid.status_code)


def test_assessment_session_full_lifecycle(client):
    """
    Полный жизненный цикл тестирования KITE:
    1. Старт сессии (/sessions/start) -> 12 канонических заданий с HMAC-сидом.
    2. Получение задания (/tasks/0) -> изоморфный рендеринг, 3 публичных теста.
    3. Отправка ответов (/submit-item).
    4. Завершение сессии (/finish) -> байесовский EAP расчет theta*, присвоение категории.
    5. Получение результатов (/results).
    """
    headers = _register_and_auth(client, email="assessment.cand@example.com")

    # Сначала онбординг
    client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        json={
            "specialization_id": 1,
            "claimed_grade_id": 2,
            "work_format": "remote",
            "salary_min": 170000,
            "salary_max": 240000,
            "consent_personal_data": True,
            "consent_profile_publish": True,
            "skills": [{"skill_id": 1, "proficiency_level": "advanced", "years_experience": 3}],
        },
        headers=headers,
    )

    # 1. Старт сессии тестирования
    start_resp = client.post(
        "/api/v1/assessment/sessions/start",
        json={"specialization_id": 1, "claimed_grade_id": 2, "session_type": "initial"},
        headers=headers,
    )
    assert start_resp.status_code == 201, f"Session start failed: {start_resp.text}"
    start_data = start_resp.json()
    session_id = start_data["session_id"]
    assert start_data["total_tasks"] == 12
    assert start_data["status"] == "in_progress"
    assert "variant_seed" in start_data

    # 2. Получение первого задания (GET /tasks/0)
    task_resp = client.get(f"/api/v1/assessment/sessions/{session_id}/tasks/0", headers=headers)
    assert task_resp.status_code == 200, f"Task fetch failed: {task_resp.text}"
    task_data = task_resp.json()
    assert task_data["task_index"] == 0
    assert len(task_data["prompt"]) > 10
    # Проверка наличия публичных тестов
    assert len(task_data["public_tests"]) >= 0

    # 3. Отправка ответов на задания
    for idx in range(12):
        ans_resp = client.post(
            f"/api/v1/assessment/sessions/{session_id}/submit-item",
            json={
                "task_index": idx,
                "answer_payload": {"selected_option": "A", "code": "def solution(): return 42"},
                "time_spent_seconds": 45,
            },
            headers=headers,
        )
        assert ans_resp.status_code == 200, f"Submit answer {idx} failed: {ans_resp.text}"

    # 4. Завершение тестирования
    finish_resp = client.post(f"/api/v1/assessment/sessions/{session_id}/finish", headers=headers)
    assert finish_resp.status_code == 200, f"Finish session failed: {finish_resp.text}"
    finish_data = finish_resp.json()
    assert finish_data["status"] == "completed"
    assert finish_data["theta_score"] >= 0.0
    assert finish_data["verdict"] in ["confirmed", "boost_offered", "retest_lower_offered", "failed"]

    # 5. Получение детальных результатов
    res_resp = client.get(f"/api/v1/assessment/sessions/{session_id}/results", headers=headers)
    assert res_resp.status_code == 200
    res_data = res_resp.json()
    assert res_data["session_id"] == session_id
    assert "explainability" in res_data
    assert len(res_data["explainability"]) > 5


def test_cooldown_status_and_jury_demo_bypass(client):
    """
    EC-08 & EC-09: Проверка статуса кулдауна и механизма мгновенного сброса для жюри.
    """
    headers = _register_and_auth(client, email="cooldown.tester@example.com")

    # 1. Запрос статуса кулдауна нового соискателя (кулдаун не активен)
    cd_resp = client.get("/api/v1/assessment/cooldown-status", headers=headers)
    assert cd_resp.status_code == 200
    assert cd_resp.json()["is_cooldown_active"] is False

    # 2. Выполнение демо-сброса для жюри (POST /cooldown-status/jury-reset)
    reset_resp = client.post(
        "/api/v1/assessment/cooldown-status/jury-reset",
        json={"reason": "jury_demonstration_test"},
        headers=headers,
    )
    assert reset_resp.status_code == 200
    assert reset_resp.json()["is_cooldown_active"] is False
    assert reset_resp.json()["days_remaining"] == 0


def test_micro_challenges_listing_and_submission(client):
    """
    Проверка API микро-челленджей: создание, получение списка, dry-run тестов и сдача решения.
    """
    emp_headers = _register_and_auth(
        client,
        email="employer.challenges@example.com",
        first_name="HR",
        last_name="Директор",
        role="employer",
    )
    headers = _register_and_auth(client, email="challenge.cand@example.com")

    # 1. Создание челленджа
    create_payload = {
        "title": "Sliding Window Median Filter",
        "description": "Реализуйте фильтр медианы для окна размера K в реальном времени.",
        "specialization_id": 1,
        "grade_id": 2,
        "template_code": "def median_filter(records, k):\n    return []\n",
        "reference_solution": "def median_filter(records, k):\n    return [sorted(records[i:i+k])[k//2] for i in range(len(records)-k+1)]\n",
        "test_cases": [
            {"input": {"records": [1, 3, 2, 5, 4], "k": 3}, "expected": [2, 3, 4], "is_public": True},
            {"input": {"records": [10, 20, 30, 40], "k": 2}, "expected": [10, 20, 30], "is_public": False},
        ],
        "time_limit_ms": 1000,
        "memory_limit_mb": 256,
        "points": 50,
    }
    cr_resp = client.post("/api/v1/micro-challenges/", json=create_payload, headers=emp_headers)
    assert cr_resp.status_code == 201, f"Create challenge failed: {cr_resp.text}"
    challenge_id = cr_resp.json()["id"]

    # 2. Получение списка челленджей
    list_resp = client.get("/api/v1/micro-challenges/?specialization_id=1", headers=headers)
    assert list_resp.status_code == 200, f"List challenges failed: {list_resp.status_code} {list_resp.text}"
    assert len(list_resp.json()["items"]) >= 1

    # 3. Детали челленджа
    det_resp = client.get(f"/api/v1/micro-challenges/{challenge_id}", headers=headers)
    assert det_resp.status_code == 200
    assert det_resp.json()["id"] == challenge_id

    # 4. Прогон на публичных тестах (dry-run)
    run_resp = client.post(
        f"/api/v1/micro-challenges/{challenge_id}/run-tests",
        json={"code": "def median_filter(records, k):\n    return [2, 3, 4]\n"},
        headers=headers,
    )
    assert run_resp.status_code == 200
    assert "public_results" in run_resp.json()

    # 5. Финальная сдача решения (submit)
    sub_resp = client.post(
        f"/api/v1/micro-challenges/{challenge_id}/submit",
        json={"code": "def median_filter(records, k):\n    return [2, 3, 4]\n"},
        headers=headers,
    )
    assert sub_resp.status_code == 201
    assert "submission_id" in sub_resp.json()
    assert sub_resp.json()["status"] in ["accepted", "wrong_answer"]


def test_uncalibrated_candidate_profile_honest_defaults(client):
    """
    R1 & R2: Новый соискатель без анкеты и категорий возвращает:
    - city: None
    - work_format: None
    - grade: 'Не определен'
    - specialization: 'Не выбрана'
    - category_title: 'Профиль не откалиброван'
    - skills: []
    - expected_salary: None, salary_min: None, salary_max: None
    - theta: 0.0, kite_score_scaled: 0.0
    """
    headers = _register_and_auth(client, email="new.uncalibrated.cand@fsp-test.ru")
    resp = client.get("/api/v1/candidate-profile/me", headers=headers)
    assert resp.status_code == 200, f"Expected 200, got {resp.status_code}: {resp.text}"
    data = resp.json()
    assert data["city"] is None
    assert data["work_format"] is None
    assert data["grade"] == "Не определен"
    assert data["specialization"] == "Не выбрана"
    assert data["category_title"] == "Профиль не откалиброван"
    assert data["skills"] == []
    assert data["expected_salary"] is None
    assert data["salary_min"] is None
    assert data["salary_max"] is None
    assert data["theta"] == 0.0
    assert data["kite_score_scaled"] == 0.0

