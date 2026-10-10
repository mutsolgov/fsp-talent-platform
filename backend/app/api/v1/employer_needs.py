"""
FSP IT-Talent Platform — API Module 7: employer-needs.
Defined in docs/04_OPENAPI_CONTRACTS_AND_SECURITY.md §2.7 and DISPATCH.md.
"""
from __future__ import annotations

import math
from typing import Dict, Optional, Tuple
import sqlalchemy as sa
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.api.v1.auth import get_current_user
from app.database import get_db
from app.models.employer_profiles import EmployerProfile
from app.models.employer_needs import EmployerNeed
from app.models.specializations import Specialization
from app.models.grades import Grade
from app.models.users import User
from app.models.candidate_profiles import CandidateProfile
from app.models.candidate_categorizations import CandidateCategorization
from app.models.categories import Category
from app.schemas.base import PaginationMeta, StatusMessageResponse
from app.schemas.employer_needs import (
    CreateEmployerNeedRequest,
    EmployerNeedListResponse,
    EmployerNeedResponse,
    UpdateEmployerNeedRequest,
)

router = APIRouter(prefix="/employer-needs", tags=["employer-needs"])


async def count_matched_candidates(
    db: AsyncSession,
    specialization_id: int,
    target_grade_id: int,
) -> int:
    """
    Counts active published candidates matching specialization_id and target_grade_id.
    Matches via verified CandidateCategorization or onboarding survey_data_json.
    """
    cat_stmt = (
        select(CandidateProfile.id)
        .join(CandidateCategorization, CandidateCategorization.candidate_profile_id == CandidateProfile.id)
        .join(Category, CandidateCategorization.category_id == Category.id)
        .where(
            CandidateProfile.is_published.is_(True),
            CandidateCategorization.is_current.is_(True),
            Category.specialization_id == specialization_id,
            sa.or_(
                CandidateCategorization.confirmed_grade_id == target_grade_id,
                Category.grade_id == target_grade_id,
            ),
        )
    )
    matching_ids = set((await db.execute(cat_stmt)).scalars().all())

    # Check candidates with onboarding survey who don't yet have a categorization record
    survey_stmt = (
        select(CandidateProfile.id, CandidateProfile.survey_data_json)
        .where(CandidateProfile.is_published.is_(True))
    )
    if matching_ids:
        survey_stmt = survey_stmt.where(CandidateProfile.id.not_in(matching_ids))

    for cand_id, s_data in (await db.execute(survey_stmt)).all():
        if isinstance(s_data, dict):
            if (
                s_data.get("specialization_id") == specialization_id
                and s_data.get("claimed_grade_id") == target_grade_id
            ):
                matching_ids.add(cand_id)

    return len(matching_ids)


from app.api.deps import get_current_employer



def _format_need_response(need: EmployerNeed, matched_candidates_count: int = 0) -> EmployerNeedResponse:
    spec_code = need.specialization.code if need.specialization else "backend"
    grade_code = need.target_grade.code if need.target_grade else "middle"

    core_stack = need.core_stack_json or []
    nice_stack = need.nice_to_have_stack_json or []

    return EmployerNeedResponse(
        id=need.id,
        employer_profile_id=need.employer_profile_id,
        specialization_id=need.specialization_id,
        target_grade_id=need.target_grade_id,
        title=f"{spec_code.capitalize()} {grade_code.capitalize()}",
        specialization=spec_code,
        grade=grade_code,
        description=need.team_tasks_text,
        team_tasks_text=need.team_tasks_text,
        required_skills=core_stack,
        core_stack=core_stack,
        optional_skills=nice_stack,
        nice_to_have_stack=nice_stack,
        salary_min=need.salary_min,
        salary_max=need.salary_max,
        salary_currency="RUB",
        work_format=need.work_format,
        city="Москва",
        is_active=need.is_active,
        matched_candidates_count=matched_candidates_count,
        created_at=need.created_at,
        updated_at=need.updated_at,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    response_model=EmployerNeedResponse,
    summary="Создание структурированной потребности с обязательной вилкой в ₽",
)
async def create_employer_need(
    payload: CreateEmployerNeedRequest,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> EmployerNeedResponse:
    # 1. Проверка специализации
    spec = await db.scalar(select(Specialization).where(Specialization.id == payload.specialization_id))
    if not spec:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Указанная специализация не найдена",
        )

    # 2. Проверка грейда
    grade_id = payload.target_grade_id or payload.grade_id or 2
    grade = await db.scalar(select(Grade).where(Grade.id == grade_id))
    if not grade:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Указанный грейд не найден",
        )

    # 3. Валидация зарплаты (RUB обязательна)
    if payload.salary_currency != "RUB":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Валюта зарплаты должна быть строго RUB (ERR_INVALID_CURRENCY)",
        )
    if payload.salary_min <= 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Минимальная зарплата должна быть строго положительной (ERR_SALARY_MIN_NOT_POSITIVE)",
        )
    if payload.salary_max < payload.salary_min:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="salary_max не может быть меньше salary_min (ERR_SALARY_MAX_LT_MIN)",
        )
    if (payload.salary_max / payload.salary_min) > 3.5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Разброс зарплатной вилки превышает допустимый предел 3.5 (ERR_SUSPICIOUS_SALARY_SPREAD)",
        )

    core_stack = payload.required_skills or payload.core_stack or []
    nice_stack = payload.optional_skills or payload.nice_to_have_stack or []
    tasks_text = payload.team_tasks_text or payload.description or payload.title or "Задачи команды разработки"

    need = EmployerNeed(
        employer_profile_id=employer.id,
        specialization_id=payload.specialization_id,
        target_grade_id=grade_id,
        core_stack_json=core_stack,
        nice_to_have_stack_json=nice_stack,
        salary_min=payload.salary_min,
        salary_max=payload.salary_max,
        work_format=payload.work_format or "remote",
        team_tasks_text=tasks_text,
        is_active=True,
    )
    db.add(need)
    await db.commit()

    # Load relationships for serialization
    stmt = (
        select(EmployerNeed)
        .options(selectinload(EmployerNeed.specialization), selectinload(EmployerNeed.target_grade))
        .where(EmployerNeed.id == need.id)
    )
    loaded_need = (await db.execute(stmt)).scalar_one()
    matched_count = await count_matched_candidates(db, loaded_need.specialization_id, loaded_need.target_grade_id)
    return _format_need_response(loaded_need, matched_candidates_count=matched_count)


@router.get(
    "",
    response_model=EmployerNeedListResponse,
    summary="Список потребностей текущего работодателя",
)
async def list_employer_needs(
    is_active: Optional[bool] = Query(None, description="Фильтр по активности"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> EmployerNeedListResponse:
    query = (
        select(EmployerNeed)
        .options(selectinload(EmployerNeed.specialization), selectinload(EmployerNeed.target_grade))
        .where(EmployerNeed.employer_profile_id == employer.id)
    )
    if is_active is not None:
        query = query.where(EmployerNeed.is_active == is_active)

    # Total count
    count_stmt = select(func.count(EmployerNeed.id)).where(EmployerNeed.employer_profile_id == employer.id)
    if is_active is not None:
        count_stmt = count_stmt.where(EmployerNeed.is_active == is_active)
    total = (await db.scalar(count_stmt)) or 0

    query = query.order_by(EmployerNeed.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
    needs = list((await db.execute(query)).scalars().all())

    matched_counts_cache: Dict[Tuple[int, int], int] = {}
    items = []
    for n in needs:
        key = (n.specialization_id, n.target_grade_id)
        if key not in matched_counts_cache:
            matched_counts_cache[key] = await count_matched_candidates(db, n.specialization_id, n.target_grade_id)
        items.append(_format_need_response(n, matched_candidates_count=matched_counts_cache[key]))
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return EmployerNeedListResponse(
        items=items,
        meta=PaginationMeta(total=total, page=page, page_size=page_size, total_pages=total_pages),
    )


@router.get(
    "/{id}",
    response_model=EmployerNeedResponse,
    summary="Детальная карточка потребности команды",
)
async def get_employer_need(
    id: int,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> EmployerNeedResponse:
    stmt = (
        select(EmployerNeed)
        .options(selectinload(EmployerNeed.specialization), selectinload(EmployerNeed.target_grade))
        .where(EmployerNeed.id == id, EmployerNeed.employer_profile_id == employer.id)
    )
    need = (await db.execute(stmt)).scalar_one_or_none()
    if not need:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Потребность работодателя не найдена",
        )
    count = await count_matched_candidates(db, need.specialization_id, need.target_grade_id)
    return _format_need_response(need, matched_candidates_count=count)


@router.put(
    "/{id}",
    response_model=EmployerNeedResponse,
    summary="Обновление требований потребности",
)
async def update_employer_need(
    id: int,
    payload: UpdateEmployerNeedRequest,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> EmployerNeedResponse:
    stmt = (
        select(EmployerNeed)
        .options(selectinload(EmployerNeed.specialization), selectinload(EmployerNeed.target_grade))
        .where(EmployerNeed.id == id, EmployerNeed.employer_profile_id == employer.id)
    )
    need = (await db.execute(stmt)).scalar_one_or_none()
    if not need:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Потребность работодателя не найдена",
        )

    # Validate salary if modified
    if payload.salary_currency is not None and payload.salary_currency != "RUB":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Валюта зарплаты должна быть строго RUB (ERR_INVALID_CURRENCY)",
        )
    new_min = payload.salary_min if payload.salary_min is not None else need.salary_min
    new_max = payload.salary_max if payload.salary_max is not None else need.salary_max

    if new_min <= 0 or new_max < new_min:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Некорректная зарплатная вилка",
        )
    if (new_max / new_min) > 3.5:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Разброс зарплатной вилки превышает 3.5 (ERR_SUSPICIOUS_SALARY_SPREAD)",
        )

    need.salary_min = new_min
    need.salary_max = new_max

    if payload.specialization_id is not None:
        need.specialization_id = payload.specialization_id
    target_gid = payload.target_grade_id or payload.grade_id
    if target_gid is not None:
        need.target_grade_id = target_gid
    if payload.required_skills is not None or payload.core_stack is not None:
        need.core_stack_json = payload.required_skills or payload.core_stack or []
    if payload.optional_skills is not None or payload.nice_to_have_stack is not None:
        need.nice_to_have_stack_json = payload.optional_skills or payload.nice_to_have_stack or []
    if payload.team_tasks_text is not None or payload.description is not None:
        need.team_tasks_text = payload.team_tasks_text or payload.description or ""
    if payload.work_format is not None:
        need.work_format = payload.work_format
    if payload.is_active is not None:
        need.is_active = payload.is_active

    await db.commit()
    await db.refresh(need)
    count = await count_matched_candidates(db, need.specialization_id, need.target_grade_id)
    return _format_need_response(need, matched_candidates_count=count)


@router.patch(
    "/{id}/close",
    response_model=EmployerNeedResponse,
    summary="Закрытие потребности команды",
)
async def close_employer_need(
    id: int,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> EmployerNeedResponse:
    stmt = (
        select(EmployerNeed)
        .options(selectinload(EmployerNeed.specialization), selectinload(EmployerNeed.target_grade))
        .where(EmployerNeed.id == id, EmployerNeed.employer_profile_id == employer.id)
    )
    need = (await db.execute(stmt)).scalar_one_or_none()
    if not need:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Потребность работодателя не найдена",
        )

    need.is_active = False
    await db.commit()
    await db.refresh(need)
    count = await count_matched_candidates(db, need.specialization_id, need.target_grade_id)
    return _format_need_response(need, matched_candidates_count=count)


@router.delete(
    "/{id}",
    response_model=StatusMessageResponse,
    summary="Удаление потребности",
)
async def delete_employer_need(
    id: int,
    employer: EmployerProfile = Depends(get_current_employer),
    db: AsyncSession = Depends(get_db),
) -> StatusMessageResponse:
    stmt = select(EmployerNeed).where(EmployerNeed.id == id, EmployerNeed.employer_profile_id == employer.id)
    need = (await db.execute(stmt)).scalar_one_or_none()
    if not need:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Потребность работодателя не найдена",
        )

    await db.delete(need)
    await db.commit()
    return StatusMessageResponse(status="ok", message="Потребность успешно удалена")
