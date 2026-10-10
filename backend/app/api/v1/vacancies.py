"""
FSP IT-Talent Platform — API Module 10: vacancies.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.10 and DISPATCH.md.
Mandatory Invariant: salary_min > 0 AND salary_max >= salary_min in RUB (spread <= 3.5).
"""
from __future__ import annotations

from datetime import datetime, timezone
import math
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models.employer_profiles import EmployerProfile
from app.models.grades import Grade
from app.models.specializations import Specialization
from app.models.users import User
from app.models.vacancies import Vacancy
from app.schemas.base import PaginationMeta
from app.schemas.candidate_profile import WorkFormatEnum
from app.schemas.vacancies import (
    CreateVacancyRequest,
    PaginatedVacanciesResponse,
    UpdateVacancyRequest,
    UpdateVacancyStatusRequest,
    VacancyDetailResponse,
    VacancyStatusEnum,
)
from app.services.antifraud_service import validate_salary_range

router = APIRouter(prefix="/vacancies", tags=["vacancies"])


from app.api.deps import get_current_employer


def _serialize_vacancy(v: Vacancy) -> VacancyDetailResponse:
    app_count = len(v.applications) if hasattr(v, "applications") and v.applications is not None else 0
    spec_name = v.specialization.name if getattr(v, "specialization", None) else "Backend"
    grade_name = v.grade.name if getattr(v, "grade", None) else "Middle"
    emp_name = v.employer_profile.company_name if getattr(v, "employer_profile", None) else "Компания"
    status_enum = VacancyStatusEnum(v.status) if v.status in VacancyStatusEnum._value2member_map_ else VacancyStatusEnum.PUBLISHED
    fmt_enum = WorkFormatEnum(v.work_format) if v.work_format in WorkFormatEnum._value2member_map_ else WorkFormatEnum.ANY

    skills = v.required_skills_json if isinstance(v.required_skills_json, list) else []

    return VacancyDetailResponse(
        id=v.id,
        employer_profile_id=v.employer_profile_id,
        employer_company_name=emp_name,
        specialization=spec_name,
        specialization_id=v.specialization_id,
        grade=grade_name,
        grade_id=v.grade_id,
        title=v.title,
        description=v.description,
        required_skills=skills,
        optional_skills=[],
        salary_min=v.salary_min,
        salary_max=v.salary_max,
        salary_currency="RUB",
        work_format=fmt_enum,
        city=v.city,
        status=status_enum,
        applications_count=app_count,
        created_at=v.created_at,
        updated_at=v.updated_at,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=VacancyDetailResponse,
    summary="Создание вакансии с обязательной вилкой зарплаты в рублях",
)
@router.post(
    "/",
    status_code=status.HTTP_201_CREATED,
    response_model=VacancyDetailResponse,
    include_in_schema=False,
)
async def create_vacancy(
    payload: CreateVacancyRequest,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> VacancyDetailResponse:
    # 1. Mandatory salary validation
    is_valid, err_msg = validate_salary_range(payload.salary_min, payload.salary_max)
    if not is_valid:
        error_code = "ERR_INVALID_SALARY"
        if payload.salary_max < payload.salary_min:
            error_code = "ERR_SALARY_MAX_LT_MIN"
        elif payload.salary_min > 0 and (payload.salary_max / payload.salary_min) > 3.5:
            error_code = "ERR_SUSPICIOUS_SALARY_SPREAD"
        elif payload.salary_min <= 0:
            error_code = "ERR_SALARY_MIN_NOT_POSITIVE"
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"{err_msg} ({error_code})",
        )

    # 2. Check specialization & grade
    spec = await db.scalar(select(Specialization).where(Specialization.id == payload.specialization_id))
    if not spec:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Специализация не найдена")

    grd = await db.scalar(select(Grade).where(Grade.id == payload.grade_id))
    if not grd:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Грейд не найден")

    # 3. Create vacancy
    fmt_str = payload.work_format.value if hasattr(payload.work_format, "value") else str(payload.work_format)
    vacancy = Vacancy(
        employer_profile_id=employer.id,
        specialization_id=payload.specialization_id,
        grade_id=payload.grade_id,
        title=payload.title,
        description=payload.description,
        required_skills_json=payload.required_skills,
        salary_min=payload.salary_min,
        salary_max=payload.salary_max,
        work_format=fmt_str,
        city=payload.city or "Москва",
        status="published",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db.add(vacancy)
    await db.commit()
    await db.refresh(vacancy)

    fetch_stmt = (
        select(Vacancy)
        .where(Vacancy.id == vacancy.id)
        .options(
            selectinload(Vacancy.specialization),
            selectinload(Vacancy.grade),
            selectinload(Vacancy.employer_profile),
            selectinload(Vacancy.applications),
        )
    )
    loaded = (await db.execute(fetch_stmt)).scalar_one()
    return _serialize_vacancy(loaded)


@router.get(
    "",
    response_model=PaginatedVacanciesResponse,
    summary="Каталог вакансий с фильтрацией",
)
@router.get(
    "/",
    response_model=PaginatedVacanciesResponse,
    include_in_schema=False,
)
async def list_vacancies(
    specialization_id: Optional[int] = Query(None),
    grade_id: Optional[int] = Query(None),
    status_filter: Optional[str] = Query("published", alias="status"),
    city: Optional[str] = Query(None),
    work_format: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> PaginatedVacanciesResponse:
    query = (
        select(Vacancy)
        .options(
            selectinload(Vacancy.specialization),
            selectinload(Vacancy.grade),
            selectinload(Vacancy.employer_profile),
            selectinload(Vacancy.applications),
        )
        .order_by(Vacancy.created_at.desc())
    )
    count_query = select(func.count(Vacancy.id))

    if status_filter:
        query = query.where(Vacancy.status == status_filter)
        count_query = count_query.where(Vacancy.status == status_filter)
    if specialization_id:
        query = query.where(Vacancy.specialization_id == specialization_id)
        count_query = count_query.where(Vacancy.specialization_id == specialization_id)
    if grade_id:
        query = query.where(Vacancy.grade_id == grade_id)
        count_query = count_query.where(Vacancy.grade_id == grade_id)
    if city:
        query = query.where(Vacancy.city.ilike(f"%{city}%"))
        count_query = count_query.where(Vacancy.city.ilike(f"%{city}%"))
    if work_format:
        query = query.where(Vacancy.work_format == work_format)
        count_query = count_query.where(Vacancy.work_format == work_format)
    if search:
        query = query.where(Vacancy.title.ilike(f"%{search}%"))
        count_query = count_query.where(Vacancy.title.ilike(f"%{search}%"))

    total = (await db.execute(count_query)).scalar_one()
    items_stmt = query.offset((page - 1) * page_size).limit(page_size)
    vacancies = (await db.execute(items_stmt)).scalars().all()

    items = [_serialize_vacancy(v) for v in vacancies]
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return PaginatedVacanciesResponse(
        items=items,
        meta=PaginationMeta(total=total, page=page, page_size=page_size, total_pages=total_pages),
    )


@router.get(
    "/mine",
    response_model=PaginatedVacanciesResponse,
    summary="Список вакансий текущего работодателя",
)
async def list_my_vacancies(
    status_filter: Optional[str] = Query(None, alias="status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> PaginatedVacanciesResponse:
    query = (
        select(Vacancy)
        .where(Vacancy.employer_profile_id == employer.id)
        .options(
            selectinload(Vacancy.specialization),
            selectinload(Vacancy.grade),
            selectinload(Vacancy.employer_profile),
            selectinload(Vacancy.applications),
        )
        .order_by(Vacancy.created_at.desc())
    )
    count_query = select(func.count(Vacancy.id)).where(Vacancy.employer_profile_id == employer.id)

    if status_filter:
        query = query.where(Vacancy.status == status_filter)
        count_query = count_query.where(Vacancy.status == status_filter)

    total = (await db.execute(count_query)).scalar_one()
    items_stmt = query.offset((page - 1) * page_size).limit(page_size)
    vacancies = (await db.execute(items_stmt)).scalars().all()

    items = [_serialize_vacancy(v) for v in vacancies]
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return PaginatedVacanciesResponse(
        items=items,
        meta=PaginationMeta(total=total, page=page, page_size=page_size, total_pages=total_pages),
    )


@router.get(
    "/{id}",
    response_model=VacancyDetailResponse,
    summary="Детальная страница вакансии",
)
async def get_vacancy_detail(
    id: int,
    db: AsyncSession = Depends(get_db),
) -> VacancyDetailResponse:
    stmt = (
        select(Vacancy)
        .where(Vacancy.id == id)
        .options(
            selectinload(Vacancy.specialization),
            selectinload(Vacancy.grade),
            selectinload(Vacancy.employer_profile),
            selectinload(Vacancy.applications),
        )
    )
    v = (await db.execute(stmt)).scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вакансия не найдена")
    return _serialize_vacancy(v)


@router.put(
    "/{id}",
    response_model=VacancyDetailResponse,
    summary="Редактирование параметров вакансии",
)
async def update_vacancy(
    id: int,
    payload: UpdateVacancyRequest,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> VacancyDetailResponse:
    stmt = (
        select(Vacancy)
        .where(Vacancy.id == id)
        .options(
            selectinload(Vacancy.specialization),
            selectinload(Vacancy.grade),
            selectinload(Vacancy.employer_profile),
            selectinload(Vacancy.applications),
        )
    )
    v = (await db.execute(stmt)).scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вакансия не найдена")

    if v.employer_profile_id != employer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Редактирование чужой вакансии запрещено")

    if payload.salary_min is not None or payload.salary_max is not None:
        new_min = payload.salary_min if payload.salary_min is not None else v.salary_min
        new_max = payload.salary_max if payload.salary_max is not None else v.salary_max
        is_valid, err_msg = validate_salary_range(new_min, new_max)
        if not is_valid:
            error_code = "ERR_INVALID_SALARY"
            if new_max < new_min:
                error_code = "ERR_SALARY_MAX_LT_MIN"
            elif new_min > 0 and (new_max / new_min) > 3.5:
                error_code = "ERR_SUSPICIOUS_SALARY_SPREAD"
            elif new_min <= 0:
                error_code = "ERR_SALARY_MIN_NOT_POSITIVE"
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"{err_msg} ({error_code})",
            )
        v.salary_min = new_min
        v.salary_max = new_max

    if payload.title is not None:
        v.title = payload.title
    if payload.description is not None:
        v.description = payload.description
    if payload.specialization_id is not None:
        v.specialization_id = payload.specialization_id
    if payload.grade_id is not None:
        v.grade_id = payload.grade_id
    if payload.required_skills is not None:
        v.required_skills_json = payload.required_skills
    if payload.work_format is not None:
        v.work_format = payload.work_format.value if hasattr(payload.work_format, "value") else str(payload.work_format)
    if payload.city is not None:
        v.city = payload.city
    if payload.status is not None:
        v.status = payload.status.value if hasattr(payload.status, "value") else str(payload.status)

    v.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(v)
    return _serialize_vacancy(v)


@router.post(
    "/{id}/close",
    response_model=VacancyDetailResponse,
    summary="Закрытие вакансии работодателем",
)
async def close_vacancy(
    id: int,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> VacancyDetailResponse:
    stmt = (
        select(Vacancy)
        .where(Vacancy.id == id)
        .options(
            selectinload(Vacancy.specialization),
            selectinload(Vacancy.grade),
            selectinload(Vacancy.employer_profile),
            selectinload(Vacancy.applications),
        )
    )
    v = (await db.execute(stmt)).scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вакансия не найдена")

    if v.employer_profile_id != employer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Закрытие чужой вакансии запрещено")

    v.status = "closed"
    v.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(v)
    return _serialize_vacancy(v)


@router.patch(
    "/{id}/status",
    response_model=VacancyDetailResponse,
    summary="Изменение статуса вакансии",
)
async def update_vacancy_status(
    id: int,
    payload: UpdateVacancyStatusRequest,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> VacancyDetailResponse:
    stmt = (
        select(Vacancy)
        .where(Vacancy.id == id)
        .options(
            selectinload(Vacancy.specialization),
            selectinload(Vacancy.grade),
            selectinload(Vacancy.employer_profile),
            selectinload(Vacancy.applications),
        )
    )
    v = (await db.execute(stmt)).scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вакансия не найдена")

    if v.employer_profile_id != employer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Изменение статуса чужой вакансии запрещено")

    v.status = payload.status.value if hasattr(payload.status, "value") else str(payload.status)
    v.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(v)
    return _serialize_vacancy(v)


@router.delete(
    "/{id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Удаление вакансии",
)
async def delete_vacancy(
    id: int,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Vacancy).where(Vacancy.id == id)
    v = (await db.execute(stmt)).scalar_one_or_none()
    if not v:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Вакансия не найдена")

    if v.employer_profile_id != employer.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Удаление чужой вакансии запрещено")

    await db.delete(v)
    await db.commit()
    return None
