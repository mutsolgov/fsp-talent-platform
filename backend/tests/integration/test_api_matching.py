"""
Integration Test Suite for API Modules 7 & 8: Matching Layer.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.7-2.8 and DISPATCH.md.
"""
from __future__ import annotations

import asyncio
import os
import sys

# Ensure backend directory is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

import pytest  # noqa: E402
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy import text  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.database import get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models.base import Base  # noqa: E402
import app.models as _models  # noqa: F401, E402
from scripts.seed_reference_data import seed_reference_data  # noqa: E402

from sqlalchemy import event, text

TEST_DB_URL = "sqlite+aiosqlite:///./test_matching_integration.db"
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
                    "invitations", "fsp_achievements", "shortlist_items",
                    "saved_shortlists", "employer_needs", "employer_profiles",
                    "candidate_categorizations", "candidate_skills",
                    "candidate_profiles", "user_consents", "users"
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



_inn_counter = 0
VALID_INNS = ["7707083893", "7736207543", "7710140679", "7842349892", "7702070139"]


def _auth_headers(client, email: str, role: str = "employer") -> dict:
    global _inn_counter
    inn = None
    company_name = None
    if role == "employer":
        inn = VALID_INNS[_inn_counter % len(VALID_INNS)]
        company_name = f"ООО Финтех {_inn_counter}"
        _inn_counter += 1

    reg_payload = {
        "email": email,
        "password": "StrongPassword123!",
        "role": role,
        "first_name": "Тест",
        "last_name": "Пользователь",
        "company_name": company_name,
        "inn": inn,
        "consent_pdn_processing": True,
        "consent_profile_publication": True,
    }
    reg_resp = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_resp.status_code == 201, f"Registration failed: {reg_resp.text}"
    token = reg_resp.json()["tokens"]["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_employer_needs_crud_and_salary_validation(client):
    """
    Проверка CRUD потребностей работодателя и строгой валидации зарплатной вилки в ₽:
    - salary_min > 0
    - salary_max >= salary_min
    - salary_max / salary_min <= 3.5
    """
    headers = _auth_headers(client, "employer.needs@example.com", role="employer")

    # 1. Попытка создать с salary_min <= 0
    resp_neg = client.post(
        "/api/v1/employer-needs",
        headers=headers,
        json={
            "specialization_id": 1,
            "target_grade_id": 2,
            "title": "Backend Middle",
            "required_skills": ["python", "fastapi"],
            "salary_min": 0,
            "salary_max": 200000,
        },
    )
    assert resp_neg.status_code == 422, "Ожидалась ошибка валидации при salary_min <= 0"

    # 2. Попытка создать с salary_max < salary_min
    resp_inverted = client.post(
        "/api/v1/employer-needs",
        headers=headers,
        json={
            "specialization_id": 1,
            "target_grade_id": 2,
            "title": "Backend Middle",
            "required_skills": ["python", "fastapi"],
            "salary_min": 250000,
            "salary_max": 180000,
        },
    )
    assert resp_inverted.status_code == 422, "Ожидалась ошибка валидации при salary_max < salary_min"

    # 3. Попытка создать со спредом > 3.5 (например, от 50 000 до 300 000, ratio 6.0)
    resp_spread = client.post(
        "/api/v1/employer-needs",
        headers=headers,
        json={
            "specialization_id": 1,
            "target_grade_id": 2,
            "title": "Backend Middle",
            "required_skills": ["python", "fastapi"],
            "salary_min": 50000,
            "salary_max": 300000,
        },
    )
    assert resp_spread.status_code == 422, "Ожидалась ошибка валидации при спреде > 3.5"

    # 4. Успешное создание потребности
    resp_create = client.post(
        "/api/v1/employer-needs",
        headers=headers,
        json={
            "specialization_id": 1,
            "target_grade_id": 2,
            "title": "Middle Backend Python",
            "description": "Разработка микросервисов платформы",
            "required_skills": ["python", "fastapi", "postgresql"],
            "optional_skills": ["docker", "redis"],
            "salary_min": 180000,
            "salary_max": 280000,
            "salary_currency": "RUB",
            "work_format": "remote",
        },
    )
    assert resp_create.status_code == 201
    need_data = resp_create.json()
    need_id = need_data["id"]
    assert need_data["salary_min"] == 180000
    assert need_data["salary_max"] == 280000
    assert need_data["salary_currency"] == "RUB"
    assert need_data["is_active"] is True

    # 5. Получение списка потребностей
    resp_list = client.get("/api/v1/employer-needs", headers=headers)
    assert resp_list.status_code == 200
    items = resp_list.json()["items"]
    assert len(items) >= 1
    assert items[0]["id"] == need_id

    # 6. Получение детальной карточки потребности
    resp_get = client.get(f"/api/v1/employer-needs/{need_id}", headers=headers)
    assert resp_get.status_code == 200
    assert resp_get.json()["id"] == need_id

    # 7. Обновление потребности
    resp_update = client.put(
        f"/api/v1/employer-needs/{need_id}",
        headers=headers,
        json={"salary_min": 200000, "salary_max": 300000},
    )
    assert resp_update.status_code == 200
    assert resp_update.json()["salary_min"] == 200000

    # 8. Закрытие потребности
    resp_close = client.patch(f"/api/v1/employer-needs/{need_id}/close", headers=headers)
    assert resp_close.status_code == 200
    assert resp_close.json()["is_active"] is False

    # 9. Удаление потребности
    resp_del = client.delete(f"/api/v1/employer-needs/{need_id}", headers=headers)
    assert resp_del.status_code == 200
    resp_del_check = client.get(f"/api/v1/employer-needs/{need_id}", headers=headers)
    assert resp_del_check.status_code == 404


def test_candidate_bank_search_and_explainability(client):
    """
    Проверка поиска в банке кандидатов:
    - Расчет многофакторного скоринга S
    - Генерация радарной диаграммы Explainability
    - Псевдонимизация ФИО (152-ФЗ)
    - Физическое отсутствие контактов в поисковой выдаче
    """
    # 1. Регистрация соискателя и онбординг
    cand_headers = _auth_headers(client, "cand.bank@example.com", role="candidate")
    survey_resp = client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        headers=cand_headers,
        json={
            "specialization_id": 1,
            "claimed_grade_id": 2,
            "skills": ["python", "fastapi", "postgresql"],
            "city": "Москва",
            "work_format": "remote",
        },
    )
    assert survey_resp.status_code == 201

    # 2. Поиск работодателем
    emp_headers = _auth_headers(client, "employer.search@example.com", role="employer")
    search_resp = client.get(
        "/api/v1/candidate-bank?specialization=backend&grade=middle",
        headers=emp_headers,
    )
    assert search_resp.status_code == 200
    data = search_resp.json()
    items = data["items"]
    assert len(items) >= 1

    card = items[0]
    # Проверка маскирования имени по 152-ФЗ: 'Тест П. (#C-...)'
    assert "(#C-" in card["masked_full_name"]
    # Проверка наличия скора
    assert card["match_score"] is not None
    assert 0.0 <= card["match_score"] <= 100.0

    # Проверка Explainability
    expl = card["explainability"]
    assert expl is not None
    assert "radar_series" in expl
    assert len(expl["radar_series"]) == 5
    assert "human_summary_ru" in expl
    assert "recommendation_badge" in expl


def test_candidate_bank_privacy_152fz_masking(client):
    """
    Проверка защиты персональных данных соискателя (152-ФЗ):
    - В GET /{id} поля email, phone, telegram, github_url строго равны None
    - Запрос GET /{id}/contacts возвращает 403 Forbidden для работодателя
    """
    cand_headers = _auth_headers(client, "cand.private@example.com", role="candidate")
    client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        headers=cand_headers,
        json={
            "specialization_id": 1,
            "claimed_grade_id": 2,
            "skills": ["python"],
        },
    )

    emp_headers = _auth_headers(client, "employer.private@example.com", role="employer")

    # Получаем карточку из банка
    search = client.get("/api/v1/candidate-bank", headers=emp_headers).json()
    cand_id = search["items"][0]["id"]

    # Проверяем детальный просмотр
    detail_resp = client.get(f"/api/v1/candidate-bank/{cand_id}", headers=emp_headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()

    assert detail["is_contacts_masked"] is True
    assert detail["email"] is None
    assert detail["phone"] is None
    assert detail["telegram"] is None
    assert detail["github_url"] is None
    assert detail["raw_resume_pdf_url"] is None

    # Попытка получить прямые контакты до принятия приглашения
    contacts_resp = client.get(f"/api/v1/candidate-bank/{cand_id}/contacts", headers=emp_headers)
    assert contacts_resp.status_code == 403
    assert "152-ФЗ" in contacts_resp.json()["message"] or "152-ФЗ" in contacts_resp.text


def test_categories_catalog_endpoint(client):
    """Проверка доступности каталога 24 канонических категорий."""
    resp = client.get("/api/v1/candidate-bank/categories")
    assert resp.status_code == 200
    categories = resp.json()
    assert len(categories) == 24


def test_shortlist_stateful_pinning_and_refinement(client):
    """
    Проверка stateful-шортлистов:
    - Создание шортлиста
    - Закрепление кандидата (is_pinned = True)
    - Дифференциальное переранжирование (Delta S)
    - Удаление шортлиста
    """
    # 1. Регистрация соискателя
    cand_headers = _auth_headers(client, "cand.shortlist@example.com", role="candidate")
    client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        headers=cand_headers,
        json={"specialization_id": 1, "claimed_grade_id": 2, "skills": ["python"]},
    )

    emp_headers = _auth_headers(client, "employer.shortlist@example.com", role="employer")
    search = client.get("/api/v1/candidate-bank", headers=emp_headers).json()
    cand_id = search["items"][0]["id"]

    # 2. Создание шортлиста
    create_resp = client.post(
        "/api/v1/candidate-bank/shortlists",
        headers=emp_headers,
        json={
            "title": "Подборка Middle Python",
            "candidate_ids": [cand_id],
            "filter_criteria_json": {"city": "Москва"},
        },
    )
    assert create_resp.status_code == 201
    s_data = create_resp.json()
    shortlist_id = s_data["id"]
    assert s_data["title"] == "Подборка Middle Python"
    assert len(s_data["items"]) == 1

    # 3. Закрепление кандидата в шортлисте
    pin_resp = client.post(
        f"/api/v1/candidate-bank/shortlists/{shortlist_id}/pin/{cand_id}",
        headers=emp_headers,
        json={"is_pinned": True},
    )
    assert pin_resp.status_code == 200
    assert pin_resp.json()["is_pinned"] is True

    # 4. Просмотр списка шортлистов
    list_resp = client.get("/api/v1/candidate-bank/shortlists", headers=emp_headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) >= 1
    assert list_resp.json()[0]["pinned_count"] == 1

    # 5. Уточнение фильтров (refine)
    refine_resp = client.post(
        f"/api/v1/candidate-bank/shortlists/{shortlist_id}/refine",
        headers=emp_headers,
        json={"new_filter_criteria_json": {"city": "Москва", "work_format": "remote"}},
    )
    assert refine_resp.status_code == 200
    ref_items = refine_resp.json()["items"]
    assert len(ref_items) == 1
    assert ref_items[0]["is_pinned"] is True

    # 6. Удаление шортлиста
    del_resp = client.delete(f"/api/v1/candidate-bank/shortlists/{shortlist_id}", headers=emp_headers)
    assert del_resp.status_code == 204


def test_matched_candidates_count_live_updating(client):
    """
    Проверка корректного подсчета matched_candidates_count в employer_needs:
    - Создаем потребность (Backend Middle)
    - Изначально подходящих кандидатов 0
    - Регистрируем соискателя с совпадением по специализации и грейду (Backend Middle)
    - Проверяем, что matched_candidates_count обновился до 1
    """
    emp_headers = _auth_headers(client, "employer.matched_count@example.com", role="employer")

    # 1. Создаем потребность (специализация 1 = backend, грейд 2 = middle)
    create_resp = client.post(
        "/api/v1/employer-needs",
        headers=emp_headers,
        json={
            "specialization_id": 1,
            "target_grade_id": 2,
            "title": "Middle Python Backend",
            "required_skills": ["python", "fastapi"],
            "salary_min": 180000,
            "salary_max": 250000,
        },
    )
    assert create_resp.status_code == 201
    need_id = create_resp.json()["id"]
    assert create_resp.json()["matched_candidates_count"] == 0

    # 2. Регистрируем подходящего кандидата
    cand_headers = _auth_headers(client, "cand.matched@example.com", role="candidate")
    survey_resp = client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        headers=cand_headers,
        json={
            "specialization_id": 1,
            "claimed_grade_id": 2,
            "skills": ["python", "fastapi"],
            "city": "Москва",
            "work_format": "remote",
            "expected_salary": 200000,
        },
    )
    assert survey_resp.status_code == 201

    # 3. Запрашиваем карточку потребности и список — счетчик должен быть 1
    get_resp = client.get(f"/api/v1/employer-needs/{need_id}", headers=emp_headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["matched_candidates_count"] == 1

    list_resp = client.get("/api/v1/employer-needs", headers=emp_headers)
    assert list_resp.status_code == 200
    matched_need = next(n for n in list_resp.json()["items"] if n["id"] == need_id)
    assert matched_need["matched_candidates_count"] == 1


def test_candidate_bank_invitation_status_live(client):
    """
    Проверка живого статуса приглашения (invitation_status) в выдаче банка кандидатов:
    - До отправки инвайта: invitation_status is None
    - После отправки инвайта: invitation_status == 'sent'
    """
    # 1. Регистрируем кандидата
    cand_headers = _auth_headers(client, "cand.inv_status@example.com", role="candidate")
    client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        headers=cand_headers,
        json={"specialization_id": 1, "claimed_grade_id": 2, "skills": ["python"]},
    )

    # 2. Поиск работодателем до приглашения
    emp_headers = _auth_headers(client, "employer.inv_status@example.com", role="employer")
    search_before = client.get("/api/v1/candidate-bank", headers=emp_headers).json()
    assert len(search_before["items"]) >= 1
    cand_id = search_before["items"][0]["id"]
    assert search_before["items"][0]["invitation_status"] is None

    # 3. Отправка приглашения
    inv_resp = client.post(
        "/api/v1/invitations",
        headers=emp_headers,
        json={
            "candidate_profile_id": cand_id,
            "proposal_text": "Приглашаем в команду backend разработки",
            "salary_min": 200000,
            "salary_max": 280000,
            "contact_method": "platform",
        },
    )
    assert inv_resp.status_code == 201

    # 4. Повторный поиск работодателем — статус должен быть 'sent'
    search_after = client.get("/api/v1/candidate-bank", headers=emp_headers).json()
    card = next(c for c in search_after["items"] if c["id"] == cand_id)
    assert card["invitation_status"] == "sent"


def test_candidate_bank_real_fsp_achievements_aggregation_and_serialization(client):
    """
    Проверка реальной агрегации и сериализации достижений ФСП (fsp_achievements):
    - При наличии fsp_id и записей в fsp_achievements возвращается сериализованный список
    - Контакты соискателя строго замаскированы по 152-ФЗ
    """
    cand_headers = _auth_headers(client, "cand.fsp_real@example.com", role="candidate")
    client.post(
        "/api/v1/candidate-profile/onboarding-survey",
        headers=cand_headers,
        json={"specialization_id": 1, "claimed_grade_id": 2, "skills": ["python", "c++"]},
    )

    emp_headers = _auth_headers(client, "employer.fsp_real@example.com", role="employer")
    search = client.get("/api/v1/candidate-bank", headers=emp_headers).json()
    cand_id = search["items"][0]["id"]

    # Добавляем реальное достижение ФСП в БД
    async def _insert_fsp():
        async with test_session_factory() as session:
            from app.models.candidate_profiles import CandidateProfile
            from app.models.fsp_achievements import FspAchievement
            cand_profile = await session.get(CandidateProfile, cand_id)
            cand_profile.fsp_id = "FSP-RUS-7701"
            cand_profile.fsp_verified = True

            ach = FspAchievement(
                candidate_profile_id=cand_id,
                fsp_id="FSP-RUS-7701",
                championship_name="Чемпионат России по спортивному программированию 2025",
                discipline="algorithmic",
                stage="всероссийский",
                year=2025,
                place=2,
                medal="silver",
                sport_rank="kms",
                rating_points=24,
            )
            session.add(ach)
            await session.commit()

    asyncio.run(_insert_fsp())

    # Запрашиваем анонимизированную детальную карточку
    detail_resp = client.get(f"/api/v1/candidate-bank/{cand_id}", headers=emp_headers)
    assert detail_resp.status_code == 200
    detail = detail_resp.json()

    assert detail["fsp_id"] == "FSP-RUS-7701"
    assert detail["fsp_verified"] is True
    assert len(detail["fsp_achievements"]) == 1
    ach_data = detail["fsp_achievements"][0]
    assert ach_data["championship_name"] == "Чемпионат России по спортивному программированию 2025"
    assert ach_data["medal"] == "silver"
    assert ach_data["stage"] == "всероссийский"
    assert ach_data["sport_rank"] == "kms"
    assert ach_data["rating_points"] == 24

    # Проверка 152-ФЗ
    assert detail["is_contacts_masked"] is True
    assert detail["email"] is None
    assert detail["phone"] is None
