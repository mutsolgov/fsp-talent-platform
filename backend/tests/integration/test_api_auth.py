"""
Integration Test Suite for API Module 1: auth & 152-ФЗ compliance.
Verifies all 9 endpoints, 152-ФЗ consent enforcement, INN checksums, JWT lifecycle, and reference data.
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
from sqlalchemy import select

from app.core.config import settings
from app.core.security import create_access_token
from app.database import get_db
from app.main import app
from app.models.base import Base
from app.models.categories import Category
from app.models.grades import Grade
from app.models.skills import Skill
from app.models.specializations import Specialization
from app.models.users import User
from app.models.user_consents import UserConsent
from app.models.audit_logs import AuditLog
from app.models.candidate_profiles import CandidateProfile
from scripts.seed_reference_data import seed_reference_data
from fastapi.testclient import TestClient

# Dedicated test engine (isolated file or shared in-memory for testing)
from sqlalchemy import event, text

TEST_DB_URL = "sqlite+aiosqlite:///./test_auth_integration.db"
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
                await session.execute(text("DELETE FROM audit_logs"))
                await session.execute(text("DELETE FROM user_consents"))
                await session.execute(text("DELETE FROM users"))
                await session.commit()

    asyncio.run(_setup())

    # Override database dependency in FastAPI app
    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.clear()
        asyncio.run(test_engine.dispose())



def test_reference_data_seeding(client):
    """Проверка корректности сидирования справочников (24 категории, 6 специализаций, 4 грейда, 350+ навыков)."""
    async def _check():
        async with test_session_factory() as session:
            specs = (await session.execute(select(Specialization))).scalars().all()
            grades = (await session.execute(select(Grade))).scalars().all()
            cats = (await session.execute(select(Category))).scalars().all()
            skills = (await session.execute(select(Skill))).scalars().all()

            assert len(specs) == 6, f"Ожидалось 6 специализаций, получено {len(specs)}"
            assert len(grades) == 4, f"Ожидалось 4 грейда, получено {len(grades)}"
            assert len(cats) == 24, f"Ожидалось 24 категории (6x4), получено {len(cats)}"
            assert len(skills) >= 350, f"Ожидалось >= 350 навыков, получено {len(skills)}"

    asyncio.run(_check())


def test_candidate_registration_success(client):
    """Успешная регистрация соискателя с фиксацией 152-ФЗ согласий и выдачей JWT токенов."""
    payload = {
        "email": "ivan.petrov@example.com",
        "password": "StrongPassword2026!",
        "role": "candidate",
        "first_name": "Иван",
        "last_name": "Петров",
        "consent_pdn_processing": True,
        "consent_profile_publication": True,
        "policy_version": "v1.0-2026",
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"

    data = response.json()
    assert data["email"] == "ivan.petrov@example.com"
    assert data["role"] == "candidate"
    assert data["is_email_verified"] is False
    assert "tokens" in data
    assert "access_token" in data["tokens"]
    assert "refresh_token" in data["tokens"]
    assert data["tokens"]["token_type"] == "bearer"

    # Проверка сохранения в базе данных
    async def _verify_db():
        async with test_session_factory() as session:
            res_user = await session.execute(select(User).where(User.email == "ivan.petrov@example.com"))
            user = res_user.scalar_one_or_none()
            assert user is not None
            assert user.role == "candidate"

            res_consent = await session.execute(select(UserConsent).where(UserConsent.user_id == user.id))
            consent = res_consent.scalar_one_or_none()
            assert consent is not None
            assert consent.consent_pdn_processing is True
            assert consent.consent_profile_publication is True
            assert consent.policy_version == "v1.0-2026"

            res_audit = await session.execute(select(AuditLog).where(AuditLog.user_id == user.id))
            audit = res_audit.scalar_one_or_none()
            assert audit is not None
            assert audit.action == "USER_REGISTER"

    asyncio.run(_verify_db())


def test_registration_mandatory_pdn_consent_rejection(client):
    """Попытка регистрации без обязательного согласия на обработку ПДн (ст. 9 152-ФЗ) отклоняется с кодом 422."""
    payload = {
        "email": "no.consent@example.com",
        "password": "Password12345",
        "role": "candidate",
        "first_name": "Алексей",
        "last_name": "Сидоров",
        "consent_pdn_processing": False,  # Нарушение 152-ФЗ
        "consent_profile_publication": True,
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"


def test_employer_registration_valid_inn(client):
    """Успешная регистрация работодателя с валидным 10-значным ИНН (контрольная сумма ФНС РФ)."""
    # 7707083893 — валидный 10-значный ИНН ПАО Сбербанк
    payload = {
        "email": "hr@sberbank.corp",
        "password": "CorporatePassword2026!",
        "role": "employer",
        "company_name": "ПАО Сбербанк",
        "inn": "7707083893",
        "consent_pdn_processing": True,
        "consent_profile_publication": True,
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
    data = response.json()
    assert data["role"] == "employer"
    assert data["email"] == "hr@sberbank.corp"


def test_employer_registration_invalid_inn_checksum(client):
    """Попытка регистрации работодателя с невалидной контрольной суммой ИНН отклоняется с кодом 422."""
    payload = {
        "email": "hr@fraud.corp",
        "password": "CorporatePassword2026!",
        "role": "employer",
        "company_name": "ООО Однодневка",
        "inn": "7707083890",  # Неверная контрольная цифра (должна быть 3)
        "consent_pdn_processing": True,
        "consent_profile_publication": True,
    }
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"


def test_registration_duplicate_email_conflict(client):
    """Повторная регистрация с уже существующим email отклоняется со статусом 409 Conflict."""
    payload = {
        "email": "duplicate@example.com",
        "password": "Password12345",
        "role": "candidate",
        "first_name": "Тест",
        "last_name": "Тестов",
        "consent_pdn_processing": True,
        "consent_profile_publication": True,
    }
    r1 = client.post("/api/v1/auth/register", json=payload)
    assert r1.status_code == 201

    r2 = client.post("/api/v1/auth/register", json=payload)
    assert r2.status_code == 409, f"Expected 409, got {r2.status_code}"


def test_login_and_token_generation(client):
    """Аутентификация с корректными и некорректными учетными данными."""
    reg_payload = {
        "email": "login.test@example.com",
        "password": "SecretPassword123!",
        "role": "candidate",
        "first_name": "Анна",
        "last_name": "Смирнова",
        "consent_pdn_processing": True,
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    # 1. Корректный логин
    login_res = client.post(
        "/api/v1/auth/login",
        json={"email": "login.test@example.com", "password": "SecretPassword123!"},
    )
    assert login_res.status_code == 200
    token_data = login_res.json()
    assert "access_token" in token_data
    assert "refresh_token" in token_data
    assert token_data["token_type"] == "bearer"

    # 2. Неверный пароль -> 401
    bad_login = client.post(
        "/api/v1/auth/login",
        json={"email": "login.test@example.com", "password": "WrongPassword!"},
    )
    assert bad_login.status_code == 401


def test_token_refresh(client):
    """Ротация JWT токенов по валидному Refresh токену."""
    reg_payload = {
        "email": "refresh.test@example.com",
        "password": "Password12345",
        "role": "candidate",
        "first_name": "Ольга",
        "last_name": "Кузнецова",
        "consent_pdn_processing": True,
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    refresh_token = reg_res.json()["tokens"]["refresh_token"]

    # Ротация токена
    ref_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_res.status_code == 200
    ref_data = ref_res.json()
    assert "access_token" in ref_data
    assert "refresh_token" in ref_data

    # Невалидный refresh token -> 401
    bad_ref = client.post("/api/v1/auth/refresh", json={"refresh_token": "invalid.jwt.token"})
    assert bad_ref.status_code == 401


def test_get_me_profile(client):
    """Получение профиля текущего пользователя и проверка валидности Bearer токена."""
    reg_payload = {
        "email": "me.profile@example.com",
        "password": "Password12345",
        "role": "candidate",
        "first_name": "Дмитрий",
        "last_name": "Морозов",
        "consent_pdn_processing": True,
        "consent_profile_publication": True,
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["tokens"]["access_token"]

    # Запрос с токеном
    res = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    profile = res.json()
    assert profile["email"] == "me.profile@example.com"
    assert profile["role"] == "candidate"
    assert profile["consent_pdn_processing"] is True
    assert profile["consent_profile_publication"] is True

    # Запрос без токена -> 401
    res_unauth = client.get("/api/v1/auth/me")
    assert res_unauth.status_code == 401


def test_change_password(client):
    """Безопасная смена пароля и последующий вход с новым паролем."""
    reg_payload = {
        "email": "pwd.change@example.com",
        "password": "OldPassword123!",
        "role": "candidate",
        "first_name": "Павел",
        "last_name": "Васильев",
        "consent_pdn_processing": True,
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["tokens"]["access_token"]

    # 1. Попытка смены на тот же пароль -> 422
    same_pwd_res = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"old_password": "OldPassword123!", "new_password": "OldPassword123!"},
    )
    assert same_pwd_res.status_code == 422

    # 2. Неверный старый пароль -> 400
    wrong_old_res = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"old_password": "IncorrectPassword!", "new_password": "BrandNewPassword2026!"},
    )
    assert wrong_old_res.status_code == 400

    # 3. Успешная смена пароля -> 200
    change_res = client.post(
        "/api/v1/auth/change-password",
        headers={"Authorization": f"Bearer {token}"},
        json={"old_password": "OldPassword123!", "new_password": "BrandNewPassword2026!"},
    )
    assert change_res.status_code == 200

    # 4. Вход со старым паролем отклоняется -> 401
    fail_login = client.post(
        "/api/v1/auth/login",
        json={"email": "pwd.change@example.com", "password": "OldPassword123!"},
    )
    assert fail_login.status_code == 401

    # 5. Вход с новым паролем успешен -> 200
    ok_login = client.post(
        "/api/v1/auth/login",
        json={"email": "pwd.change@example.com", "password": "BrandNewPassword2026!"},
    )
    assert ok_login.status_code == 200


def test_verify_email(client):
    """Подтверждение email через одноразовый криптографический токен."""
    reg_payload = {
        "email": "verify.email@example.com",
        "password": "Password12345",
        "role": "candidate",
        "first_name": "Елена",
        "last_name": "Зайцева",
        "consent_pdn_processing": True,
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    user_id = reg_res.json()["user_id"]

    verify_token = create_access_token({"sub": str(user_id), "purpose": "email_verification"})

    # Подтверждение email
    ver_res = client.post("/api/v1/auth/verify-email", json={"token": verify_token})
    assert ver_res.status_code == 200

    # Повторное подтверждение -> 409
    dup_ver_res = client.post("/api/v1/auth/verify-email", json={"token": verify_token})
    assert dup_ver_res.status_code == 409


def test_consents_management(client):
    """Просмотр и обновление согласий 152-ФЗ со штампом времени."""
    reg_payload = {
        "email": "consent.mgmt@example.com",
        "password": "Password12345",
        "role": "candidate",
        "first_name": "Сергей",
        "last_name": "Ковалев",
        "consent_pdn_processing": True,
        "consent_profile_publication": True,
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["tokens"]["access_token"]

    # 1. GET /consents
    get_res = client.get("/api/v1/auth/consents", headers={"Authorization": f"Bearer {token}"})
    assert get_res.status_code == 200
    c_data = get_res.json()
    assert c_data["consent_pdn_processing"] is True
    assert c_data["consent_profile_publication"] is True
    assert c_data["revoked_at"] is None

    # 2. PUT /consents (отзыв публикации)
    put_res = client.put(
        "/api/v1/auth/consents",
        headers={"Authorization": f"Bearer {token}"},
        json={"consent_profile_publication": False},
    )
    assert put_res.status_code == 200
    updated_data = put_res.json()
    assert updated_data["consent_profile_publication"] is False
    assert updated_data["revoked_at"] is not None


def test_logout(client):
    """Выход из системы с логированием действия в журнале аудита."""
    reg_payload = {
        "email": "logout.test@example.com",
        "password": "Password12345",
        "role": "candidate",
        "first_name": "Мария",
        "last_name": "Федорова",
        "consent_pdn_processing": True,
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["tokens"]["access_token"]

    res = client.post("/api/v1/auth/logout", headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_consents_upsert_when_not_exists(client):
    """UPSERT для PUT /auth/consents: если запись в user_consents отсутствует, создается новая."""
    reg_payload = {
        "email": "upsert.consent@example.com",
        "password": "Password12345",
        "role": "candidate",
        "first_name": "Игорь",
        "last_name": "Николаев",
        "consent_pdn_processing": True,
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    user_id = reg_res.json()["user_id"]
    token = reg_res.json()["tokens"]["access_token"]

    # Удаляем запись согласия из БД, симулируя ее отсутствие
    async def _delete_consent():
        async with test_session_factory() as session:
            await session.execute(text("DELETE FROM user_consents WHERE user_id = :uid"), {"uid": user_id})
            await session.commit()

    asyncio.run(_delete_consent())

    # PUT /consents должен создать запись (UPSERT), а не вернуть 404
    put_res = client.put(
        "/api/v1/auth/consents",
        headers={"Authorization": f"Bearer {token}"},
        json={"consent_profile_publication": True, "consent_pdn_processing": True},
    )
    assert put_res.status_code == 200, f"Expected 200, got {put_res.status_code}: {put_res.text}"
    data = put_res.json()
    assert data["user_id"] == user_id
    assert data["consent_pdn_processing"] is True
    assert data["consent_profile_publication"] is True
    assert data["revoked_at"] is None

    # Проверяем, что запись действительно появилась в БД и зафиксирован аудит
    async def _verify():
        async with test_session_factory() as session:
            res = await session.execute(select(UserConsent).where(UserConsent.user_id == user_id))
            consent = res.scalar_one_or_none()
            assert consent is not None
            assert consent.consent_pdn_processing is True
            assert consent.consent_profile_publication is True

            res_audit = await session.execute(
                select(AuditLog).where(AuditLog.user_id == user_id, AuditLog.action == "UPDATE_CONSENT")
            )
            audit = res_audit.scalar_one_or_none()
            assert audit is not None

    asyncio.run(_verify())

    # Также проверяем обновление только одного поля
    put_res2 = client.put(
        "/api/v1/auth/consents",
        headers={"Authorization": f"Bearer {token}"},
        json={"consent_profile_publication": False},
    )
    assert put_res2.status_code == 200
    data2 = put_res2.json()
    assert data2["consent_profile_publication"] is False
    assert data2["revoked_at"] is not None


def test_consents_revoke(client):
    """POST /auth/consents/revoke (ст. 21 152-ФЗ РФ): фиксирует отзыв согласий, скрывает профиль, логирует REVOKE_CONSENT."""
    reg_payload = {
        "email": "revoke.consent@example.com",
        "password": "Password12345",
        "role": "candidate",
        "first_name": "Ольга",
        "last_name": "Соколова",
        "consent_pdn_processing": True,
        "consent_profile_publication": True,
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    user_id = reg_res.json()["user_id"]
    token = reg_res.json()["tokens"]["access_token"]

    # Создаем CandidateProfile с is_published=True
    async def _create_profile():
        async with test_session_factory() as session:
            profile = CandidateProfile(
                user_id=user_id,
                first_name="Ольга",
                last_name="Соколова",
                city="Москва",
                work_format="remote",
                is_published=True,
            )
            session.add(profile)
            await session.commit()

    asyncio.run(_create_profile())

    # Отзыв согласий
    revoke_res = client.post("/api/v1/auth/consents/revoke", headers={"Authorization": f"Bearer {token}"})
    assert revoke_res.status_code == 200, f"Expected 200, got {revoke_res.status_code}: {revoke_res.text}"
    data = revoke_res.json()
    assert data["consent_pdn_processing"] is False
    assert data["consent_profile_publication"] is False
    assert data["revoked_at"] is not None

    # Проверяем в БД: профиль скрыт (is_published=False) и действие залогировано
    async def _verify_revoke():
        async with test_session_factory() as session:
            res_prof = await session.execute(select(CandidateProfile).where(CandidateProfile.user_id == user_id))
            prof = res_prof.scalar_one_or_none()
            assert prof is not None
            assert prof.is_published is False

            res_audit = await session.execute(
                select(AuditLog).where(AuditLog.user_id == user_id, AuditLog.action == "REVOKE_CONSENT")
            )
            audit = res_audit.scalar_one_or_none()
            assert audit is not None

    asyncio.run(_verify_revoke())


def test_export_archive(client):
    """GET /auth/export-archive (ст. 14 152-ФЗ РФ): выгрузка персональных данных в виде машиночитаемого архива."""
    reg_payload = {
        "email": "export.archive@example.com",
        "password": "Password12345",
        "role": "candidate",
        "first_name": "Дмитрий",
        "last_name": "Кузнецов",
        "consent_pdn_processing": True,
        "consent_profile_publication": True,
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["tokens"]["access_token"]
    user_id = reg_res.json()["user_id"]

    # Создаем CandidateProfile
    async def _create_profile():
        async with test_session_factory() as session:
            profile = CandidateProfile(
                user_id=user_id,
                first_name="Дмитрий",
                last_name="Кузнецов",
                city="Санкт-Петербург",
                work_format="remote",
                is_published=True,
            )
            session.add(profile)
            await session.commit()

    asyncio.run(_create_profile())

    export_res = client.get("/api/v1/auth/export-archive", headers={"Authorization": f"Bearer {token}"})
    assert export_res.status_code == 200
    assert 'attachment; filename="fsp_user_archive_152fz.json"' in export_res.headers.get("content-disposition", "")
    assert "application/json" in export_res.headers.get("content-type", "")

    data = export_res.json()
    assert "metadata" in data
    assert "Статья 14" in data["metadata"]["legal_basis"]
    assert "user" in data
    assert data["user"]["email"] == "export.archive@example.com"
    assert "consents" in data
    assert "profile" in data
    assert data["profile"]["first_name"] == "Дмитрий"
    assert "skills" in data
    assert "assessment_sessions" in data
    assert "applications" in data
    assert "invitations" in data
    assert "audit_trail" in data


def test_onboarding_survey_mandatory_pdn_consent(client):
    """POST /candidate-profile/onboarding-survey: отказ без согласия на обработку ПДн (HTTP 400)."""
    reg_payload = {
        "email": "onboarding.consent@example.com",
        "password": "Password12345",
        "role": "candidate",
        "first_name": "Валерий",
        "last_name": "Морозов",
        "consent_pdn_processing": True,
        "consent_profile_publication": True,
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    token = reg_res.json()["tokens"]["access_token"]

    survey_payload = {
        "specialization_id": 1,
        "claimed_grade_id": 1,
        "skills": ["Python", "FastAPI"],
        "city": "Москва",
        "work_format": "remote",
        "consent_personal_data": False,
    }

    resp_fail = client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        json=survey_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_fail.status_code == 400
    assert resp_fail.json()["detail"] == "Согласие на обработку персональных данных (152-ФЗ) обязательно"

    # С consent_personal_data=True онбординг проходит успешно
    survey_payload["consent_personal_data"] = True
    resp_ok = client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        json=survey_payload,
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp_ok.status_code == 201


def test_admin_audit_logs_rbac_and_content(client):
    """GET /admin/audit-logs: проверка RBAC (403 для candidate, 200 для admin) и структуры записей."""
    # 1. Register candidate and verify 403 Forbidden
    reg_cand = client.post(
        "/api/v1/auth/register",
        json={
            "email": "cand.audit.rbac@example.com",
            "password": "Password12345",
            "role": "candidate",
            "first_name": "Иван",
            "last_name": "Тестов",
            "consent_pdn_processing": True,
            "consent_profile_publication": True,
        },
    )
    cand_token = reg_cand.json()["tokens"]["access_token"]
    resp_cand = client.get("/api/v1/admin/audit-logs", headers={"Authorization": f"Bearer {cand_token}"})
    assert resp_cand.status_code == 403

    # 2. Register admin and verify 200 OK
    reg_admin = client.post(
        "/api/v1/auth/register",
        json={
            "email": "admin.audit.rbac@example.com",
            "password": "Password12345",
            "role": "admin",
            "first_name": "Админ",
            "last_name": "Главный",
            "consent_pdn_processing": True,
            "consent_profile_publication": True,
        },
    )
    admin_token = reg_admin.json()["tokens"]["access_token"]
    resp_admin = client.get("/api/v1/admin/audit-logs", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp_admin.status_code == 200
    data = resp_admin.json()
    assert "items" in data
    assert "meta" in data
    assert isinstance(data["items"], list)

    # 3. GET /admin/users should return registered users list
    resp_users = client.get("/api/v1/admin/users", headers={"Authorization": f"Bearer {admin_token}"})
    assert resp_users.status_code == 200
    data_users = resp_users.json()
    assert "items" in data_users
    assert len(data_users["items"]) > 0
    first_u = data_users["items"][0]
    assert "email" in first_u
    assert "role" in first_u
    assert "is_pdn_consent_given" in first_u


